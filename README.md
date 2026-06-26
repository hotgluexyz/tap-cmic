# tap-cmic

A [Singer](https://www.singer.io/) tap that extracts data from **CMiC**. It is built with [hotglue-singer-sdk](https://github.com/hotgluexyz/HotglueSingerSDK) and speaks the standard Singer message protocol on stdout, so you can pair it with any compatible target.

## Features

- **REST**-style HTTP streams (see `client.py` / `streams.py`).
- **Basic** authentication (`user` / `password`).

- Configurable **`base_url`** and optional **`start_date`** (see [Configuration](#configuration)).
- Incremental sync uses CMiC `finder` request parameters and bookmarks on synthetic `hg_modified_at`.

### Streams

| Stream | Endpoint / notes | Primary key | Replication key |
| ------ | ---------------- | ----------- | ----------------- |
| `projects` | `GET /pm-rest-api/rest/1/pmproject` | `GrpmpVUuid` | `hg_modified_at` from `GrpmpIuUpdateDate` / `GrpmpIuCreateDate` |
| `contracts` | `GET /pm-rest-api/rest/1/scmast` | `ScmstVUuid` | `hg_modified_at` from `ScmstIuUpdateDate` / `ScmstIuCreateDate` |
| `vendors` | `GET /ap-rest-api/rest/1/apvendor` | `BpvenVUuid` | `hg_modified_at` from `BpvenIuUpdateDate` / `BpvenIuCreateDate` |
| `insurances` | `GET /ap-rest-api/rest/1/apinsurance` | `InsVUuid` | `hg_modified_at` from `InsIuUpdateDate` / `InsIuCreateDate` |

All streams use CMiC's offset pagination with `limit=500`.

## Requirements

- Python **3.10+** (see `requires-python` in `pyproject.toml`).

## Installation

1. **Clone** this repository and `cd` into the project directory.
2. **Create `config.json`** in the project root with your credentials and settings (see [Configuration](#configuration) for the fields and an example).
3. **Create a virtual environment** and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

4. **Install the package** in editable mode:

```bash
pip install -e .
```

5. **Run the tap** (with the venv still activated):

```bash
tap-cmic --help
```

## Configuration

| Setting | Type | Required | Default | Description |
| ------- | ---- | -------- | ------- | ----------- |
| `start_date` | string (datetime) | no | `2000-01-01T00:00:00Z` | Earliest record date to sync. |
| `base_url` | string | yes | — | CMiC Basic Auth API base URL, without a trailing slash. See CMiC's [Cloud Web APP and API URLs](https://developers.cmicglobal.com/v1/docs/cloud-api-server-urls). |
| `user` | string | yes | — | Account username. |
| `password` | string | yes | — | Account password. |

Run `tap-cmic --about` (or `tap-cmic --about --format=markdown`) for the authoritative schema for your installed version.

### Example `config.json`

```json
{
  "start_date": "2000-01-01T00:00:00Z",
  "base_url": "https://atlas-api.cmiccloud.com/cmicprod",
  "user": "YOUR_API_SERVICE_ACCOUNT",
  "password": "YOUR_PASSWORD"
}
```

Do not commit real credentials. Prefer environment variables or a secrets manager in production.

### Environment-based config

You can load settings from the process environment using `--config=ENV` (the SDK merges env into config). Env names follow the tap’s setting keys (see `tap-cmic --about`).

## Usage

With your virtual environment **activated** and `config.json` in place:

Discover stream catalog:

```bash
tap-cmic --config config.json --discover > catalog.json
```

Run a sync (with optional state):

```bash
tap-cmic --config config.json --catalog catalog.json --state state.json
```

Pipe to any Singer target:

```bash
tap-cmic --config config.json --catalog catalog.json | target-jsonl
```

Inspect built-in settings and stream metadata:

```bash
tap-cmic --about
```

## License
Apache 2.0 — see `LICENSE` and `pyproject.toml`.
