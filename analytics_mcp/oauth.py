# Copyright 2026 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MCP OAuth 2.1 Authorization Server provider backed by Google OAuth 2.0."""

from collections import OrderedDict
from dataclasses import dataclass
import secrets
import time
from typing import List, Optional, Tuple
from urllib.parse import urlencode

from analytics_mcp.tools.client import get_required_scopes
import httpx
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    ProviderTokenVerifier,
    RefreshToken,
    TokenError,
    TokenVerifier,
    construct_redirect_uri,
)
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
OAUTH_CALLBACK_PATH = "/oauth/callback"

_AUTH_CODE_TTL_SECONDS = 300
_DEFAULT_TOKEN_TTL_SECONDS = 3600
_MAX_STORED_ENTRIES = 10000


def _bounded_set(store: OrderedDict, key: str, value) -> None:
    """Inserts into an OrderedDict and evicts the oldest entry if over capacity."""
    if key in store:
        store.move_to_end(key)
    store[key] = value
    while len(store) > _MAX_STORED_ENTRIES:
        store.popitem(last=False)


@dataclass
class _PendingAuthorization:
    """Stores MCP client authorization parameters during Google OAuth redirect."""

    client_id: str
    params: AuthorizationParams
    created_at: float


class GoogleAuthorizationCode(AuthorizationCode):
    """MCP authorization code paired with exchanged Google OAuth tokens."""

    google_access_token: str
    google_refresh_token: Optional[str] = None
    google_expires_in: int = _DEFAULT_TOKEN_TTL_SECONDS


