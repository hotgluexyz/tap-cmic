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
    "username": "placeholder",
    "password": "placeholder",
}

SAMPLE_CONFIG_WITH_COMP_CODE = {
    **SAMPLE_CONFIG,
    "comp_code": "001",
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
        "q": (
            f"(InsIuUpdateDate >= '{start_time}' "
            f"or InsIuCreateDate >= '{start_time}')"
        ),
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


def test_companies_stream_params_match_cmic_definition():
    """companies uses selectByDate finder on glcompany."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    companies = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "companies"),
    )
    companies._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = companies.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": f"selectByDate;auditDate={start_time}",
    }


def test_companies_post_process_sets_synthetic_replication_key():
    """companies bookmarks use hg_modified_at from CompIu update/create dates."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    companies = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "companies"),
    )

    record = companies.post_process(
        {
            "CompVUuid": "company-1",
            "CompIuCreateDate": "2024-01-01T00:00:00Z",
            "CompIuUpdateDate": "2024-02-01T00:00:00Z",
        },
    )

    assert record is not None
    assert record["hg_modified_at"] == "2024-02-01T00:00:00Z"


def test_vouchers_stream_uses_query_filter_params():
    """vouchers uses q so create and update dates both drive incremental sync."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vouchers = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vouchers"),
    )
    vouchers._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = vouchers.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "q": (f"VouIuUpdateDate >= '{start_time}' or VouIuCreateDate >= '{start_time}'"),
    }


def test_vouchers_post_process_prefers_update_date():
    """hg_modified_at prefers VouIuUpdateDate when present (e.g. after payment)."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vouchers = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vouchers"),
    )

    record = vouchers.post_process(
        {
            "VouNum": 251507376,
            "VouIuCreateDate": "2026-07-01T09:14:13-04:00",
            "VouIuUpdateDate": "2026-07-01T10:21:40-04:00",
        },
    )

    assert record is not None
    assert record["hg_modified_at"] == "2026-07-01T10:21:40-04:00"


def test_vouchers_post_process_falls_back_to_create_date():
    """hg_modified_at falls back to VouIuCreateDate when update is null."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vouchers = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vouchers"),
    )

    record = vouchers.post_process(
        {
            "VouNum": 1,
            "VouIuCreateDate": "2026-08-04T12:33:11-04:00",
            "VouIuUpdateDate": None,
        },
    )

    assert record is not None
    assert record["hg_modified_at"] == "2026-08-04T12:33:11-04:00"


def test_projects_params_include_company_q_with_comp_code():
    """With comp_code, projects keeps finder and adds GrpmpCompCode q."""
    tap = TapCMiC(config=SAMPLE_CONFIG_WITH_COMP_CODE)
    projects = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "projects"),
    )
    projects._write_starting_replication_value(None)

    params = projects.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": (
            f"selectByPmProjInfo;pmprojectDate="
            f"{SAMPLE_CONFIG_WITH_COMP_CODE['start_date']}T00:00:00+0000"
        ),
        "q": f"GrpmpCompCode = '{SAMPLE_CONFIG_WITH_COMP_CODE['comp_code']}'",
    }


def test_companies_params_include_company_q_with_comp_code():
    """With comp_code, companies keeps selectByDate finder and adds CompCode q."""
    tap = TapCMiC(config=SAMPLE_CONFIG_WITH_COMP_CODE)
    companies = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "companies"),
    )
    companies._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG_WITH_COMP_CODE["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = companies.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": f"selectByDate;auditDate={start_time}",
        "q": f"CompCode = '{SAMPLE_CONFIG_WITH_COMP_CODE['comp_code']}'",
    }


def test_insurances_params_wrap_query_with_comp_code():
    """With comp_code, insurances wraps the query with InsCompCode."""
    tap = TapCMiC(config=SAMPLE_CONFIG_WITH_COMP_CODE)
    insurances = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "insurances"),
    )
    insurances._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG_WITH_COMP_CODE["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = insurances.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "q": (
            f"InsCompCode = '{SAMPLE_CONFIG_WITH_COMP_CODE['comp_code']}' and "
            f"((InsIuUpdateDate >= '{start_time}' "
            f"or InsIuCreateDate >= '{start_time}'))"
        ),
    }


def test_vouchers_params_wrap_query_with_comp_code():
    """With comp_code, vouchers wraps the date query with VouCompCode."""
    tap = TapCMiC(config=SAMPLE_CONFIG_WITH_COMP_CODE)
    vouchers = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vouchers"),
    )
    vouchers._write_starting_replication_value(None)
    start_time = (
        datetime.datetime.fromisoformat(SAMPLE_CONFIG_WITH_COMP_CODE["start_date"]).replace(
            tzinfo=datetime.timezone.utc,
        )
        + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%dT%H:%M:%S%z")

    params = vouchers.get_url_params(context=None, next_page_token=500)

    assert params == {
        "limit": 500,
        "offset": 500,
        "q": (
            f"VouCompCode = '{SAMPLE_CONFIG_WITH_COMP_CODE['comp_code']}' and "
            f"(VouIuUpdateDate >= '{start_time}' or VouIuCreateDate >= '{start_time}')"
        ),
    }
