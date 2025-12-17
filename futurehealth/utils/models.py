from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReceiptData(BaseModel):
    model_config = ConfigDict(extra='allow')

    business_nif: str
    invoice_number: str
    total_amount: float
    date: str
    personal_nif: Optional[str] = None
