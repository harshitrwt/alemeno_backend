import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas
from tasks import process_job

app = FastAPI(title="Transaction Processing Pipeline")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.post("/jobs/upload")
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = models.Job(filename=file.filename, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_job.delay(job.id, file_path)

    return {"job_id": job.id, "status": job.status}


@app.get("/jobs/{job_id}/status")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {"job_id": job.id, "status": job.status}

    if job.status == "completed" and job.summary:
        response["summary"] = {
            "total_spend_inr": job.summary.total_spend_inr,
            "total_spend_usd": job.summary.total_spend_usd,
            "anomaly_count": job.summary.anomaly_count,
            "risk_level": job.summary.risk_level,
        }
    if job.status == "failed":
        response["error"] = job.error_message

    return response


@app.get("/jobs/{job_id}/results")
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet, current status: {job.status}",
        )

    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.job_id == job_id)
        .all()
    )
    anomalies = [t for t in transactions if t.is_anomaly]

    category_breakdown = {}
    for t in transactions:
        category_breakdown[t.category] = category_breakdown.get(t.category, 0) + (t.amount or 0)

    return {
        "job_id": job.id,
        "status": job.status,
        "transactions": [schemas.TransactionOut.model_validate(t) for t in transactions],
        "anomalies": [schemas.TransactionOut.model_validate(t) for t in anomalies],
        "category_breakdown": category_breakdown,
        "summary": schemas.JobSummaryOut.model_validate(job.summary) if job.summary else None,
    }


@app.get("/jobs")
def list_jobs(status: str = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Job)
    if status:
        query = query.filter(models.Job.status == status)
    jobs = query.order_by(models.Job.created_at.desc()).all()

    return [
        {
            "id": j.id,
            "filename": j.filename,
            "status": j.status,
            "row_count_raw": j.row_count_raw,
            "row_count_clean": j.row_count_clean,
            "created_at": j.created_at,
        }
        for j in jobs
    ]
