import pandas as pd

DOMESTIC_ONLY_MERCHANTS = {"swiggy", "ola", "irctc", "flipkart", "zomato", "bookmyshow"}

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_anomaly"] = False
    df["anomaly_reason"] = None

    # for amount exceeds 3times the account's median
    medians = df.groupby("account_id")["amount"].median()
    for idx, row in df.iterrows():
        median = medians.get(row["account_id"])
        if median and row["amount"] and row["amount"] > 3 * median:
            df.at[idx, "is_anomaly"] = True
            df.at[idx, "anomaly_reason"] = "Amount exceeds 3x times account median"

    # for USD currency on a domestic-only merchant
    for idx, row in df.iterrows():
        merchant = str(row["merchant"]).strip().lower()
        if row["currency"] == "USD" and merchant in DOMESTIC_ONLY_MERCHANTS:
            existing = df.at[idx, "anomaly_reason"]
            reason = "USD based transaction for domestic-only merchant"
            df.at[idx, "is_anomaly"] = True
            df.at[idx, "anomaly_reason"] = f"{existing}; {reason}" if existing else reason

    return df
