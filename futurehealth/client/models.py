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

    id: str
    name: str
    address: str

    def __str__(self):
        return f'{self.id} - {self.name}'