class GoogleOAuthProvider(
    OAuthAuthorizationServerProvider[
        GoogleAuthorizationCode, RefreshToken, AccessToken
    ]
):
    """OAuth 2.1 Authorization Server provider that proxies to Google OAuth 2.0."""

    def __init__(
        self,
        google_client_id: str,
        google_client_secret: str,
        issuer_url: str,
        allow_write: bool = False,
        streamable_http_path: str = "/mcp",
    ) -> None:
        if not google_client_id or not google_client_secret:
            raise ValueError(
                "google_client_id and google_client_secret are required for "
                "GoogleOAuthProvider."
            )
        self.google_client_id = google_client_id
        self.google_client_secret = google_client_secret
        self.issuer_url = issuer_url.rstrip("/")
        self.resource_server_url = (
            f"{self.issuer_url}/{streamable_http_path.lstrip('/')}"
        )
        self.callback_url = f"{self.issuer_url}{OAUTH_CALLBACK_PATH}"
        self.google_scopes = get_required_scopes(allow_write=allow_write)

        self._clients: OrderedDict[str, OAuthClientInformationFull] = (
            OrderedDict()
        )
        self._pending_authorizations: OrderedDict[
            str, _PendingAuthorization
        ] = OrderedDict()
        self._auth_codes: OrderedDict[str, GoogleAuthorizationCode] = (
            OrderedDict()
        )
        self._access_tokens: OrderedDict[str, AccessToken] = OrderedDict()
        self._refresh_tokens: OrderedDict[str, RefreshToken] = OrderedDict()

    def _prune_expired(self) -> None:
        """Evicts expired pending states, authorization codes, and access tokens."""
        now = time.time()
        expired_pending = [
            k
            for k, v in self._pending_authorizations.items()
            if v.created_at + _AUTH_CODE_TTL_SECONDS < now
        ]
        for k in expired_pending:
            self._pending_authorizations.pop(k, None)

        expired_codes = [
            k for k, v in self._auth_codes.items() if v.expires_at < now
        ]
        for k in expired_codes:
            self._auth_codes.pop(k, None)

        expired_tokens = [
            k
            for k, v in self._access_tokens.items()
            if v.expires_at and v.expires_at < int(now)
        ]
        for k in expired_tokens:
            self._access_tokens.pop(k, None)

    async def get_client(
        self, client_id: str
    ) -> Optional[OAuthClientInformationFull]:
        """Retrieves registered MCP OAuth client information by client_id."""
        return self._clients.get(client_id)

    async def register_client(
        self, client_info: OAuthClientInformationFull
    ) -> None:
        """Registers a dynamic MCP OAuth client in memory."""
        if not client_info.client_id:
            return
        _bounded_set(self._clients, client_info.client_id, client_info)

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Redirects the user's browser to Google's OAuth 2.0 consent page."""
        self._prune_expired()
        state_key = secrets.token_urlsafe(32)
        _bounded_set(
            self._pending_authorizations,
            state_key,
            _PendingAuthorization(
                client_id=client.client_id,
                params=params,
                created_at=time.time(),
            ),
        )
        query = urlencode(
            {
                "client_id": self.google_client_id,
                "redirect_uri": self.callback_url,
                "response_type": "code",
                "scope": " ".join(self.google_scopes),
                "access_type": "offline",
                "prompt": "consent",
                "state": state_key,
            }
        )
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"

    async def handle_oauth_callback(self, request: Request) -> Response:
        """Handles the OAuth 2.0 callback from Google and redirects to the MCP client."""
        self._prune_expired()
        state_key = request.query_params.get("state")
        if not state_key or state_key not in self._pending_authorizations:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Invalid or expired OAuth state.",
                },
                status_code=400,
            )

        pending = self._pending_authorizations.pop(state_key)
        if pending.created_at + _AUTH_CODE_TTL_SECONDS < time.time():
            redirect_url = construct_redirect_uri(
                str(pending.params.redirect_uri),
                error="invalid_request",
                error_description="OAuth authorization request expired.",
                state=pending.params.state,
            )
            return RedirectResponse(url=redirect_url, status_code=302)

        error = request.query_params.get("error")
        if error:
            redirect_url = construct_redirect_uri(
                str(pending.params.redirect_uri),
                error=error,
                error_description=request.query_params.get("error_description"),
                state=pending.params.state,
            )
            return RedirectResponse(url=redirect_url, status_code=302)

        google_code = request.query_params.get("code")
        if not google_code:
            redirect_url = construct_redirect_uri(
                str(pending.params.redirect_uri),
                error="invalid_request",
                error_description="Missing authorization code from Google.",
                state=pending.params.state,
            )
            return RedirectResponse(url=redirect_url, status_code=302)

        token_data = await self._exchange_code_with_google(google_code)
        if "error" in token_data or "access_token" not in token_data:
            redirect_url = construct_redirect_uri(
                str(pending.params.redirect_uri),
                error="server_error",
                error_description=token_data.get(
                    "error_description",
                    "Failed to exchange authorization code with Google.",
                ),
                state=pending.params.state,
            )
            return RedirectResponse(url=redirect_url, status_code=302)

        mcp_code = secrets.token_urlsafe(32)
        try:
            expires_in = int(
                token_data.get("expires_in", _DEFAULT_TOKEN_TTL_SECONDS)
            )
        except (TypeError, ValueError):
            expires_in = _DEFAULT_TOKEN_TTL_SECONDS

        granted_scope_str = token_data.get("scope")
        if isinstance(granted_scope_str, str) and granted_scope_str.strip():
            scopes = granted_scope_str.split()
        else:
            scopes = list(pending.params.scopes or self.google_scopes)
        _bounded_set(
            self._auth_codes,
            mcp_code,
            GoogleAuthorizationCode(
                code=mcp_code,
                scopes=scopes,
                expires_at=time.time() + _AUTH_CODE_TTL_SECONDS,
                client_id=pending.client_id,
                code_challenge=pending.params.code_challenge,
                redirect_uri=pending.params.redirect_uri,
                redirect_uri_provided_explicitly=(
                    pending.params.redirect_uri_provided_explicitly
                ),
                resource=pending.params.resource or self.resource_server_url,
                google_access_token=token_data["access_token"],
                google_refresh_token=token_data.get("refresh_token"),
                google_expires_in=expires_in,
            ),
        )

        redirect_url = construct_redirect_uri(
            str(pending.params.redirect_uri),
            code=mcp_code,
            state=pending.params.state,
        )
        return RedirectResponse(url=redirect_url, status_code=302)

    async def _exchange_code_with_google(self, code: str) -> dict:
        """Exchanges a Google authorization code for access and refresh tokens."""
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.google_client_id,
                        "client_secret": self.google_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.callback_url,
                    },
                )
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "error": "server_error",
                "error_description": f"Upstream Google token exchange failed: {exc}",
            }

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> Optional[GoogleAuthorizationCode]:
        """Loads a pending MCP authorization code."""
        code_obj = self._auth_codes.get(authorization_code)
        if not code_obj or code_obj.client_id != client.client_id:
            return None
        if code_obj.expires_at < time.time():
            self._auth_codes.pop(authorization_code, None)
            return None
        return code_obj

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: GoogleAuthorizationCode,
    ) -> OAuthToken:
        """Exchanges the MCP authorization code for the Google OAuth tokens."""
        self._auth_codes.pop(authorization_code.code, None)
        now = int(time.time())
        access_token_str = authorization_code.google_access_token
        expires_in = authorization_code.google_expires_in
        scopes = authorization_code.scopes or list(self.google_scopes)

        _bounded_set(
            self._access_tokens,
            access_token_str,
            AccessToken(
                token=access_token_str,
                client_id=client.client_id,
                scopes=scopes,
                expires_at=now + expires_in,
                resource=authorization_code.resource
                or self.resource_server_url,
            ),
        )

        refresh_token_str = authorization_code.google_refresh_token
        if refresh_token_str:
            _bounded_set(
                self._refresh_tokens,
                refresh_token_str,
                RefreshToken(
                    token=refresh_token_str,
                    client_id=client.client_id,
                    scopes=scopes,
                    resource=(
                        authorization_code.resource or self.resource_server_url
                    ),
                ),
            )

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=expires_in,
            scope=" ".join(scopes),
            refresh_token=refresh_token_str,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> Optional[RefreshToken]:
        """Loads a stored refresh token."""
        token_obj = self._refresh_tokens.get(refresh_token)
        if not token_obj or token_obj.client_id != client.client_id:
            return None
        return token_obj

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: List[str],
    ) -> OAuthToken:
        """Exchanges a Google refresh token for a fresh Google access token."""
        if scopes and not set(scopes).issubset(set(refresh_token.scopes)):
            raise TokenError(
                error="invalid_scope",
                error_description=(
                    "Requested scopes exceed those granted to the refresh token."
                ),
            )
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.google_client_id,
                        "client_secret": self.google_client_secret,
                        "refresh_token": refresh_token.token,
                        "grant_type": "refresh_token",
                    },
                )
                token_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TokenError(
                error="invalid_grant",
                error_description=f"Failed to contact Google token endpoint: {exc}",
            ) from exc

        if "error" in token_data or "access_token" not in token_data:
            raise TokenError(
                error="invalid_grant",
                error_description=token_data.get(
                    "error_description",
                    "Failed to refresh Google access token.",
                ),
            )

        access_token_str = token_data["access_token"]
        try:
            expires_in = int(
                token_data.get("expires_in", _DEFAULT_TOKEN_TTL_SECONDS)
            )
        except (TypeError, ValueError):
            expires_in = _DEFAULT_TOKEN_TTL_SECONDS
        effective_scopes = scopes or refresh_token.scopes

        _bounded_set(
            self._access_tokens,
            access_token_str,
            AccessToken(
                token=access_token_str,
                client_id=client.client_id,
                scopes=effective_scopes,
                expires_at=int(time.time()) + expires_in,
                resource=refresh_token.resource or self.resource_server_url,
            ),
        )

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=expires_in,
            scope=" ".join(effective_scopes),
            refresh_token=refresh_token.token,
        )

    async def _introspect_google_token(
        self, token: str
    ) -> Optional[AccessToken]:
        """Verifies a Google OAuth access token via Google's tokeninfo endpoint."""
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    GOOGLE_TOKENINFO_URL,
                    params={"access_token": token},
                )
                if response.status_code != 200:
                    return None
                data = response.json()
                expires_in = int(data.get("expires_in", 0))
        except (httpx.HTTPError, TypeError, ValueError):
            return None

        if expires_in <= 0:
            return None

        # Prevent confused-deputy attacks by ensuring the token was issued for
        # this server's configured Google OAuth Client ID.
        if self.google_client_id not in (data.get("aud"), data.get("azp")):
            return None

        token_scopes = str(data.get("scope", "")).split()
        access_token = AccessToken(
            token=token,
            client_id=self.google_client_id,
            scopes=token_scopes,
            expires_at=int(time.time()) + expires_in,
            resource=self.resource_server_url,
        )
        _bounded_set(self._access_tokens, token, access_token)
        return access_token

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """Loads and validates an access token from cache or Google tokeninfo."""
        if not token:
            return None
        token_obj = self._access_tokens.get(token)
        if token_obj is not None:
            if token_obj.expires_at and token_obj.expires_at < int(time.time()):
                self._access_tokens.pop(token, None)
                return None
            return token_obj
        return await self._introspect_google_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revokes an access or refresh token locally and with Google."""
        if isinstance(token, AccessToken):
            self._access_tokens.pop(token.token, None)
        elif isinstance(token, RefreshToken):
            self._refresh_tokens.pop(token.token, None)

        try:
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": token.token},
                )
        except httpx.HTTPError:
            pass


def build_oauth_components(
    provider: GoogleOAuthProvider,
) -> Tuple[AuthSettings, TokenVerifier, List[Route]]:
    """Builds AuthSettings, TokenVerifier, and custom callback route for Server."""
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(provider.issuer_url),
        resource_server_url=AnyHttpUrl(provider.resource_server_url),
        validate_token_resource=False,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=provider.google_scopes,
            default_scopes=provider.google_scopes,
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=provider.google_scopes,
    )
    verifier = ProviderTokenVerifier(provider)
    routes = [
        Route(
            OAUTH_CALLBACK_PATH,
            endpoint=provider.handle_oauth_callback,
            methods=["GET"],
        )
    ]
    return auth_settings, verifier, routes
