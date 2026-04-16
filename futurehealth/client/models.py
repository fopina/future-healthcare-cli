from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Person(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    card_number: str = Field(alias='CardNumber')
    name: str = Field(alias='Name')
    email: str = Field(alias='Email')


class Service(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    id: int = Field(alias='Id')
    name: str = Field(alias='Name')
    mantory_invoice_file: bool = Field(alias='IsMandatoryInvoiceFile')
    mantory_additional_file: bool = Field(alias='IsMandatoryAditionalFile')


class Building(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None

    def __str__(self):
        return f'{self.id} - {self.name}'


class ReimbursementClaim(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    claim_type: Optional[str] = Field(default=None, alias='ClaimType')
    claim_status: Optional[str] = Field(default=None, alias='ClaimStatus')
    is_process_state_additional_information: Optional[bool] = Field(
        default=None, alias='IsProcessStateAditionalInformation'
    )
    clinic_case: Optional[str] = Field(default=None, alias='ClinicCase')
    date_of_treatment: Optional[str] = Field(default=None, alias='DateOfTreatment')
    payment_date: Optional[str] = Field(default=None, alias='PaymentDate')
    received_date: Optional[str] = Field(default=None, alias='ReceivedDate')
    person_name: Optional[str] = Field(default=None, alias='PersonName')
    card_number: Optional[str] = Field(default=None, alias='CardNumber')
    practice_name: Optional[str] = Field(default=None, alias='PracticeName')
    service_name: Optional[str] = Field(default=None, alias='ServiceName')
    total_value: Optional[float] = Field(default=None, alias='TotalValue')
    total_deductible: Optional[float] = Field(default=None, alias='TotalDeductible')
    total_copayment: Optional[float] = Field(default=None, alias='TotalCoPayment')
    total_insurer: Optional[float] = Field(default=None, alias='TotalInsurer')
    refund_iban: Optional[str] = Field(default=None, alias='RefundIban')


class ReimbursementPaginationResult(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    current_page: Optional[int] = Field(default=None, alias='CurrentPage')
    total_pages: Optional[int] = Field(default=None, alias='TotalPages')


class Reimbursement(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    process_nr: Optional[str] = Field(default=None, alias='ProcessNr')
    type: Optional[str] = Field(default=None, alias='Type')
    person_name: Optional[str] = Field(default=None, alias='PersonName')
    expense_date: Optional[str] = Field(default=None, alias='ExpenseDate')
    practice_name: Optional[str] = Field(default=None, alias='PracticeName')
    invoice_nr: Optional[str] = Field(default=None, alias='InvoiceNr')
    total_value: Optional[float] = Field(default=None, alias='TotalValue')
    currency_code: Optional[str] = Field(default=None, alias='CurrencyCode')
    status: Optional[str] = Field(default=None, alias='Status')
    claims: Optional[list[ReimbursementClaim]] = Field(default=None, alias='Claims')


class UnifiedRefundsResult(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    refunds: Optional[list[Reimbursement]] = Field(default=None, alias='Refunds')
    pagination_result: Optional[ReimbursementPaginationResult] = Field(default=None, alias='PaginationResult')
