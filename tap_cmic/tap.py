"""CMiC tap class."""

from __future__ import annotations

from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th  # JSON schema typing helpers
from typing_extensions import override

from tap_cmic.auth import CMiCOAuthAuthenticator, resolve_token_url
from tap_cmic.streams import (
    CompaniesStream,
    ContractsStream,
    InsurancesStream,
    ProjectsStream,
    VouchersStream,
    VendorsStream,
)

STREAM_TYPES = [
    CompaniesStream,
    ContractsStream,
    InsurancesStream,
    ProjectsStream,
    VouchersStream,
    VendorsStream,
]


class TapCMiC(Tap):
    """Singer tap for CMiC."""

    name = "tap-cmic"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
            default="2000-01-01T00:00:00Z",
        ),
        th.Property(
            "base_url",
            th.StringType,
            required=True,
            description="Base URL for the CMiC API",
        ),
        th.Property(
            "client_id",
            th.StringType,
            required=True,
            description="CMiC Client ID (Basic) or Entra application (client) id (OAuth)",
        ),
        th.Property(
            "user_id",
            th.StringType,
            description="CMiC User ID (Basic Auth)",
        ),
        th.Property(
            "password",
            th.StringType,
            description="CMiC password (Basic Auth)",
        ),
        th.Property(
            "client_secret",
            th.StringType,
            description="Entra client secret (OAuth)",
        ),
        th.Property(
            "tenant_id",
            th.StringType,
            description="Entra directory (tenant) id (OAuth)",
        ),
        th.Property(
            "token_url",
            th.StringType,
            description="Entra OAuth token URL (OAuth);",
        ),
        th.Property(
            "access_token",
            th.StringType,
            description="OAuth access token",
        ),
        th.Property(
            "scope",
            th.StringType,
            description="OAuth scope; defaults to api://{client_id}/.default",
        ),
        th.Property(
            "comp_code",
            th.StringType,
            required=False,
            description="Selected CMiC company code (CompCode)",
        ),
    ).to_dict()

    @classmethod
    def access_token_support(cls, connector=None):
        """Return authenticator class and auth endpoint for --access-token."""
        if connector is None:
            return CMiCOAuthAuthenticator, ""
        return CMiCOAuthAuthenticator, resolve_token_url(connector.config)

    @override
    def discover_streams(self) -> list[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapCMiC.cli()
