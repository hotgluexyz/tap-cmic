"""Tests standard tap features using the built-in SDK tests library."""

import datetime
from typing import cast

import pytest
from hotglue_singer_sdk.testing import get_standard_tap_tests

from tap_cmic.client import CMiCStream
from tap_cmic.tap import TapCMiC

SAMPLE_CONFIG = {
    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "base_url": "https://example.com/cmicprtn",
    "user": "placeholder",
    "password": "placeholder",
}

# _test_stream_connections makes live HTTP calls; excluded by default.
# Replace SAMPLE_CONFIG placeholders with real credentials and call it directly.
_STANDARD_TESTS = [
    t
    for t in get_standard_tap_tests(TapCMiC, config=SAMPLE_CONFIG)
    if getattr(t, "__name__", "") != "_test_stream_connections"
]


@pytest.mark.parametrize("test_func", _STANDARD_TESTS)
def test_standard(test_func):
    """Run built-in SDK tap tests (CLI output and catalog discovery)."""
    test_func()


def test_stream_params_match_cmic_definition():
    """CMiC stream requests should match the hotglue connector definition."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    projects = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "projects"),
    )
    projects._write_starting_replication_value(None)

    params = projects.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": f"selectByPmProjInfo;pmprojectDate={SAMPLE_CONFIG['start_date']}T00:00:00+0000",
    }


def test_insurances_stream_uses_query_filter_params():
    """insurances uses q because CMiC rejects finder for this endpoint."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    insurances = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "insurances"),
    )
    insurances._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = insurances.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "q": f"InsIuUpdateDate >= '{start_time}' or InsIuCreateDate >= '{start_time}'",
    }


def test_post_process_sets_synthetic_replication_key():
    """CMiC bookmarks use hg_modified_at coalesced from update/create fields."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vendors = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vendors"),
    )

    record = vendors.post_process(
        {
            "BpvenVUuid": "vendor-1",
            "BpvenIuCreateDate": "2024-01-01T00:00:00Z",
            "BpvenIuUpdateDate": "2024-02-01T00:00:00Z",
        },
    )

    assert record is not None
    assert record["hg_modified_at"] == "2024-02-01T00:00:00Z"
