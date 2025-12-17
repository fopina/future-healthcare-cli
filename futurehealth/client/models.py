from pydantic import BaseModel, Field


class Person(BaseModel):
    card_number: str = Field(alias='CardNumber')
    name: str = Field(alias='Name')
    email: str = Field(alias='Email')


class Service(BaseModel):
    id: int = Field(alias='Id')
    name: str = Field(alias='Name')


class Building(BaseModel):
    id: str
    name: str
    address: str

    def __str__(self):
        return f'{self.id} - {self.name}'
