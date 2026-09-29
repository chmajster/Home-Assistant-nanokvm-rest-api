"""Encrypted ConfigEntry credentials with a separate, owner-only local key."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .errors import KVMError

CREDENTIAL_FIELD = "credential_encrypted"
KEY_FILE = ".storage/nanokvm_rest.credentials.key"


class CredentialVault:
    """Never regenerate a missing key when encrypted records already exist."""

    def __init__(self, key_path: Path):
        self.path = key_path
        self._fernet: Fernet | None = None

    def load(self, *, encrypted_records_exist: bool = False) -> None:
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            except FileNotFoundError:
                if encrypted_records_exist:
                    raise KVMError("secret_storage", "Encryption key is missing") from None
                key = Fernet.generate_key()
                try:
                    fd = os.open(
                        self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
                    )
                except FileExistsError:
                    # Another simultaneous setup created the key; read that key.
                    return self.load(encrypted_records_exist=encrypted_records_exist)
                with os.fdopen(fd, "wb") as out:
                    out.write(key)
                    out.flush()
                    os.fsync(out.fileno())
                fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_size > 128
                    or info.st_uid != os.geteuid()
                ):
                    raise KVMError("secret_storage", "Invalid key file")
                if stat.S_IMODE(info.st_mode) & 0o077:
                    os.fchmod(source.fileno(), 0o600)
                key = source.read(128)
            self._fernet = Fernet(key)
        except KVMError:
            raise
        except (OSError, ValueError) as err:
            raise KVMError("secret_storage", "Cannot load credential encryption key") from err

    def encrypt(self, password: str) -> str:
        if self._fernet is None:
            raise KVMError("secret_storage")
        if not isinstance(password, str) or len(password.encode("utf-8")) > 4096:
            raise KVMError("invalid_data")
        return "v1:" + self._fernet.encrypt(password.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if (
            self._fernet is None
            or not isinstance(ciphertext, str)
            or not ciphertext.startswith("v1:")
        ):
            raise KVMError("secret_storage", "Invalid credential envelope")
        try:
            return self._fernet.decrypt(ciphertext[3:].encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError, ValueError) as err:
            raise KVMError("secret_storage", "Credential authentication failed") from err


async def async_vault(hass) -> CredentialVault:
    """Use the same vault for both providers; key IO never blocks HA's loop."""
    import asyncio

    key = "nanokvm_rest_credential_vault"
    lock = hass.data.setdefault(key + "_lock", asyncio.Lock())
    async with lock:
        if key not in hass.data:
            vault = CredentialVault(Path(hass.config.path(KEY_FILE)))
            encrypted = any(
                CREDENTIAL_FIELD in entry.data
                for entry in hass.config_entries.async_entries("nanokvm_rest")
            )
            await hass.async_add_executor_job(lambda: vault.load(encrypted_records_exist=encrypted))
            hass.data[key] = vault
        return hass.data[key]


async def async_password(hass, data: dict) -> str:
    """Legacy plaintext is accepted only as migration/input, never written anew."""
    if "password" in data:
        return str(data["password"])
    if CREDENTIAL_FIELD in data:
        return (await async_vault(hass)).decrypt(data[CREDENTIAL_FIELD])
    return ""


async def async_protect_data(hass, data: dict) -> dict:
    """Return a new record, preserving the old record until the caller saves it."""
    result = dict(data)
    if "password" in result:
        result["password_present"] = bool(result["password"])
        result[CREDENTIAL_FIELD] = (await async_vault(hass)).encrypt(result.pop("password"))
    result.setdefault("provider", "nanokvm")
    return result
