"""CMiC tap class."""

from __future__ import annotations

from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th  # JSON schema typing helpers
from typing_extensions import override

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
            "user",
            th.StringType,
            required=True,
            description="The CMiC username",
        ),
        th.Property(
            "password",
            th.StringType,
            required=True,
            description="The CMiC password",
        ),
    ).to_dict()

    @override
    def discover_streams(self) -> list[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapCMiC.cli()
