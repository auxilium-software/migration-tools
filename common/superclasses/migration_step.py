import json
import os
from dotenv import load_dotenv
import pymysql

from common.auxilium1.enums.data_location import DataLocation
from common.enums.dump_file import DumpFile


class MigrationStep:
    def __init__(self):
        load_dotenv()

    def read_from_database(self, target: int, query: str, args: tuple = None):
        try:
            conn = pymysql.connect(
                host=os.getenv(f"AUX_{target}_MARIADB_HOSTNAME"),
                user=os.getenv(f"AUX_{target}_MARIADB_USERNAME"),
                password=os.getenv(f"AUX_{target}_MARIADB_PASSWORD"),
                db=os.getenv(f"AUX_{target}_MARIADB_DATABASE"),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

            with conn.cursor() as cursor:
                cursor.execute(query, args)

            return cursor.fetchall()
        finally:
            conn.close()

    def write_to_database(self, target: int, query: str, args: dict = {}):
        try:
            conn = pymysql.connect(
                host=os.getenv(f"AUX_{target}_MARIADB_HOSTNAME"),
                user=os.getenv(f"AUX_{target}_MARIADB_USERNAME"),
                password=os.getenv(f"AUX_{target}_MARIADB_PASSWORD"),
                db=os.getenv(f"AUX_{target}_MARIADB_DATABASE"),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

            with conn.cursor() as cursor:
                cursor.execute(query, args)

            conn.commit()
        finally:
            conn.close()

    def write_many_to_database(self, target: int, query: str, args_list: list, chunk_size: int = 500) -> None:
        if not args_list:
            return

        query = query.strip().rstrip(";")
        conn = pymysql.connect(
            host=os.getenv(f"AUX_{target}_MARIADB_HOSTNAME"),
            user=os.getenv(f"AUX_{target}_MARIADB_USERNAME"),
            password=os.getenv(f"AUX_{target}_MARIADB_PASSWORD"),
            db=os.getenv(f"AUX_{target}_MARIADB_DATABASE"),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            with conn.cursor() as cursor:
                for i in range(0, len(args_list), chunk_size):
                    cursor.executemany(query, args_list[i:i + chunk_size])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def read_cache_file(self, target: DumpFile):
        # file path relative to main.py
        with open(f"cache/{target.value}.json") as json_file:
            return json.load(json_file)

    def write_to_cache_file(self, target: DumpFile, data: dict):
        # file path relative to main.py
        with open(f"cache/{target.value}.json", "w") as json_file:
            json.dump(data, json_file, indent=4, sort_keys=False)

    def grab_data_from_data_location_automatically(self, data_location: DataLocation, data_access: str):
        if data_location == DataLocation.LOCAL_FILE:
            return data_access
        return "UwU"
