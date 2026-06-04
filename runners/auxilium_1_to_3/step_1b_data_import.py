import json

from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep


class Step1BDataImport(MigrationStep):
    def __init__(self):
        super().__init__()

    def go(self, target: str) -> bool:
        # file path relative to main.py
        with open(f"cache/{target}.json") as json_file:
            data = json.load(json_file)
            self.write_to_cache_file(target=DumpFile.AUX_1_TO_3_STEP_1_DB_DUMP, data=data)
            return True
