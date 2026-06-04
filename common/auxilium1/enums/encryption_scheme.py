from enum import Enum


class EncryptionScheme(str, Enum):
    JSON = "JSON"
    PACK = "PACK"
