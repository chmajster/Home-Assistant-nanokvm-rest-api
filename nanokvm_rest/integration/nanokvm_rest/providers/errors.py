"""Safe, actionable errors shared by KVM transports and the Manager API."""

from __future__ import annotations

MESSAGES = {
    "invalid_url": "Podaj prawidłowy adres IPv4, IPv6 lub hostname oraz port 1–65535.",
    "forbidden_target": "Adres nie należy do dozwolonej sieci LAN lub wskazuje chronioną usługę lokalną.",
    "dns_error": "Nie można odnaleźć hosta w DNS. Sprawdź nazwę i konfigurację DNS/mDNS Home Assistant.",
    "connection_refused": "Urządzenie odrzuca połączenie. Sprawdź, czy jest włączone i czy port jest prawidłowy.",
    "timeout": "Urządzenie nie odpowiedziało w wyznaczonym czasie. Sprawdź połączenie z siecią LAN.",
    "tls_error": "Nie można zweryfikować połączenia TLS. Sprawdź certyfikat i protokół urządzenia.",
    "unreachable": "Brak odpowiedzi z urządzenia. Sprawdź adres, trasę sieciową i zaporę.",
    "not_jetkvm": "Host odpowiada, ale odpowiedź nie jest zgodna z lokalnym API JetKVM.",
    "setup_required": "JetKVM wymaga pierwszej konfiguracji w swoim lokalnym interfejsie.",
    "authentication_required": "JetKVM wymaga lokalnego hasła. Podaj je w konfiguracji urządzenia.",
    "invalid_password": "Urządzenie odrzuciło hasło. Popraw dane dostępowe i ponów test.",
    "rate_limited": "Zbyt wiele prób logowania. Odczekaj przed ponowną próbą.",
    "protocol_error": "Urządzenie zwróciło nieprawidłową odpowiedź protokołu KVM.",
    "permission_denied": "Urządzenie nie zezwala na tę operację dla bieżącej sesji.",
    "busy": "To urządzenie ma już aktywną sesję KVM. Rozłącz ją przed otwarciem następnej.",
    "unsupported": "Wybrana funkcja nie jest dostępna dla tego urządzenia lub transportu.",
    "session_required": "Ta operacja wymaga aktywnej sesji Live KVM.",
    "unknown_provider": "Nieobsługiwany typ urządzenia KVM.",
    "secret_storage": "Nie można odczytać magazynu sekretów KVM. Sprawdź klucz i uprawnienia pliku.",
    "wrong_device": "Pod nowym adresem odpowiada inne urządzenie. Poprzednia konfiguracja nie została zmieniona.",
    "invalid_data": "Nieprawidłowe dane urządzenia.",
    "not_found": "Nie znaleziono urządzenia KVM.",
}


class KVMError(Exception):
    """Never include upstream bodies, passwords, cookies or SDP in an error."""

    def __init__(self, code: str, detail: str = "", *, retry_after: int | None = None):
        self.code = code if code in MESSAGES else "protocol_error"
        self.message = MESSAGES[self.code]
        # Call sites pass only fixed diagnostic strings/status numbers.
        self.detail = detail[:256]
        self.retry_after = retry_after
        super().__init__(self.message)

    def public(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.detail:
            result["detail"] = self.detail
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        return result
