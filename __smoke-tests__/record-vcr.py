from hotglue_smoke_test.vcr.tap import VCRTapTestRunner

from tap_cmic.tap import TapCMiC


class Runner(VCRTapTestRunner):
    FILTER_HEADERS = [*VCRTapTestRunner.FILTER_HEADERS]
    PRESERVE_KEYS = {"hasMore"}
    TOKEN_KEYS = {*VCRTapTestRunner.TOKEN_KEYS, "username"}

    def module(self) -> str:
        return "tap_cmic.tap"

    def launch(self):
        TapCMiC.cli()


if __name__ == "__main__":
    Runner.main()
