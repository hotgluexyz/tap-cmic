"""Stream type classes for tap-cmic."""

from __future__ import annotations

from tap_cmic.client import CMiCStream
from tap_cmic.schemas import (
    CONTRACTS_SCHEMA,
    INSURANCES_SCHEMA,
    PROJECTS_SCHEMA,
    VENDORS_SCHEMA,
)


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
