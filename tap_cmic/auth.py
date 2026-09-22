"""CMiC OAuth2 client-credentials authenticator."""

from __future__ import annotations

from typing import Any, Mapping

from hotglue_singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
from hotglue_singer_sdk.streams import Stream as RESTStreamBase


def resolve_token_url(config: Mapping[str, Any]) -> str:
    """Return Entra token URL from config (`token_url` or `tenant_id`)."""
    token_url = config.get("token_url")
    if token_url:
        return token_url
    tenant_id = config.get("tenant_id")
    if not tenant_id:
        raise RuntimeError("tenant_id or token_url is required for OAuth client credentials.")
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


class CMiCOAuthAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Entra client-credentials auth for the CMiC OAuth API host."""

    @property
    def oauth_request_body(self) -> dict:
        client_id = self.config["client_id"]
        return {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": self.config["client_secret"],
            "scope": self.config.get("scope") or f"api://{client_id}/.default",
        }

    @classmethod
    def create_for_stream(cls, stream: RESTStreamBase) -> CMiCOAuthAuthenticator:
        return cls(stream=stream, auth_endpoint=resolve_token_url(stream.config))
