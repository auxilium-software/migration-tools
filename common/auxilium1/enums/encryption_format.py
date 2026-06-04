from enum import Enum


class EncryptionFormat(str, Enum):
    JSON = '{'
    PACK = 'p'
