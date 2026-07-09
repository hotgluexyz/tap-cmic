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
        "q": (
            "InsCoverTypeCode = 'COI' "
            f"and (InsIuUpdateDate >= '{start_time}' "
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


def test_contracts_child_context_for_request_for_payment():
    """contracts passes vendor and contract codes to child streams."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    contracts = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "contracts"),
    )

    context = contracts.get_child_context(
        {
            "ScmstCompCode": "001",
            "ScmstVenCode": "HOTG01",
            "ScmstContCode": "74584-01",
        },
        None,
    )

    assert context == {
        "ScmstCompCode": "001",
        "ScmstVenCode": "HOTG01",
        "ScmstContCode": "74584-01",
    }


def test_contracts_request_for_payment_uses_parent_context_finder():
    """contracts_request_for_payment queries CMiC per parent contract."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    request_for_payment = cast(
        CMiCStream,
        next(
            stream
            for stream in tap.streams.values()
            if stream.name == "contracts_request_for_payment"
        ),
    )

    params = request_for_payment.get_url_params(
        {
            "ScmstCompCode": "001",
            "ScmstVenCode": "HOTG01",
            "ScmstContCode": "74584-01",
        },
        next_page_token=500,
    )

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": "scRfpTotal;vendorCode=HOTG01,contractCode=74584-01",
    }


def test_contracts_vouchers_uses_parent_context_finder():
    """contracts_vouchers queries CMiC per parent contract."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vouchers = cast(
        CMiCStream,
        next(
            stream
            for stream in tap.streams.values()
            if stream.name == "contracts_vouchers"
        ),
    )

    params = vouchers.get_url_params(
        {
            "ScmstCompCode": "001",
            "ScmstVenCode": "HOTG01",
            "ScmstContCode": "74584-01",
        },
        next_page_token=500,
    )

    assert params == {
        "limit": 500,
        "offset": 500,
        "finder": (
            "VouInvOutGrandAmtFinder;"
            "CompCodeVar=001,VendorCodeVar=HOTG01,ContCodeVar=74584-01"
        ),
    }


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


def test_vouchers_stream_has_no_finder_filter():
    """vouchers lists apallvouchers without contract-scoped finders."""
    tap = TapCMiC(config=SAMPLE_CONFIG)
    vouchers = cast(
        CMiCStream,
        next(stream for stream in tap.streams.values() if stream.name == "vouchers"),
    )

    params = vouchers.get_url_params(context=None, next_page_token=500)

    assert params == {"limit": 500, "offset": 500}
