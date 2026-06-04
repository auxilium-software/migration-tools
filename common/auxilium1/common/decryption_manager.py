import json
import struct
import base64

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from common.auxilium1.enums.encryption_format import EncryptionFormat


class DecryptionManager:
    def __init__(self, encryption_key: str, encryption_algorithm: str) -> None:
        self._key       = base64.b64decode(encryption_key)
        self._algorithm = encryption_algorithm.upper()  # normalise once at construction

        assert len(self._key) in (16, 24, 32), \
            f"Invalid key length {len(self._key)} bytes - expected 16, 24, or 32"

    def decrypt(self, data: "str | bytes") -> str:
        if isinstance(data, (bytes, bytearray)):
            indicator = chr(data[0])
        else:
            indicator = data[0]

        if indicator == EncryptionFormat.JSON.value:
            return self._decrypt_json(data)

        if indicator == EncryptionFormat.PACK.value:
            raw = data if isinstance(data, (bytes, bytearray)) else data.encode("latin-1")
            return self._decrypt_packed(raw)

        raise ValueError(
            f"Unrecognised format indicator {indicator!r}. "
            f"Expected {EncryptionFormat.JSON.value!r} or {EncryptionFormat.PACK.value!r}."
        )

    def _decrypt_json(self, data: str) -> str:
        try:
            meta = json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"JSON format: failed to parse envelope - {e}") from e

        if not isinstance(meta, dict) or "iv" not in meta or "ed" not in meta:
            raise ValueError(f"JSON format: missing 'iv' or 'ed' keys, got {list(meta.keys())!r}")

        iv         = base64.b64decode(meta["iv"].replace("-", "+").replace("_", "/"))
        ciphertext = base64.b64decode(meta["ed"].replace("-", "+").replace("_", "/"))

        return self._do_decrypt(ciphertext, iv)

    _HEADER_FMT    = "<HQ"
    _HEADER_SIZE   = struct.calcsize(_HEADER_FMT)   # 10 bytes
    _DATA_OFFSET   = 1 + _HEADER_SIZE               # 11 bytes

    def _decrypt_packed(self, data: bytes) -> str:
        if len(data) < self._DATA_OFFSET:
            raise ValueError(f"Packed format: payload too short ({len(data)} bytes)")

        try:
            iv_length, ed_length = struct.unpack_from(self._HEADER_FMT, data, 1)
        except struct.error as e:
            raise ValueError(f"Packed format: failed to unpack header - {e}") from e

        expected = self._DATA_OFFSET + iv_length + ed_length
        if len(data) < expected:
            raise ValueError(
                f"Packed format: buffer too short - need {expected} bytes, have {len(data)}"
            )

        iv         = data[self._DATA_OFFSET : self._DATA_OFFSET + iv_length]
        ciphertext = data[self._DATA_OFFSET + iv_length : self._DATA_OFFSET + iv_length + ed_length]

        return self._do_decrypt(ciphertext, iv)

    def _do_decrypt(self, ciphertext: bytes, iv: bytes) -> str:
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                return plaintext.decode(encoding)
            except UnicodeDecodeError:
                continue

        # last resort - decode as latin-1 (never raises) and flag it
        decoded = plaintext.decode("latin-1")
        print(f"Warning: could not decode plaintext as utf-8 or cp1252, fell back to latin-1")
        return decoded

    def decrypt_bytes(self, data: "str | bytes") -> bytes:
        if isinstance(data, (bytes, bytearray)):
            indicator = chr(data[0])
        else:
            indicator = data[0]

        if indicator == EncryptionFormat.JSON.value:
            return self._decrypt_json_bytes(data)
        if indicator == EncryptionFormat.PACK.value:
            raw = data if isinstance(data, (bytes, bytearray)) else data.encode("latin-1")
            return self._decrypt_packed_bytes(raw)

        raise ValueError(f"Unrecognised format indicator {indicator!r}")

    def _decrypt_packed_bytes(self, data: bytes) -> bytes:
        if len(data) < self._DATA_OFFSET:
            raise ValueError(f"Packed format: payload too short ({len(data)} bytes)")
        iv_length, ed_length = struct.unpack_from(self._HEADER_FMT, data, 1)
        iv = data[self._DATA_OFFSET: self._DATA_OFFSET + iv_length]
        ciphertext = data[self._DATA_OFFSET + iv_length: self._DATA_OFFSET + iv_length + ed_length]
        return self._do_decrypt_bytes(ciphertext, iv)

    def _do_decrypt_bytes(self, ciphertext: bytes, iv: bytes) -> bytes:
        cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
