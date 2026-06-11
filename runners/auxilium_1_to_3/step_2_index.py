from common.auxilium1.enums.data_type import DataType
from common.auxilium1.enums.relation_type import RelationType
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep


class Step2Index (MigrationStep):
    def __init__(self):
        super().__init__()

        self.unprocessed_data = {}
        self.builder = {}


    def process_data_pointers(self):
        for data_uuid, data_pointer_details in self.unprocessed_data["dataPointers"].items():
            if data_pointer_details["ownerUuid"] is None:
                continue

            elif data_pointer_details['ownerUuid'] in self.builder["users"]:
                if data_pointer_details['historical'] == 1:
                    continue

                self.builder["users"][data_pointer_details['ownerUuid']]["dataPointers"][data_pointer_details['dataType']] = {
                    "objectSchema": data_pointer_details["objectSchema"],
                    "mimeType": data_pointer_details["mimeType"],
                    "flags": data_pointer_details["flags"],
                    "objectSize": data_pointer_details["objectSize"],
                    "dataLocation": data_pointer_details["dataLocation"],
                    "dataAccess": data_pointer_details["dataAccess"],
                    "documentDate": data_pointer_details["documentDate"],
                    "creationTimestamp": data_pointer_details["creationTimestamp"],
                }

            elif data_pointer_details['ownerUuid'] in self.builder["cases"]:
                if data_pointer_details['historical'] == 1:
                    continue

                self.builder["cases"][data_pointer_details['ownerUuid']]["dataPointers"][data_pointer_details['dataType']] = {
                    "objectSchema": data_pointer_details["objectSchema"],
                    "mimeType": data_pointer_details["mimeType"],
                    "flags": data_pointer_details["flags"],
                    "objectSize": data_pointer_details["objectSize"],
                    "dataLocation": data_pointer_details["dataLocation"],
                    "dataAccess": data_pointer_details["dataAccess"],
                    "documentDate": data_pointer_details["documentDate"],
                    "creationTimestamp": data_pointer_details["creationTimestamp"],
                }

            else:
                print(f"    Data pointer {data_uuid} has owner UUID: {data_pointer_details['ownerUuid']} not found in users or cases")

    def process_relations(self):
        for relation_details in self.unprocessed_data["relations"]:
            is_uuid = relation_details["isUuid"]
            relation_type = relation_details["relationType"]
            points_to = relation_details["pointsTo"]

            if is_uuid in self.builder["users"] and points_to in self.builder["cases"]:
                if relation_type == RelationType.ASSIGNED.value:
                    self.builder["cases"][points_to]["assignments"].append(is_uuid)
                elif relation_type == RelationType.SUBJECT.value:
                    self.builder["cases"][points_to]["subjects"].append(is_uuid)
                elif relation_type == RelationType.REPRESENTATIVE.value:
                    self.builder["cases"][points_to]["representatives"].append(is_uuid)
                else:
                    raise Exception(f"Unhandled user→case relation type: {relation_type!r}")

            elif is_uuid in self.builder["cases"]:
                if relation_type == RelationType.MEMBER.value:
                    self.builder["cases"][is_uuid]["members"].append(points_to)
                elif relation_type == RelationType.RECIPIENT.value:
                    self.builder["cases"][is_uuid]["recipients"].append(points_to)
                elif relation_type == RelationType.REPRESENTATIVE.value:
                    self.builder["cases"][is_uuid]["representatives"].append(points_to)
                elif relation_type == RelationType.SENDER.value:
                    self.builder["cases"][is_uuid]["senders"].append(points_to)
                else:
                    raise Exception(f"Unhandled case relation type: {relation_type!r}")

            else:
                print(f"    Relation {is_uuid} → {points_to} not found in users or cases")

    def process_communications(self):
        pass

    def process_enumerators(self):
        self.builder["enumeratorDefinitions"] = self.unprocessed_data["enumeratorDefinitions"]


    def go(self):
        self.unprocessed_data = self.read_cache_file(target=DumpFile.AUX_1_TO_3_STEP_1_DB_DUMP)

        self.builder = {
            "users": self.unprocessed_data["users"],
            "cases": self.unprocessed_data["cases"],
            "communications": {},
            "enumeratorDefinitions": {},
        }

        for _, user_details in self.builder["users"].items():
            user_details["dataPointers"] = {}

        for _, case_details in self.builder["cases"].items():
            case_details["dataPointers"]    = {}
            case_details["assignments"]     = []
            case_details["subjects"]        = []
            case_details["representatives"] = []
            case_details["members"]         = []
            case_details["recipients"]      = []
            case_details["senders"]         = []

        self.process_data_pointers()
        self.process_relations()
        self.process_communications()
        self.process_enumerators()

        self.write_to_cache_file(target=DumpFile.AUX_1_TO_3_STEP_2_INDEX, data=self.builder)


