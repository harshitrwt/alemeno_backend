from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class TransactionOut(BaseModel):
    txn_id: Optional[str] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool = False

    class Config:
        from_attributes = True


class JobSummaryOut(BaseModel):
    total_spend_inr: float = 0
    total_spend_usd: float = 0
    top_merchants: Optional[Any] = None
    anomaly_count: int = 0
    narrative: Optional[str] = None
    risk_level: Optional[str] = None

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    id: int
    filename: str
    status: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime

    class Config:
        from_attributes = True
