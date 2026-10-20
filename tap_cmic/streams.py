"""Stream type classes for tap-cmic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from dateutil.relativedelta import relativedelta
from typing_extensions import override

from tap_cmic.client import CMiCStream
from tap_cmic.schemas import (
    COMPANIES_SCHEMA,
    CONTRACTS_SCHEMA,
    INSURANCES_SCHEMA,
    PROJECTS_SCHEMA,
    VENDORS_SCHEMA,
    VOUCHERS_SCHEMA,
)


class CompaniesStream(CMiCStream):
    """Stream for ``companies`` (GL company master)."""

    name = "companies"
    path = "/glrestapi/rest/v1/glcompany"
    primary_keys = ["CompVUuid"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("CompIuUpdateDate", "CompIuCreateDate")
    finder_template = "selectByDate;auditDate={replication_key_value}"
    is_inclusive = True
    comp_code_field = "CompCode"
    schema = COMPANIES_SCHEMA


class ProjectsStream(CMiCStream):
    """Stream for ``projects``."""

    name = "projects"
    path = "/pm-rest-api/rest/1/pmproject"
    primary_keys = ["GrpmpVUuid"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("GrpmpIuUpdateDate", "GrpmpIuCreateDate")
    finder_template = "selectByPmProjInfo;pmprojectDate={replication_key_value}"
    comp_code_field = "GrpmpCompCode"
    schema = PROJECTS_SCHEMA


class ContractsStream(CMiCStream):
    """Stream for ``contracts``."""

    name = "contracts"
    path = "/pm-rest-api/rest/1/scmast"
    primary_keys = ["ScmstVUuid"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("ScmstIuUpdateDate", "ScmstIuCreateDate")
    finder_template = "selectByPostDate;AuditDate={replication_key_value}"
    is_inclusive = True
    comp_code_field = "ScmstCompCode"
    schema = CONTRACTS_SCHEMA


class VouchersStream(CMiCStream):
    """All AP vouchers."""

    name = "vouchers"
    path = "/ap-rest-api/rest/1/apallvouchers"
    primary_keys = ["VouNum"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("VouIuUpdateDate", "VouIuCreateDate")
    query_template = (
        "VouIuUpdateDate >= '{replication_key_value}' "
        "or VouIuCreateDate >= '{replication_key_value}'"
    )
    is_inclusive = True
    comp_code_field = "VouCompCode"
    schema = VOUCHERS_SCHEMA


class VendorsStream(CMiCStream):
    """Stream for ``vendors``."""

    name = "vendors"
    path = "/ap-rest-api/rest/1/apvendor"
    primary_keys = ["BpvenVUuid"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("BpvenIuUpdateDate", "BpvenIuCreateDate")
    finder_template = "selectByDate;auditDate={replication_key_value}"
    is_inclusive = True
    comp_code_field = "BpvenCompCode"
    schema = VENDORS_SCHEMA


class InsurancesStream(CMiCStream):
    """Stream for ``insurances``.

    Pages within monthly date windows so offset stays small on /apinsurance.
    """

    name = "insurances"
    path = "/ap-rest-api/rest/1/apinsurance"
    primary_keys = ["InsVUuid"]
    replication_key = "hg_modified_at"
    replication_key_sources = ("InsIuUpdateDate", "InsIuCreateDate")
    query_template = (
        "((InsIuUpdateDate >= '{window_start}' and InsIuUpdateDate < '{window_end}') "
        "or (InsIuCreateDate >= '{window_start}' and InsIuCreateDate < '{window_end}'))"
    )
    is_inclusive = True
    comp_code_field = "InsCompCode"
    schema = INSURANCES_SCHEMA
    date_window = relativedelta(months=1)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._window_start: datetime | None = None
        self._window_end: datetime | None = None
        self._seen_pks: set[str] = set()

    @override
    def post_process(
        self,
        row: dict,
        context: dict | None = None,
    ) -> dict | None:
        row = super().post_process(row, context)
        pk = row["InsVUuid"]
        if pk in self._seen_pks:
            return None
        self._seen_pks.add(pk)
        return row

    @override
    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        if self._window_start is None:
            self._window_start = self.get_starting_time(context, self.is_inclusive)
            self._window_end = self._window_start + self.date_window
            self.logger.info(
                "Insurances window %s → %s",
                self._window_start.isoformat(),
                self._window_end.isoformat(),
            )

        # str tokens mark a new window (offset 0); only ints are real offsets.
        parent_token = next_page_token if isinstance(next_page_token, int) else None
        params = super().get_url_params(context, parent_token)
        # Parent only substitutes {replication_key_value}; overwrite with window bounds.
        params["q"] = self.query_template.format(
            window_start=self._window_start.strftime(self.replication_datetime_format),
            window_end=self._window_end.strftime(self.replication_datetime_format),
        )
        if self.comp_code and self.comp_code_field:
            params["q"] = self._company_scoped_query(params["q"])
        return params

    @override
    def get_next_page_token(
        self,
        response: requests.Response,
        previous_token: Any | None,
    ) -> Any | None:
        # Non-int tokens mark a window reset; parent should treat them as offset 0.
        parent_prev = previous_token if isinstance(previous_token, int) else None
        token = super().get_next_page_token(response, parent_prev)
        if token is not None:
            return token

        if self._window_end < datetime.now(timezone.utc):
            self._window_start = self._window_end
            self._window_end = self._window_start + self.date_window
            self.logger.info(
                "Insurances window %s → %s",
                self._window_start.isoformat(),
                self._window_end.isoformat(),
            )
            # Unique + truthy so the SDK keeps paging and does not see a loop.
            return self._window_start.isoformat()
        return None
