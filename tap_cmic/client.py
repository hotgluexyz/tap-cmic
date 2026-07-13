"""HTTP API client, including CMiCStream base class."""

from __future__ import annotations

from typing import Any

import requests
from hotglue_singer_sdk.authenticators import BasicAuthenticator
from hotglue_singer_sdk.streams import RESTStream
from typing_extensions import override


class CMiCStream(RESTStream):
    """CMiC stream class."""

    records_jsonpath = "$.items[*]"
    page_size = 500
    replication_datetime_format = "%Y-%m-%dT%H:%M:%S%z"
    replication_key_sources: tuple[str, ...] = ()
    finder_template: str | None = None
    query_template: str | None = None
    is_inclusive = False

    @override
    @property
    def url_base(self) -> str:
        """Return the API URL root."""
        return self.config["base_url"]

    @override
    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return BasicAuthenticator(
            stream=self,
            username=self.config["username"],
            password=self.config["password"],
        )

    def get_next_page_token(
        self,
        response: requests.Response,
        previous_token: Any | None,
    ) -> Any | None:
        """Return token identifying next page or None if all records have been read.

        Args:
            response: A raw `requests.Response`_ object.
            previous_token: Previous pagination reference.

        Returns:
            Reference value to retrieve next page.

        .. _requests.Response:
            https://requests.readthedocs.io/en/latest/api/#requests.Response
        """
        previous_offset = previous_token or 0
        if not response.json()["hasMore"]:
            return None
        return previous_offset + self.page_size

    @override
    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict[str, Any] = {"limit": self.page_size}
        if next_page_token is not None:
            params["offset"] = next_page_token

        filter_template = self.finder_template or self.query_template
        if filter_template:
            replication_key_value = self.get_starting_time(
                context,
                self.is_inclusive,
            ).strftime(self.replication_datetime_format)
            params["finder" if self.finder_template else "q"] = filter_template.replace(
                "{replication_key_value}",
                replication_key_value,
            )
        return params

    @override
    def post_process(
        self,
        row: dict,
        context: dict | None = None,
    ) -> dict | None:
        """As needed, append or transform raw data to match expected structure.

        Args:
            row: An individual record from the stream.
            context: The stream context.

        Returns:
            The updated record dictionary, or ``None`` to skip the record.
        """
        if self.replication_key_sources:
            row[self.replication_key] = next(
                (
                    row[source]
                    for source in self.replication_key_sources
                    if row.get(source) not in (None, "")
                ),
                None,
            )
        return row
