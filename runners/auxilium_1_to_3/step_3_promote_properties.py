import json

from common.auxilium1.enums.data_type import DataType
from common.auxilium1.enums.object_schema import ObjectSchema
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep


def _to_locale(data_pointer_id: str, data_pointer_details: str, raw: str):
    return json.loads(raw)["value"].lower() + "-GB"

def _to_consent_bool(data_pointer_id: str, data_pointer_details: str, raw: str):
    return json.loads(raw)["value"] == "YES"

def _to_wemwbs(data_pointer_id: str, data_pointer_details: str, raw: str):
    temp = {k: int(v) for k, v in json.loads(raw).items()}
    temp["@id"] = data_pointer_id
    temp["@creationTimestamp"] = data_pointer_details["creationTimestamp"]
    return temp

def _to_dict(data_pointer_id: str, data_pointer_details: str, raw: str):
    temp = {
        k: v for k, v in json.loads(raw).items()
    }
    temp["@id"] = data_pointer_id
    temp["@type"] = "enum-json-v1"
    temp["@creationTimestamp"] = data_pointer_details["creationTimestamp"]
    return temp

TRANSFORMS = {
    DataType.LANGUAGE_PREFERENCE.value:         _to_locale,

    DataType.CASE_STUDY_CONSENT.value:          _to_dict,
    DataType.RESEARCH_CONTACT_CONSENT.value:    _to_dict,

    DataType.WEMWBS.value:                      _to_wemwbs,

    DataType.EMPLOYMENT_DETAILS.value:          _to_dict,
    DataType.MILITARY_SERVICE.value:            _to_dict,
    DataType.RELATIONSHIP_STATUS.value:         _to_dict,
    DataType.MILITARY_SERVICE_STATUS.value:     _to_dict,
    DataType.USER_TYPE.value:                   _to_dict,
    DataType.TIMEZONE_PREFERENCE.value:         _to_dict,
}

# first-class fields: always present at root, default None.
# enum-json data types are NOT here any more -> they go to dataEnumerators.
USER_ROOT_FIELDS = {
    DataType.LANGUAGE_PREFERENCE.value: "languagePreference",
    DataType.HOME_ADDRESS.value: "fullAddress",
    DataType.PHONE_NUMBER.value: "telephoneNumber",
    DataType.DATE_OF_BIRTH.value: "dateOfBirth",
    DataType.WEMWBS.value: "wemwbs",
}

CASE_ROOT_FIELDS = {
    DataType.BRIEF_DESCRIPTION.value: "caseBriefDescription",
    DataType.CASE_DESCRIPTION.value:  "caseDescription",

    DataType.CASE_REFERRER.value: "caseReferrer",
}

# scalar "properties": promote to root fields / dataEnumerators / additionalProperties
SCALAR_SCHEMAS = {
    ObjectSchema.TEXT.value,
    ObjectSchema.TEXT_ISO_DATE.value,
    ObjectSchema.ENUM_JSON_V1.value,
    ObjectSchema.WEMWBS_JSON_V1.value,
}

# binary attachments -> entity["files"]
FILE_SCHEMAS = {
    ObjectSchema.FILE.value,
    ObjectSchema.IMAGE.value,
    ObjectSchema.AUDIO.value,
    ObjectSchema.VIDEO.value,
}

# communications -> entity["messages"]
MESSAGE_SCHEMAS = {
    ObjectSchema.MESSAGE_JSON_V1.value,
    ObjectSchema.EMAIL_JSON_V1.value,
    ObjectSchema.RFC822.value,
}

# timeline notes -> entity["timeline"]
TIMELINE_SCHEMAS = {
    ObjectSchema.TIMELINE_NOTE_JSON_V1.value,
}

TODO_SCHEMAS = {
    ObjectSchema.TODO_JSON_V1.value,
}
ASSIGNMENT_SCHEMAS = {
    ObjectSchema.ASSIGNMENT_RECORD_JSON_V1.value,
}



class Step3PromoteProperties(MigrationStep):
    def __init__(self):
        super().__init__()
        self.builder = {}

    @staticmethod
    def _process(entity: dict, root_fields: dict) -> None:
        # pop so dataPointers is gone from the entity once we're done
        data_pointers = entity.pop("dataPointers")

        additional = {}
        data_enumerators = {}
        files = {}
        messages = {}
        timeline = {}
        todo = {}
        assignment_record = {}

        # every first-class field exists, even if the source had no value
        for field in root_fields.values():
            entity[field] = None

        for pointer_id, pointer_details in data_pointers.items():
            schema = pointer_details["objectSchema"]
            data_type = pointer_details["dataType"]

            if schema in SCALAR_SCHEMAS:
                value = pointer_details["dataAccess"]
                transform = TRANSFORMS.get(data_type)
                if transform is not None:
                    value = transform(pointer_id, pointer_details, value)

                if isinstance(value, dict) and value.get("@type") == "enum-json-v1":
                    data_enumerators[data_type] = value
                elif data_type in root_fields:
                    entity[root_fields[data_type]] = value
                else:
                    additional[data_type] = value

            elif schema in FILE_SCHEMAS:
                files[pointer_id] = pointer_details
            elif schema in MESSAGE_SCHEMAS:
                messages[pointer_id] = pointer_details
            elif schema in TIMELINE_SCHEMAS:
                timeline[pointer_id] = pointer_details
            elif schema in TODO_SCHEMAS:
                todo[pointer_id] = pointer_details
            elif schema in ASSIGNMENT_SCHEMAS:
                assignment_record[pointer_id] = pointer_details
            else:
                raise ValueError(
                    f"unhandled objectSchema {schema!r} on pointer {pointer_id!r} "
                    f"(dataType {data_type!r})"
                )

        entity["additionalProperties"] = additional
        entity["dataEnumerators"] = data_enumerators
        entity["files"] = files
        entity["messages"] = messages
        entity["timeline"] = timeline
        entity["todo"] = todo
        entity["assignmentRecords"] = assignment_record

    def go(self) -> None:
        live_data = self.read_cache_file(target=DumpFile.AUX_1_TO_3_STEP_2_INDEX)
        self.builder = {
            "users": live_data["users"],
            "cases": live_data["cases"],
            "communications": live_data["communications"],
            "enumeratorDefinitions": live_data["enumeratorDefinitions"],
        }

        for user_details in self.builder["users"].values():
            self._process(user_details, USER_ROOT_FIELDS)
        for case_details in self.builder["cases"].values():
            self._process(case_details, CASE_ROOT_FIELDS)

        self.write_to_cache_file(target=DumpFile.AUX_1_TO_3_STEP_3_PROMOTE, data=self.builder)
