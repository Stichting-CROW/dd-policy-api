from enum import Enum

class Modality(str, Enum):
    car = "car"
    cargo_bicycle = "cargo_bicycle"
    bicycle = "bicycle"
    moped = "moped"

DefaultModes = [Modality.bicycle, Modality.moped, Modality.cargo_bicycle]