import datetime as dt
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, Literal

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp.server import (
    FastMCP,
)
from mcp.server.fastmcp.server import Settings as BaseFastMcpSettings
from mcp.server.lowlevel.server import LifespanResultT
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, Secret, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class FastMcpSettings(BaseFastMcpSettings):
    """
    FastMCP server settings. But with defaults to pass them to
    the FastMCP constructor.
    """

    # Server settings
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # HTTP settings
    host: str = "127.0.0.1"
    port: int = 8000
    mount_path: str = "/"
    sse_path: str = "/sse"
    message_path: str = "/messages/"
    streamable_http_path: str = "/mcp"

    # StreamableHTTP settings
    json_response: bool = False
    stateless_http: bool = False
    """Define if the server should create a new transport per request."""

    # resource settings
    warn_on_duplicate_resources: bool = True

    # tool settings
    warn_on_duplicate_tools: bool = True

    # prompt settings
    warn_on_duplicate_prompts: bool = True

    # TODO(Marcelo): Investigate if this is used. If it is, it's probably a good idea to remove it.
    dependencies: list[str] = Field(default_factory=list)
    """A list of dependencies to install in the server environment."""

    lifespan: (
        Callable[
            [FastMCP[LifespanResultT]],
            AbstractAsyncContextManager[LifespanResultT],
        ]
        | None
    ) = None
    """A async context manager that will be called when the server is started."""

    auth: AuthSettings | None = None

    # Transport security settings (DNS rebinding protection)
    transport_security: TransportSecuritySettings | None = None


class BasicAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BASIC_AUTH_",
        env_file=".env",
        extra="ignore",
    )

    username: str
    password: SecretStr


class BearerAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BEARER_AUTH_",
        env_file=".env",
        extra="ignore",
    )

    token: SecretStr | None = None


class JwtProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JWT_PROVIDER_",
        env_file=".env",
        extra="ignore",
    )

    private_keys: list[dict[str, Any]]
    algorithm: str | None = None
    token_lifetime: dt.timedelta = dt.timedelta(minutes=1)
    claims: dict[str, Any] = Field(default_factory=dict)


class TokenVerifierSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TOKEN_VERIFIER_",
        env_file=".env",
        extra="ignore",
    )

    url: str = "https://www.googleapis.com/oauth2/v1/tokeninfo"
    auth: Literal["bearer", "basic", "none"] = "none"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] = "GET"
    required_scopes: list[str] | None = None
    content_type: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ] = "application/json"


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        env_file=".env",
        extra="ignore",
    )

    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"


__all__ = ["FastMcpSettings", "ServerSettings", "TokenVerifierSettings"]
