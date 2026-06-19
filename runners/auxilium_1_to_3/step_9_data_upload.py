import datetime
import uuid

from dotenv import load_dotenv

from common.auxilium1.common.decryption_manager import DecryptionManager
from common.auxilium1.enums.data_location import DataLocation
from common.auxilium1.enums.object_schema import ObjectSchema
from common.enums.dump_file import DumpFile
from common.superclasses.migration_step import MigrationStep

import os


class Step9DataUpload(MigrationStep):
    ENUM_REF_CONTENT_TYPE = "application/x-auxilium-data-enumumerator-value-id"

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

        enum_value_index = {}

        for name, enum_details in self.indexed_data["enumeratorDefinitions"].items():
            enum_id = uuid.uuid4()
            enum_value_index[name] = {}
            enumerator_rows.append({
                "id":               enum_id,
                "created_at_utc":   datetime.datetime.utcnow(),
                "canonical_name":   name,
                "description":      None,
                "is_active":        1,
            })

            for sort_order, (option_name, translations) in enumerate(enum_details.items()):
                enum_value_id = uuid.uuid4()
                enum_value_index[name][option_name] = enum_value_id

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
                        canonical_name,
                        description,
                        is_active
                    )
                    VALUES
                    (
                        %(id)s,
                        %(created_at_utc)s,
                        %(canonical_name)s,
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
        wemwbs_rows = []
        unresolved_enum_refs = 0

        for user_id, user_data in self.indexed_data["users"].items():
            user_rows.append({
                "id":                                       user_id,
                "created_at_utc":                           user_data["creationTimestamp"],
                "created_by_user_id":                       None,
                "last_updated_at_utc":                      None,
                "last_updated_by_user_id":                  None,
                "email_address":                            user_data["emailAddress"],
                "password_hash":                            user_data["password"],
                "full_name":                                user_data["fullName"],
                "full_address":                             None,
                "telephone_number":                         user_data["telephoneNumber"],
                "gender":                                   None,
                "date_of_birth":                            self._date_or_none(user_data["dateOfBirth"]),
                "how_did_you_find_out_about_our_service":   None,
                "language_preference":                      "en-GB",
                "has_email_address_been_verified":          1,  # <===== actually verify this
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
                # enum property
                if isinstance(property_value, dict):
                    if property_value.get("@type") != "enum-json-v1":
                        continue

                    enum_name = property_value.get("type")
                    enum_option = property_value.get("value")

                    if enum_option is None:
                        continue

                    value_uuid = enum_value_index.get(enum_name, {}).get(enum_option)
                    if value_uuid is None:
                        print(
                            f"        unresolved enum ref on user {user_id}: "
                            f"{property_key} -> {enum_name}={enum_option!r} "
                            f"(no matching enumerator value) -> SKIP"
                        )
                        unresolved_enum_refs += 1
                        continue

                    property_rows.append({
                        "id":                       uuid.uuid4(),
                        "created_at_utc":           user_data["creationTimestamp"],
                        "created_by_user_id":       None,
                        "last_updated_at_utc":      None,
                        "last_updated_by_user_id":  None,
                        "user_id":                  user_id,
                        "original_name":            property_key,
                        "url_slug":                 property_key,
                        "content_type":             self.ENUM_REF_CONTENT_TYPE,
                        "content":                  str(value_uuid),
                    })
                    continue

                # scalar property
                property_rows.append({
                    "id":                       uuid.uuid4(),
                    "created_at_utc":           user_data["creationTimestamp"],
                    "created_by_user_id":       None,
                    "last_updated_at_utc":      None,
                    "last_updated_by_user_id":  None,
                    "user_id":                  user_id,
                    "original_name":            property_key,
                    "url_slug":                 property_key,
                    "content_type":             "text/plain;",  # charset=utf-8",
                    "content":                  property_value,
                })
            wemwbs_data = user_data.get("wemwbs")
            if wemwbs_data is not None:
                wemwbs_rows.append({
                    "id":                               wemwbs_data["@id"],
                    "created_at_utc":                   wemwbs_data["@creationTimestamp"],
                    "created_by_user_id":               user_id,
                    "user_id":                          user_id,
                    "optimism_score":                   wemwbs_data["optimism"],
                    "usefulness_score":                 wemwbs_data["usefulness"],
                    "relaxed_score":                    wemwbs_data["relaxed"],
                    "interested_in_people_score":       wemwbs_data["interested_in_people"],
                    "spare_energy_score":               wemwbs_data["spare_energy"],
                    "problem_handling_score":           wemwbs_data["problem_handling"],
                    "clear_thought_score":              wemwbs_data["clear_thought"],
                    "feeling_good_self_score":          wemwbs_data["feeling_good_self"],
                    "feeling_close_to_people_score":    wemwbs_data["feeling_close_to_people"],
                    "confidence_score":                 wemwbs_data["confidence"],
                    "making_up_own_mind_score":         wemwbs_data["make_up_own_mind"],
                    "feeling_loved_score":              wemwbs_data["feeling_loved"],
                    "interested_in_new_things_score":   wemwbs_data["interested_in_new_things"],
                    "feeling_cheerful_score":           wemwbs_data["feeling_cheerful"],
                })

        if unresolved_enum_refs:
            print(f"    WARNING: {unresolved_enum_refs} enum reference(s) could not be resolved and were skipped")

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO user__users
                (
                    id,
                    created_at_utc,
                    created_by_user_id,
                    last_updated_at_utc,
                    last_updated_by_user_id,
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
                    %(created_by_user_id)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by_user_id)s,
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
                    created_by_user_id,
                    last_updated_at_utc,
                    last_updated_by_user_id,
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
                    %(created_by_user_id)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by_user_id)s,
                    %(user_id)s,
                    %(original_name)s,
                    %(url_slug)s,
                    %(content_type)s,
                    %(content)s
                );
            """,
            args_list=property_rows,
        )

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO user__wemwbs_assessments
                (
                    id,
                    created_at_utc,
                    created_by_user_id,
                    UserId,
                    optimism_score,
                    usefulness_score,
                    relaxed_score,
                    interested_in_people_score,
                    spare_energy_score,
                    problem_handling_score,
                    clear_thought_score,
                    feeling_good_self_score,
                    feeling_close_to_people_score,
                    confidence_score,
                    making_up_own_mind_score,
                    feeling_loved_score,
                    interested_in_new_things_score,
                    feeling_cheerful_score
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by_user_id)s,
                    %(user_id)s,
                    %(optimism_score)s,
                    %(usefulness_score)s,
                    %(relaxed_score)s,
                    %(interested_in_people_score)s,
                    %(spare_energy_score)s,
                    %(problem_handling_score)s,
                    %(clear_thought_score)s,
                    %(feeling_good_self_score)s,
                    %(feeling_close_to_people_score)s,
                    %(confidence_score)s,
                    %(making_up_own_mind_score)s,
                    %(feeling_loved_score)s,
                    %(interested_in_new_things_score)s,
                    %(feeling_cheerful_score)s
                );
            """,
            args_list=wemwbs_rows,
        )










        ####################################################################################################
        # CASES + CLIENTS + WORKERS
        print("    creating cases")
        case_rows = []
        client_rows = []
        worker_rows = []
        timeline_rows = []
        for case_id, case_data in self.indexed_data["cases"].items():
            case_rows.append({
                "id":                       case_id,
                "created_at_utc":           case_data["creationTimestamp"],
                "created_by_user_id":       None,
                "last_updated_at_utc":      None,
                "last_updated_by_user_id":  None,
                "title":                    case_data["caseTitle"],
                "description":              case_data["caseDescription"],
                "sensitivity":              "confidential",
                "status":                   "open",
            })

            for user_id in case_data["subjects"]:
                client_rows.append({
                    "id":                   uuid.uuid4(),
                    "created_at_utc":       case_data["creationTimestamp"],
                    "created_by_user_id":   None,
                    "case_id":              case_id,
                    "user_id":              user_id,
                })

            for user_id in case_data["representatives"]:
                worker_rows.append({
                    "id":                   uuid.uuid4(),
                    "created_at_utc":       case_data["creationTimestamp"],
                    "created_by_user_id":   None,
                    "case_id":              case_id,
                    "user_id":              user_id,
                })

        self.write_many_to_database(
            target=3,
            query="""
                INSERT INTO case__cases
                (
                    id,
                    created_at_utc,
                    created_by_user_id,
                    last_updated_at_utc,
                    last_updated_by_user_id,
                    title,
                    description,
                    sensitivity,
                    status
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by_user_id)s,
                    %(last_updated_at_utc)s,
                    %(last_updated_by_user_id)s,
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
                    created_by_user_id,
                    case_id,
                    user_id
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by_user_id)s,
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
                    created_by_user_id,
                    case_id,
                    user_id
                )
                VALUES
                (
                    %(id)s,
                    %(created_at_utc)s,
                    %(created_by_user_id)s,
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
