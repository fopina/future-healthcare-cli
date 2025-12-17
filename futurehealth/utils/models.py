from pydantic import BaseModel


class ReceiptData(BaseModel):
    business_nif: str
    personal_nif: str
    invoice_number: str
    total_amount: float
    date: str
