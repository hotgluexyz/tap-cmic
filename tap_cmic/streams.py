"""Stream type classes for tap-cmic."""

from __future__ import annotations

from typing import Any

from typing_extensions import override

from tap_cmic.client import CMiCStream
from tap_cmic.schemas import (
    COMPANIES_SCHEMA,
    CONTRACTS_VOUCHERS_SCHEMA,
    CONTRACTS_SCHEMA,
    INSURANCES_SCHEMA,
    PROJECTS_SCHEMA,
    CONTRACTS_REQUEST_FOR_PAYMENT_SCHEMA,
    VENDORS_SCHEMA,
    VOUCHERS_SCHEMA,
)


class CompaniesStream(CMiCStream):
    """Stream for ``companies`` (GL company master)."""

    name = "companies"
    path = "/glrestapi/rest/v1/glcompany"
    primary_keys = "CompVUuid"  # type: ignore[assignment]
    replication_key = "hg_modified_at"
    replication_key_sources = ("CompIuUpdateDate", "CompIuCreateDate")
    finder_template = "selectByDate;auditDate={replication_key_value}"
    is_inclusive = True
    schema = COMPANIES_SCHEMA


class ProjectsStream(CMiCStream):
    """Stream for ``projects``."""

    name = "projects"
    path = "/pm-rest-api/rest/1/pmproject"
    primary_keys = "GrpmpVUuid"  # type: ignore[assignment]
    replication_key = "hg_modified_at"
    replication_key_sources = ("GrpmpIuUpdateDate", "GrpmpIuCreateDate")
    finder_template = "selectByPmProjInfo;pmprojectDate={replication_key_value}"
    schema = PROJECTS_SCHEMA


class ContractsStream(CMiCStream):
    """Stream for ``contracts``."""

    name = "contracts"
    path = "/pm-rest-api/rest/1/scmast"
    primary_keys = "ScmstVUuid"  # type: ignore[assignment]
    replication_key = "hg_modified_at"
    replication_key_sources = ("ScmstIuUpdateDate", "ScmstIuCreateDate")
    finder_template = "selectByPostDate;AuditDate={replication_key_value}"
    is_inclusive = True
    schema = CONTRACTS_SCHEMA

    @override
    def get_child_context(self, record: dict, context: dict | None) -> dict:
        """Pass contract keys to child streams."""
        return {
            "ScmstCompCode": record["ScmstCompCode"],
            "ScmstVenCode": record["ScmstVenCode"],
            "ScmstContCode": record["ScmstContCode"],
        }


class ContractsRequestForPaymentStream(CMiCStream):
    """Request-for-payment totals for a single contract."""

    name = "contracts_request_for_payment"
    path = "/ap-rest-api/rest/1/scrfptotals"
    parent_stream_type = ContractsStream
    primary_keys = "VsovVouUuid"  # type: ignore[assignment]
    schema = CONTRACTS_REQUEST_FOR_PAYMENT_SCHEMA

    @override
    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": self.page_size}
        if next_page_token is not None:
            params["offset"] = next_page_token
        if context:
            params["finder"] = (
                f"scRfpTotal;vendorCode={context['ScmstVenCode']},"
                f"contractCode={context['ScmstContCode']}"
            )
        return params

    @override
    def post_process(
        self,
        row: dict,
        context: dict | None = None,
    ) -> dict | None:
        row = super().post_process(row, context)
        if row and context:
            row["ScmstCompCode"] = context["ScmstCompCode"]
            row["ScmstVenCode"] = context["ScmstVenCode"]
            row["ScmstContCode"] = context["ScmstContCode"]
        return row


class ContractsVouchersStream(CMiCStream):
    """AP voucher amounts for a single contract."""

    name = "contracts_vouchers"
    path = "/ap-rest-api/rest/1/apallvouchers"
    parent_stream_type = ContractsStream
    primary_keys = "VouNum"  # type: ignore[assignment]
    schema = CONTRACTS_VOUCHERS_SCHEMA

    @override
    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": self.page_size}
        if next_page_token is not None:
            params["offset"] = next_page_token
        if context:
            params["finder"] = (
                "VouInvOutGrandAmtFinder;"
                f"CompCodeVar={context['ScmstCompCode']},"
                f"VendorCodeVar={context['ScmstVenCode']},"
                f"ContCodeVar={context['ScmstContCode']}"
            )
        return params

    @override
    def post_process(
        self,
        row: dict,
        context: dict | None = None,
    ) -> dict | None:
        row = super().post_process(row, context)
        if row and context:
            row["ScmstCompCode"] = context["ScmstCompCode"]
            row["ScmstVenCode"] = context["ScmstVenCode"]
            row["ScmstContCode"] = context["ScmstContCode"]
        return row


class VouchersStream(CMiCStream):
    """All AP vouchers."""

    name = "vouchers"
    path = "/ap-rest-api/rest/1/apallvouchers"
    primary_keys = "VouNum"  # type: ignore[assignment]
    schema = VOUCHERS_SCHEMA


class VendorsStream(CMiCStream):
    """Stream for ``vendors``."""

    name = "vendors"
    path = "/ap-rest-api/rest/1/apvendor"
    primary_keys = "BpvenVUuid"  # type: ignore[assignment]
    replication_key = "hg_modified_at"
    replication_key_sources = ("BpvenIuUpdateDate", "BpvenIuCreateDate")
    finder_template = "selectByDate;auditDate={replication_key_value}"
    is_inclusive = True
    schema = VENDORS_SCHEMA


class InsurancesStream(CMiCStream):
    """Stream for ``insurances``."""

    name = "insurances"
    path = "/ap-rest-api/rest/1/apinsurance"
    primary_keys = "InsVUuid"  # type: ignore[assignment]
    replication_key = "hg_modified_at"
    replication_key_sources = ("InsIuUpdateDate", "InsIuCreateDate")
    query_template = (
        "InsCoverTypeCode = 'COI' "
        "and (InsIuUpdateDate >= '{replication_key_value}' "
        "or InsIuCreateDate >= '{replication_key_value}')"
    )
    is_inclusive = True
    schema = INSURANCES_SCHEMA
