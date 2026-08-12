from hotglue_smoke_test.vcr.tap import VCRTapTestRunner

from tap_cmic.tap import TapCMiC


class Runner(VCRTapTestRunner):
    PRESERVE_KEYS = {
        "hasMore",
        "hg_modified_at",
        # companies
        "CompVUuid",
        "CompIuUpdateDate",
        "CompIuCreateDate",
        "CompCode",
        # projects
        "GrpmpVUuid",
        "GrpmpIuUpdateDate",
        "GrpmpIuCreateDate",
        "GrpmpCompCode",
        # contracts
        "ScmstVUuid",
        "ScmstIuUpdateDate",
        "ScmstIuCreateDate",
        "ScmstCompCode",
        # vouchers
        "VouNum",
        "VouIuUpdateDate",
        "VouIuCreateDate",
        "VouCompCode",
        # vendors
        "BpvenVUuid",
        "BpvenIuUpdateDate",
        "BpvenIuCreateDate",
        "BpvenCompCode",
        # insurances
        "InsVUuid",
        "InsCoverTypeCode",
        "InsIuUpdateDate",
        "InsIuCreateDate",
        "InsCompCode",
    }
    TOKEN_KEYS = {*VCRTapTestRunner.TOKEN_KEYS, "username"}

    def module(self) -> str:
        return "tap_cmic.tap"

    def launch(self):
        TapCMiC.cli()


if __name__ == "__main__":
    Runner.main()
