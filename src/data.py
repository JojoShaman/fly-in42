from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Type(Enum):
    """Enumerate hub zone type.

    Attributes:
        normal: Standard zone with 1 turn movement cost (default)
        blocked: Inaccessible zone. Drones must not enter or
             pass through this zone. Any path using it is invalid.
        restricted: A sensitive or dangerous zone. Movement to
             this zone costs 2 turns.
        priority: A preferred zone. Movement to this zone costs 1 turn
            but should be prioritized in pathfinding.
    """

    normal = 1
    blocked = 2
    restricted = 3
    priority = 4


class Metadata(BaseModel):
    """Data structure for hub metadata.

    Attributes:
        zone: Either normal, blocked, restricted or priority, default normal.
        color: Color name from the map file or none when unspecified.
        max_drones: Number of drones allowed on the hub at the same time.
    """

    zone: Type = Field(default=Type.normal)
    color: str = Field(default="none")
    max_drones: int = Field(default=1, ge=1)


class ConnectionMetadata(BaseModel):
    """Data structure comprising hub links.

    Attributes:
        max_link_capacity: Number of drones allowed on the
         connection at the same time.
    """

    max_link_capacity: int = Field(default=1, ge=1)


class Hub(BaseModel):
    """Data structure comprising hub information.

    Attributes:
        name: Name of the hub.
        x: Horizontal position in map.
        y: Vertical position in map.
        nb_drones: Number of drones on the hub currently.
        meta_data: Details about the hub.

    Raises:
        ValidationError: if the name contains dashes.
    """

    name: str = Field(min_length=1)
    x: int
    y: int
    nb_drones: int = Field(default=0)
    meta_data: Metadata

    @field_validator("name")
    @classmethod
    def name_validator(cls, name: str) -> str:
        """Reject name if dash is found.
        Returns:
            str: name if valid.
        """
        if "-" in name:
            raise ValueError("dashes in names are forbidden")
        return name


class Connection(BaseModel):
    """Data structure comprising information about the link.

    Attributes:
        name1: Name of the hub the link starts from.
        name2: Name of the hub the link ends.
        meta_data: Details about the link.
    """

    name1: str = Field(min_length=1)
    name2: str = Field(min_length=1)
    meta_data: ConnectionMetadata


class Data(BaseModel):
    """Main data structure comprising information on the current map.

    Attributes:
        nb_drones: Number of drones on the map.
        start_hub: Starting hub data.
        hub: list Containing all the intermediate hubs and their information.
        end_hub: End hub data.
        connection: List containing all connections and their information.
        total_hubs: List containing all hubs including start and end, in file
         order.
    """

    nb_drones: int = Field(gt=0)
    start_hub: Hub
    hub: list[Hub] = Field(default_factory=list)
    end_hub: Hub
    connection: list[Connection] = Field(default_factory=list)
    total_hubs: list[Hub] = Field(default_factory=list)
