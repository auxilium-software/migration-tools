import datetime
import hashlib
import json
import uuid

from dotenv import load_dotenv

from common.auxilium1.common.decryption_manager import DecryptionManager
from common.auxilium1.enums.data_location import DataLocation
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep

import os


class Step9DataUpload(MigrationStep):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.indexed_data = {}

    def go(self) -> None:
        self.indexed_data = self.read_cache_file(target=DumpFile.AUX_1_TO_3_STEP_3_PROMOTE)

        print("    deleting existing data")
        for table in (
            "case__cases",
            "user__users",
            "enumerator__enumerators",
            "system__settings",
            "system__metrics",
            "system__bulletin",
        ):
            self.write_to_database(target=3, query=f"DELETE FROM {table};")

        ####################################################################################################
        # CREATE SYSTEM STUFF
        print("    creating system user + settings")
        self.write_to_database(
            target=3,
            query="""
                INSERT INTO user__users
                (
                    id,
                    created_at_utc,
                    email_address,
                    password_hash,
                    full_name,
                    language_preference,
                    has_email_address_been_verified,
                    allow_login,
                    must_change_password,
                    is_case_worker,
                    is_case_worker_manager,
                    is_administrator,
                    totp_enabled,
                    deletion_requested
                )
                VALUES (
                    %(id)s,
                    %(created_at_utc)s,
                    %(email_address)s,
                    %(password_hash)s,
                    %(full_name)s,
                    %(language_preference)s,
                    %(has_email_address_been_verified)s,
                    %(allow_login)s,
                    %(must_change_password)s,
                    %(is_case_worker)s,
                    %(is_case_worker_manager)s,
                    %(is_administrator)s,
                    %(totp_enabled)s,
                    %(deletion_requested)s
                );
                  """,
            args={
                "id":                               uuid.uuid4(),
                "created_at_utc":                   datetime.datetime.utcnow(),
                "email_address":                    os.getenv("AUX_3_ADMIN_EMAIL_ADDRESS"),
                "password_hash":                    os.getenv("AUX_3_ADMIN_PASSWORD_ARGON2"),
                "full_name":                        os.getenv("AUX_3_ADMIN_FULL_NAME"),
                "language_preference":              "en-GB",
                "has_email_address_been_verified":  1,
                "allow_login":                      1,
                "must_change_password":             0,
                "is_case_worker":                   0,
                "is_case_worker_manager":           0,
                "is_administrator":                 1,
                "totp_enabled":                     0,
                "deletion_requested":               0,
            }
        )

        settings_rows = [
            {
                "config_key":   "instance.navigation.portalBaseUrl",
                "config_value": f'"{os.getenv("AUX_3_PORTAL_BASE_URL")}"',
            },
            {
                "config_key":   "instance.branding.name",
                "config_value": f'"{os.getenv("AUX_3_PORTAL_BRANDING_NAME")}"',
            },
            {
                "config_key":   "instance.fqdn",
                "config_value": f'"{os.getenv("AUX_3_PORTAL_FQDN")}"',
            },
        ]
        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO system__settings
                (
                    id,
                    created_at_utc,
                    config_key,
                    value_type,
                    config_value,
                    reason_for_modification
                )
                VALUES (
                    %(id)s,
                    %(created_at_utc)s,
                    %(config_key)s,
                    %(value_type)s,
                    %(config_value)s,
                    %(reason_for_modification)s
                );
                  """,
            args_list=[
                {
                    "id":                       uuid.uuid4(),
                    "created_at_utc":           datetime.datetime.utcnow(),
                    "config_key":               row["config_key"],
                    "value_type":               "json",
                    "config_value":             row["config_value"],
                    "reason_for_modification":  "Generated by Auxilium Migration Tools automatically.",
                }
                for row in settings_rows
            ],
        )

        ####################################################################################################
        # ENUMERATORS
        print("    creating enumerators")
        enumerator_rows = []
        value_rows = []
        translation_rows = []

        for name, enum_details in self.indexed_data["enumeratorDefinitions"].items():
            enum_id = uuid.uuid4()
            enumerator_rows.append({
                "id":               enum_id,
                "created_at_utc":   datetime.datetime.utcnow(),
                "name":             name,
                "description":      None,
                "is_active":        1,
            })

            for sort_order, (option_name, translations) in enumerate(enum_details.items()):
                enum_value_id = uuid.uuid4()

                value_rows.append({
                    "id":               enum_value_id,
                    "created_at_utc":   datetime.datetime.utcnow(),
                    "enum_type_id":     enum_id,
                    "canonical_name":   option_name,
                    "is_active":        1,
                    "sort_order":       sort_order,
                })

                for language_code, translation in translations.items():
                    if translation is None:
                        continue
                    if not language_code.endswith("-GB"):
                        language_code += "-GB"
                    translation_rows.append({
                        "id":                       uuid.uuid4(),
                        "created_at_utc":           datetime.datetime.utcnow(),
                        "data_enumerator_value_id": enum_value_id,
                        "language_code":            language_code,
                        "translation":              translation,
                    })

        if enumerator_rows:
            self.write_many_to_database(
                target=3,
                query="""
                    INSERT INTO enumerator__enumerators
                    (
                        id,
                        created_at_utc,
                        name,
                        description,
                        is_active
                    )
                    VALUES
                    (
                        %(id)s,
                        %(created_at_utc)s,
                        %(name)s,
                        %(description)s,
                        %(is_active)s
                    )
                """,
                args_list=enumerator_rows,
            )

        if value_rows:
            self.write_many_to_database(
                target=3,
                query="""
                    INSERT INTO enumerator__enumerator_values
                    (
                        id,
                        created_at_utc,
                        enum_type_id,
                        canonical_name,
                        is_active,
                        sort_order
                    )
                    VALUES
                    (
                        %(id)s,
                        %(created_at_utc)s,
                        %(enum_type_id)s,
                        %(canonical_name)s,
                        %(is_active)s,
                        %(sort_order)s
                    )
                """,
                args_list=value_rows,
            )

        if translation_rows:
            self.write_many_to_database(
                target=3,
                query="""
                    INSERT INTO enumerator__enumerator_value_translations
                    (
                        id,
                        created_at_utc,
                        data_enumerator_value_id,
                        language_code,
                        translation
                    )
                    VALUES
                    (
                        %(id)s,
                        %(created_at_utc)s,
                        %(data_enumerator_value_id)s,
                        %(language_code)s,
                        %(translation)s
                    )
                """,
                args_list=translation_rows,
            )

        ####################################################################################################
        # USERS + PROPERTIES
        print("    creating users")
        user_rows = []
        property_rows = []
        for user_id, user_data in self.indexed_data["users"].items():
            user_rows.append({
                "id":                                       user_id,
                "created_at_utc":                           user_data["creationTimestamp"],
                "created_by":                               None,
                "last_updated_at_utc":                      None,
                "last_updated_by":                          None,
                "email_address":                            user_data["emailAddress"],
                "password_hash":                            user_data["password"],
                "full_name":                                user_data["fullName"],
                "full_address":                             None,
                "telephone_number":                         user_data["telephoneNumber"],
                "gender":                                   None,
                "date_of_birth":                            self._date_or_none(user_data["dateOfBirth"]),
                "how_did_you_find_out_about_our_service":   None,
                "language_preference":                      "en-GB",
                "has_email_address_been_verified":          1,  # <===== actually verify this lol
                "allow_login":                              1,
                "must_change_password":                     1,  # <===== !!! make sure that everybody knows this is coming !!!
                "is_case_worker":                           0,
                "is_case_worker_manager":                   0,
                "is_administrator":                         0,
                "totp_secret":                              None,
                "totp_enabled":                             0,
                "totp_enabled_at_utc":                      None,
                "deletion_requested":                       0,
                "deletion_request_reason":                  None,
            })

            for property_key, property_value in user_data["additionalProperties"].items():
                if isinstance(property_value, dict):
                    continue
                property_rows.append({
                    "id":                   uuid.uuid4(),
                    "created_at_utc":       user_data["creationTimestamp"],
                    "created_by":           None,
                    "last_updated_at_utc":  None,
                    "last_updated_by":      None,
                    "user_id":              user_id,
                    "original_name":        property_key,
                    "url_slug":             property_key,
                    "content_type":         "text/plain;",  # charset=utf-8",
                    "content":              property_value,
                })

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO user__users
                (
                    id,
                    created_at_utc,
                    created_by,
                    last_updated_at_utc,
                    last_updated_by,
                    email_address,
                    password_hash,
                    full_name,
                    full_address,
                    telephone_number,
                    gender,
                    date_of_birth,
                    how_did_you_find_out_about_our_service,
                    language_preference,
                    has_email_address_been_verified,
                    allow_login,
                    must_change_password,
                    is_case_worker,
                    is_case_worker_manager,
                    is_administrator,
                    totp_secret,
                    totp_enabled,
                    totp_enabled_at_utc,
                    deletion_requested,
                    deletion_request_reason
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by)s,
                    %(email_address)s,
                    %(password_hash)s,
                    %(full_name)s,
                    %(full_address)s,
                    %(telephone_number)s,
                    %(gender)s,
                    %(date_of_birth)s,
                    %(how_did_you_find_out_about_our_service)s,
                    %(language_preference)s,
                    %(has_email_address_been_verified)s,
                    %(allow_login)s,
                    %(must_change_password)s,
                    %(is_case_worker)s,
                    %(is_case_worker_manager)s,
                    %(is_administrator)s,
                    %(totp_secret)s,
                    %(totp_enabled)s,
                    %(totp_enabled_at_utc)s,
                    %(deletion_requested)s,
                    %(deletion_request_reason)s
                );
            """,
            args_list=user_rows,
        )

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO user__additional_properties
                (
                    id,
                    created_at_utc,
                    created_by,
                    last_updated_at_utc,
                    last_updated_by,
                    user_id,
                    original_name,
                    url_slug,
                    content_type,
                    content
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by)s,
                    %(user_id)s,
                    %(original_name)s,
                    %(url_slug)s,
                    %(content_type)s,
                    %(content)s
                );
            """,
            args_list=property_rows,
        )

        ####################################################################################################
        # CASES + CLIENTS + WORKERS
        print("    creating cases")
        case_rows = []
        client_rows = []
        worker_rows = []
        for case_id, case_data in self.indexed_data["cases"].items():
            case_rows.append({
                "id":                   case_id,
                "created_at_utc":       case_data["creationTimestamp"],
                "created_by":           None,
                "last_updated_at_utc":  None,
                "last_updated_by":      None,
                "title":                case_data["caseTitle"],
                "description":          case_data["caseDescription"],
                "sensitivity":          "confidential",
                "status":               "open",
            })

            for user_id in case_data["subjects"]:
                client_rows.append({
                    "id":               uuid.uuid4(),
                    "created_at_utc":   case_data["creationTimestamp"],
                    "created_by":       None,
                    "case_id":          case_id,
                    "user_id":          user_id,
                })

            for user_id in case_data["representatives"]:
                worker_rows.append({
                    "id":               uuid.uuid4(),
                    "created_at_utc":   case_data["creationTimestamp"],
                    "created_by":       None,
                    "case_id":          case_id,
                    "user_id":          user_id,
                })

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO case__cases
                (
                    id,
                    created_at_utc,
                    created_by,
                    last_updated_at_utc,
                    last_updated_by,
                    title,
                    description,
                    sensitivity,
                    status
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by)s,
                    %(title)s,
                    %(description)s,
                    %(sensitivity)s,
                    %(status)s
                );
            """,
            args_list=case_rows,
        )

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO case__clients
                (
                    id,
                    created_at_utc,
                    created_by,
                    case_id,
                    user_id
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by)s,
                    %(case_id)s,
                    %(user_id)s
                );
            """,
            args_list=client_rows,
        )

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO case__workers
                (
                    id,
                    created_at_utc,
                    created_by,
                    case_id,
                    user_id
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by)s,
                    %(case_id)s,
                    %(user_id)s
                );
            """,
            args_list=worker_rows,
        )

    def _date_or_none(self, value):
        if value is None or value == "":
            return None
        try:
            return datetime.datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError:
            pass
        try:
            return datetime.datetime.fromisoformat(value).date()
        except ValueError:
            pass
        print(f"        unparseable DOB: {value!r} -> NULL")
        return None
