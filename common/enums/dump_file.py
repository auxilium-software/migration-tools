from enum import Enum


class DumpFile(str, Enum):
    AUX_1_TO_3_STEP_1_DB_DUMP = "aux1-3.s1.db-dump"
    AUX_1_TO_3_STEP_2_INDEX = "aux1-3.s2.index"
    AUX_1_TO_3_STEP_3_PROMOTE = "aux1-3.s3.promote_properties"
