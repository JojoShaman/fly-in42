from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class Type(Enum):
    normal = 1
    blocked = 2
    restricted = 3
    priority = 4

class Metadata(BaseModel):
    zone: Type = Field(default=Type.normal)
    color: str = Field(default="none")
    max_drones: int = Field(default=1)

class ConnectionMetadata(BaseModel):
    max_link_capacity: int = Field(default=1)

class Hub(BaseModel):
    name: str = Field(default="hub")
    x: int
    y: int
    nb_drones: int = Field(default=0)
    meta_data: Metadata

    @field_validator('name')
    @classmethod
    def name_validator(cls, name: str) -> str:
        if '-' in name:
            raise ValueError("dashes in names are forbidden")
        return name

class Connection(BaseModel):
    name1: str = Field(min_length=0)
    name2: str = Field(min_length=0)
    meta_data: ConnectionMetadata

class Data(BaseModel):
        nb_drones: int = Field(gt=0)
        start_hub: Hub
        hub: list[Hub] = Field(default_factory=list)
        end_hub: Hub
        connection: list[Connection] = Field(default_factory=list)
        total_hubs: list[Hub] = Field(default_factory=list)
