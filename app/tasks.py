from datetime import datetime
import pandas as pd
from celery_app import celery_app
from database import SessionLocal
import models
from cleaning import clean_dataframe
from anomaly import detect_anomalies
from llm import batch_classify, generate_narrative


@celery_app.task(name="process_job")
def process_job(job_id: int, file_path: str):
    db = SessionLocal()
    job = db.query(models.Job).filter(models.Job.id == job_id).first()

    try:
        job.status = "processing"
        db.commit()

        df = pd.read_csv(file_path)
        job.row_count_raw = len(df)

        df = clean_dataframe(df)
        df = detect_anomalies(df)
        job.row_count_clean = len(df)
        db.commit()

        
        to_classify = df[df["category"] == "Uncategorised"]
        batch_input = [
            {"id": int(idx), "merchant": row["merchant"], "notes": row["notes"]}
            for idx, row in to_classify.iterrows()
        ]
        classified = batch_classify(batch_input)

        df["llm_category"] = None
        df["llm_failed"] = False
        if batch_input and classified is None:
            df.loc[to_classify.index, "llm_failed"] = True
        elif classified:
            for idx, category in classified.items():
                df.at[idx, "category"] = category
                df.at[idx, "llm_category"] = category

        
        for _, row in df.iterrows():
            txn = models.Transaction(
                job_id=job_id,
                txn_id=row["txn_id"],
                date=row["date"],
                merchant=row["merchant"],
                amount=row["amount"],
                currency=row["currency"],
                status=row["status"],
                category=row["category"],
                account_id=row["account_id"],
                notes=row["notes"],
                is_anomaly=bool(row["is_anomaly"]),
                anomaly_reason=row["anomaly_reason"],
                llm_category=row.get("llm_category"),
                llm_failed=bool(row.get("llm_failed", False)),
            )
            db.add(txn)
        db.commit()

        
        total_inr = float(df.loc[df["currency"] == "INR", "amount"].sum())
        total_usd = float(df.loc[df["currency"] == "USD", "amount"].sum())
        top_merchants = df["merchant"].value_counts().head(3).to_dict()
        anomaly_count = int(df["is_anomaly"].sum())

        anomaly_details = (
            df[df["is_anomaly"]][["merchant", "amount", "currency", "anomaly_reason"]]
            .head(5)
            .to_dict(orient="records")
        )

        narrative_result = generate_narrative({
            "total_spend_inr": total_inr,
            "total_spend_usd": total_usd,
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "anomaly_details": anomaly_details,
        })

        summary = models.JobSummary(
            job_id=job_id,
            total_spend_inr=total_inr,
            total_spend_usd=total_usd,
            top_merchants=top_merchants,
            anomaly_count=anomaly_count,
            narrative=(narrative_result or {}).get("narrative", "Narrative generation failed."),
            risk_level=(narrative_result or {}).get("risk_level", "unknown"),
        )
        db.add(summary)

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()
