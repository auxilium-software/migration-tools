import base64
import json

from dotenv import load_dotenv

from common.auxilium1.common.decryption_manager import DecryptionManager
from common.auxilium1.enums.data_location import DataLocation
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep

import os


class Step1DbDump(MigrationStep):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.decryption_manager = DecryptionManager(
            encryption_key=os.getenv("AUX_1_ENCRYPTION_KEY"),
            encryption_algorithm=os.getenv("AUX_1_ENCRYPTION_ALGORITHM"),
        )
        self.builder = {}

    def read_query_builder(self, column: str, as_name: str):
        # return f"BIN_TO_UUID({column}, 1) AS {as_name}"
        return (
            f"LOWER(CONCAT("
            f"SUBSTR(HEX({column}), 9, 8), '-', "
            f"SUBSTR(HEX({column}), 5, 4), '-', "
            f"SUBSTR(HEX({column}), 1, 4), '-', "
            f"SUBSTR(HEX({column}), 17, 4), '-', "
            f"SUBSTR(HEX({column}), 21, 12)"
            f")) AS {as_name}"
        )

    def utf8ize(self, mixed):
        if isinstance(mixed, dict):
            return {k: self.utf8ize(v) for k, v in mixed.items()}
        if isinstance(mixed, list):
            return [self.utf8ize(v) for v in mixed]
        if isinstance(mixed, bytes):
            return mixed.decode("utf-8", errors="replace")
        if isinstance(mixed, str):
            return mixed.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        return mixed

    def safe_binary_to_string(self, data):
        if isinstance(data, bytes):
            if b"\x00" in data:
                return base64.b64encode(data).decode("ascii")
            return self.utf8ize(data.decode("utf-8", errors="replace"))
        if isinstance(data, str):
            if "\x00" in data:
                return base64.b64encode(data.encode("utf-8")).decode("ascii")
            return self.utf8ize(data)
        return data


    def go(self):
        db_users = self.read_from_database(1, f"SELECT *,{self.read_query_builder("user_uuid", "user_uuid_decoded")} FROM users;")
        db_cases = self.read_from_database(1, f"SELECT *,{self.read_query_builder("case_uuid", "case_uuid_decoded")} FROM cases;")
        db_data_pointers = self.read_from_database(
            1,
            f"""
            SELECT
                *,
                {self.read_query_builder("data_uuid", "data_uuid_decoded")},
                {self.read_query_builder("previous_version_uuid", "previous_version_uuid_decoded")},
                {self.read_query_builder("owner_uuid", "owner_uuid_decoded")}
                FROM data_pointers;
            """)
        db_relations = self.read_from_database(
            1,
            f"""
            SELECT
                *,
                {self.read_query_builder("is_uuid", "is_uuid_decoded")},
                {self.read_query_builder("of_uuid", "of_uuid_decoded")}
                FROM relations;
            """)
        db_enum_definitions = self.read_from_database(1, f"SELECT * FROM enum_definitions;")

        index_users = {}
        index_cases = {}
        index_relations = []
        index_data_pointers = {}
        index_enum_definitions = {}

        for user_details in db_users:
            index_users[user_details["user_uuid_decoded"]] = {
                "fullName":                 self.utf8ize(user_details["full_name"]),
                "emailAddress":             self.utf8ize(user_details["email_address"]),
                "password":                 self.utf8ize(user_details["password"]),
                "notificationPreferences":  self.utf8ize(user_details["notification_preferences"]),
                "accountType":              self.utf8ize(user_details["account_type"]),
                "active":                   user_details["active"],
                "creationTimestamp":        user_details["creation_timestamp"].isoformat(),
            }
        for case_details in db_cases:
            index_cases[case_details["case_uuid_decoded"]] = {
                "caseTitle":            self.utf8ize(case_details["case_title"]),
                "sensitivity":          self.utf8ize(case_details["sensitivity"]),
                "creationTimestamp":    case_details["creation_timestamp"].isoformat(),
                "lastUpdateTimestamp":  case_details["last_update_timestamp"].isoformat(),
                "status":               self.utf8ize(case_details["status"]),
            }
        for relation_details in db_relations:
            index_relations.append({
                "isUuid":       relation_details["is_uuid_decoded"],
                "relationType": self.utf8ize(relation_details["relation_type"]),
                "pointsTo":     relation_details["of_uuid_decoded"],
            })
        for data_pointer_details in db_data_pointers:
            if data_pointer_details["data_location"] == DataLocation.LOCAL_FILE.value:
                data_access = data_pointer_details["data_access"]
            elif data_pointer_details["data_location"] == DataLocation.IN_DATABASE.value:
                data_access = self.decryption_manager.decrypt(data_pointer_details["data_access"])
            else:
                raise Exception(f"DataLocation: {data_pointer_details['data_location']} not found in DataLocation enum")

            index_data_pointers[data_pointer_details["data_uuid_decoded"]] = {
                "previousVersionUuid":  data_pointer_details["previous_version_uuid_decoded"],
                "historical":           data_pointer_details["historical"],
                "dataType":             self.utf8ize(data_pointer_details["data_type"]),
                "objectSchema":         self.utf8ize(data_pointer_details["object_schema"]),
                "mimeType":             self.utf8ize(data_pointer_details["mime_type"]),
                "flags":                self.utf8ize(data_pointer_details["flags"]),
                "objectSize":           data_pointer_details["object_size"],
                "dataLocation":         self.utf8ize(data_pointer_details["data_location"]),
                "dataAccess":           self.safe_binary_to_string(data_access),
                "ownerUuid":            data_pointer_details["owner_uuid_decoded"],
                "documentDate":         data_pointer_details["document_date"].isoformat(),
                "creationTimestamp":    data_pointer_details["creation_timestamp"].isoformat(),
            }
        for enum_definition_details in db_enum_definitions:
            index_enum_definitions[enum_definition_details["enum_name"]] = json.loads(enum_definition_details["enum_json_object"])

        self.builder = {
            "users": index_users,
            "cases": index_cases,
            "relations": index_relations,
            "dataPointers": index_data_pointers,
            "enumeratorDefinitions": index_enum_definitions,
        }
        self.write_to_cache_file(target=DumpFile.AUX_1_TO_3_STEP_1_DB_DUMP, data=self.builder)
