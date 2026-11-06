from __future__ import annotations

from analytics_mcp.oauth import GoogleOAuthProvider

IDENTITY_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
)


class IdentityScopedGoogleOAuthProvider(GoogleOAuthProvider):
    """Google OAuth provider that also asks who the user is.

    The upstream provider requests Analytics scopes only; the usage log needs
    the user's sub and email on top, so the consent screen asks for them too.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.google_scopes = [*self.google_scopes, *IDENTITY_SCOPES]
