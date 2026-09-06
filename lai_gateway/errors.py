class GatewayError(Exception):
    """Base error for expected gateway failures."""


class ConfigError(GatewayError):
    """Configuration is missing, unsafe, or invalid."""


class HarnessHTTPError(GatewayError):
    """The lai harness control plane returned an unsuccessful HTTP response."""

    def __init__(self, status: int, message: str):
        super().__init__(f"harness_http_error status={status}: {message}")
        self.status = status
        self.message = message
