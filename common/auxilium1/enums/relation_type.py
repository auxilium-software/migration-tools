from enum import Enum


class RelationType(str, Enum):
    MEMBER = "MEMBER"
    ASSIGNED = "ASSIGNED"
    SENDER = "SENDER"
    SUBJECT = "SUBJECT"
    RECIPIENT = "RECIPIENT"
    ABOUT = "ABOUT"
