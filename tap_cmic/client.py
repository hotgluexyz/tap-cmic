"""HTTP API client, including CMiCStream base class."""

from __future__ import annotations

import datetime
from typing import Any

import requests
from hotglue_singer_sdk.authenticators import BasicAuthenticator
from hotglue_singer_sdk.streams import RESTStream
from typing_extensions import override


class CMiCStream(RESTStream):
    """CMiC stream class."""

    records_jsonpath = "$.items[*]"
    page_size = 500
    offset_param = "offset"
    page_size_param = "limit"
    finder_param = "finder"
    replication_datetime_format = "%Y-%m-%dT%H:%M:%S%z"
    replication_key_sources: tuple[str, ...] = ()
    finder_template: str | None = None
    is_inclusive = False

    next_page_token_jsonpath = None

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
            username=self.config["user"],
            password=self.config["password"],
        )

    @override
    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Returns:
            A dictionary of HTTP headers.
        """
        headers = dict(super().http_headers)
        headers["Accept"] = "application/json"
        return headers

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
        if len(list(self.parse_response(response))) < self.page_size:
            return None
        return previous_offset + self.page_size

    def _get_incremental_start(self, context: dict | None) -> datetime.datetime:
        start_time = self.get_starting_time(context, self.is_inclusive)
        if start_time is None:
            msg = f"Stream {self.name} requires start_date or state for incremental sync"
            raise RuntimeError(msg)
        return start_time

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
        params: dict[str, Any] = {self.page_size_param: self.page_size}
        if next_page_token is not None:
            params[self.offset_param] = next_page_token
        if self.finder_template:
            start_time = self._get_incremental_start(context)
            replication_key_value = start_time.strftime(self.replication_datetime_format)
            params[self.finder_param] = self.finder_template.replace(
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
