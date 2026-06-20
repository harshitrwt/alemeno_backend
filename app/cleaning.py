import pandas as pd


def normalize_date(value):
    """Handles DD-MM-YYYY and YYYY/MM/DD, falls back to a best-effort parse."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    value = str(value).strip()

    for fmt in ("%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return pd.to_datetime(value, format=fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        return pd.to_datetime(value, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def clean_amount(value):
    if pd.isna(value):
        return None
    value = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return None


def clean_currency(value):
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def clean_status(value):
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def clean_category(value):
    if pd.isna(value) or str(value).strip() == "":
        return "Uncategorised"
    return str(value).strip()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["date"] = df["date"].apply(normalize_date)
    df["amount"] = df["amount"].apply(clean_amount)
    df["currency"] = df["currency"].apply(clean_currency)
    df["status"] = df["status"].apply(clean_status)
    df["category"] = df["category"].apply(clean_category)
    df["merchant"] = df["merchant"].astype(str).str.strip()
    df["account_id"] = df["account_id"].astype(str).str.strip()
    df["notes"] = df["notes"].fillna("").astype(str).str.strip()


    missing_mask = df["txn_id"].isna() | (df["txn_id"].astype(str).str.strip() == "")
    df.loc[missing_mask, "txn_id"] = [f"GEN-{i}" for i in range(missing_mask.sum())]

    dedup_cols = ["date", "merchant", "amount", "currency", "status", "account_id"]
    df = df.drop_duplicates(subset=dedup_cols, keep="first")

    df = df.reset_index(drop=True)
    return df
