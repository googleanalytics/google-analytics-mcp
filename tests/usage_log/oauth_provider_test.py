from analytics_mcp.oauth import build_oauth_components
from analytics_mcp.usage_log.oauth_provider import (
    IdentityScopedGoogleOAuthProvider,
)

ANALYTICS_READONLY = "https://www.googleapis.com/auth/analytics.readonly"
USERINFO_EMAIL = "https://www.googleapis.com/auth/userinfo.email"


def _provider() -> IdentityScopedGoogleOAuthProvider:
    return IdentityScopedGoogleOAuthProvider(
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        issuer_url="https://ga4-mcp.example.com",
    )


def test_consent_asks_for_analytics_and_identity():
    assert _provider().google_scopes == [
        ANALYTICS_READONLY,
        "openid",
        USERINFO_EMAIL,
    ]


def test_tokens_must_carry_identity_scopes():
    auth_settings, _, _ = build_oauth_components(_provider())
    assert set(auth_settings.required_scopes) == {
        ANALYTICS_READONLY,
        "openid",
        USERINFO_EMAIL,
    }
