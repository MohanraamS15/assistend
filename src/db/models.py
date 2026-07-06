from typing import Optional
from sqlmodel import SQLModel, Field


class SenderIDMapping(SQLModel, table=True):
    __tablename__ = "sender_id_mapping"

    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: str
    sender_entity: str


class SenderIDMappingStaging(SQLModel, table=True):
    __tablename__ = "sender_id_mapping_staging"

    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: str
    sender_entity: str