import os

from dotenv import load_dotenv
from pathlib import Path

from common.auxilium1.common.decryption_manager import DecryptionManager
from common.superclasses.migration_step import MigrationStep


class Step0FileDecryption (MigrationStep):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.decryption_manager = DecryptionManager(
            encryption_key=os.getenv("AUX_1_ENCRYPTION_KEY"),
            encryption_algorithm=os.getenv("AUX_1_ENCRYPTION_ALGORITHM"),
        )

    def go(self) -> None:
        Path(os.getenv(f"AUX_1_DECRYPTED_FILES_DIRECTORY")).mkdir(parents=True, exist_ok=True)

        directory = os.fsencode(os.getenv(f"AUX_1_ENCRYPTED_FILES_DIRECTORY"))

        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith(".bin"):
                with open(os.getenv(f"AUX_1_ENCRYPTED_FILES_DIRECTORY") + f"/{filename}", "rb") as f:
                    encrypted_file_contents = f.read()

                    print(f"{filename}: {len(encrypted_file_contents)} bytes, first 16: {encrypted_file_contents[:16].hex(' ')}")

                    decrypted_file_contents = self.decryption_manager.decrypt_bytes(encrypted_file_contents)
                    with open(os.getenv(f"AUX_1_DECRYPTED_FILES_DIRECTORY") + f"/{filename}", "wb") as f2:
                        f2.write(decrypted_file_contents)
