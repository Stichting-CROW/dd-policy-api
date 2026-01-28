from enum import Enum

class Modality(str, Enum):
    car = "car"
    cargo_bicycle = "cargo_bicycle"
    bicycle = "bicycle"
    moped = "moped"
    unknown = "unknown"

DefaultModes = [Modality.bicycle, Modality.moped, Modality.cargo_bicycle]


class PropulsionType(str, Enum):
    human = "human"
    electric_assist = "electric_assist"
    electric = "electric"
    combustion = "combustion"
    unknown = "unknown"

    