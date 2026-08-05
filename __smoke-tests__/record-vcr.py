import vcr
from hotglue_smoke_test.vcr.tap import VCRTapTestRunner

from tap_cmic.tap import TapCMiC


def _drop_set_cookie(response):
    headers = response.get("headers") or {}
    headers.pop("Set-Cookie", None)
    headers.pop("set-cookie", None)
    return response


class Runner(VCRTapTestRunner):
    FILTER_HEADERS = [*VCRTapTestRunner.FILTER_HEADERS]
    PRESERVE_KEYS = {"hasMore"}

    def module(self) -> str:
        return "tap_cmic.tap"

    def launch(self):
        TapCMiC.cli()

    def vcr_use_cassette(self, filter_query_parameters):
        return vcr.use_cassette(
            self.vcr_cassette_path,
            decode_compressed_response=True,
            filter_headers=list(self.FILTER_HEADERS),
            filter_post_data_parameters=list(self.TOKEN_KEYS),
            filter_query_parameters=filter_query_parameters,
            before_record_response=_drop_set_cookie,
        )


if __name__ == "__main__":
    Runner.main()
