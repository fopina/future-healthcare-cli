from pydantic import BaseModel, Field


class Person(BaseModel):
    card_number: str = Field(alias='CardNumber')
    name: str = Field(alias='Name')
    email: str = Field(alias='Email')


class Service(BaseModel):
    id: str = Field(alias='Id')
    name: str = Field(alias='Name')
