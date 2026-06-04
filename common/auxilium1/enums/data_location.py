from enum import Enum


class DataLocation(str, Enum):
    LOCAL_FILE = "LOCAL_FILE"
    IN_DATABASE = "IN_DATABASE"
