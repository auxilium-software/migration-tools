import json

from common.auxilium1.enums.data_type import DataType
from common.auxilium1.enums.object_schema import ObjectSchema
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep


# transforms applied to dataAccess regardless of where the value lands

def _to_locale(raw: str):
    return json.loads(raw)["value"].lower() + "-GB"

def _to_consent_bool(raw: str):
    return json.loads(raw)["value"] == "YES"

def _to_wemwbs(raw: str):
    return {k: int(v) for k, v in json.loads(raw).items()}

def _to_dict(raw: str):
    temp = {
        k: v for k, v in json.loads(raw).items()
    }
    temp["@type"] = "enum-json-v1"
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

# first-class fields: always present at root, default None

USER_ROOT_FIELDS = {
    DataType.LANGUAGE_PREFERENCE.value: "languagePreference",
    DataType.HOME_ADDRESS.value: "fullAddress",
    DataType.PHONE_NUMBER.value: "telephoneNumber",
    DataType.DATE_OF_BIRTH.value: "dateOfBirth",
}

CASE_ROOT_FIELDS = {
    DataType.BRIEF_DESCRIPTION.value: "caseBriefDescription",
    DataType.CASE_DESCRIPTION.value:  "caseDescription",
}

# object schemas that are scalar "properties" and fold into additionalProperties.
# anything else (FILE, IMAGE, AUDIO, MESSAGE_JSON_V1, ...) is left in dataPointers.
SCALAR_SCHEMAS = {
    ObjectSchema.TEXT.value,
    ObjectSchema.TEXT_ISO_DATE.value,
    ObjectSchema.ENUM_JSON_V1.value,
    ObjectSchema.WEMWBS_JSON_V1.value,
}


class Step3PromoteProperties(MigrationStep):
    def __init__(self):
        super().__init__()
        self.builder = {}

    @staticmethod
    def _promote(entity: dict, root_fields: dict) -> None:
        data_pointers = entity["dataPointers"]
        additional = {}

        # every first-class field exists, even if the source had no value
        for field in root_fields.values():
            entity[field] = None

        for pointer_id, pointer_details in list(data_pointers.items()):
            if pointer_details["objectSchema"] not in SCALAR_SCHEMAS:
                continue  # attachments stay in dataPointers

            data_type = pointer_details["dataType"]

            value = pointer_details["dataAccess"]
            transform = TRANSFORMS.get(data_type)
            if transform is not None:
                value = transform(value)

            if data_type in root_fields:
                entity[root_fields[data_type]] = value
            else:
                additional[data_type] = value

            del data_pointers[pointer_id]

        entity["additionalProperties"] = additional

    def go(self) -> None:
        live_data = self.read_cache_file(target=DumpFile.AUX_1_TO_3_STEP_2_INDEX)
        self.builder = {
            "users": live_data["users"],
            "cases": live_data["cases"],
            "communications": live_data["communications"],
            "enumeratorDefinitions": live_data["enumeratorDefinitions"],
        }

        for user_details in self.builder["users"].values():
            self._promote(user_details, USER_ROOT_FIELDS)
        for case_details in self.builder["cases"].values():
            self._promote(case_details, CASE_ROOT_FIELDS)

        self.write_to_cache_file(target=DumpFile.AUX_1_TO_3_STEP_3_PROMOTE, data=self.builder)
