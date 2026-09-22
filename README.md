# tap-cmic

A [Singer](https://www.singer.io/) tap that extracts data from **CMiC**. It is built with [hotglue-singer-sdk](https://github.com/hotgluexyz/HotglueSingerSDK) and speaks the standard Singer message protocol on stdout, so you can pair it with any compatible target.

## Features

- **REST**-style HTTP streams (see `client.py` / `streams.py`).
- **Basic** authentication (`client_id`||`user_id` / `password`) or **OAuth 2.0 client credentials** (Entra / Azure AD).
- Configurable **`base_url`**, optional **`start_date`**, and optional **`comp_code`** (see [Configuration](#configuration)).
- Incremental sync uses CMiC `finder` or `q` request parameters and bookmarks on synthetic `hg_modified_at`.

### Streams

| Stream | Endpoint / notes | Primary key | Replication key |
| ------ | ---------------- | ----------- | ----------------- |
| `companies` | `GET /glrestapi/rest/v1/glcompany` | `CompVUuid` | `hg_modified_at` from `CompIuUpdateDate` / `CompIuCreateDate` |
| `projects` | `GET /pm-rest-api/rest/1/pmproject` | `GrpmpVUuid` | `hg_modified_at` from `GrpmpIuUpdateDate` / `GrpmpIuCreateDate` |
| `contracts` | `GET /pm-rest-api/rest/1/scmast` | `ScmstVUuid` | `hg_modified_at` from `ScmstIuUpdateDate` / `ScmstIuCreateDate` |
| `vouchers` | `GET /ap-rest-api/rest/1/apallvouchers` | `VouNum` | `hg_modified_at` from `VouIuUpdateDate` / `VouIuCreateDate` |
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

Auth mode is selected from config: if `client_secret` is set, the tap uses OAuth client credentials; otherwise Basic Auth.

CMiC Cloud uses separate API hosts for Basic vs OAuth. Use the host that matches your auth mode. See CMiC's [Cloud Web APP and API URLs](https://developers.cmicglobal.com/v1/docs/cloud-api-server-urls).

| Setting | Type | Required | Default | Description |
| ------- | ---- | -------- | ------- | ----------- |
| `start_date` | string (datetime) | no | `2000-01-01T00:00:00Z` | Earliest record date to sync. |
| `base_url` | string | yes | — | CMiC API base URL, without a trailing slash (Basic or OAuth host). |
| `client_id` | string | yes | — | CMiC Client ID (Basic) or Entra application (client) ID (OAuth). |
| `user_id` | string | Basic | — | CMiC User ID (Basic Auth). |
| `password` | string | Basic | — | Account password (Basic Auth). |
| `client_secret` | string | OAuth | — | Entra client secret. |
| `tenant_id` | string | OAuth* | — | Entra directory (tenant) ID. |
| `token_url` | string | OAuth* | `https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token` | Entra token endpoint. Built from `tenant_id` when omitted. |
| `scope` | string | no | `api://{client_id}/.default` | OAuth scope for client credentials. |
| `comp_code` | string | no | — | Optional CMiC company code (`CompCode`). When set, streams are scoped to that company via API `q` filters. |

\* OAuth requires `client_secret` plus either `tenant_id` or `token_url`.

Run `tap-cmic --about` (or `tap-cmic --about --format=markdown`) for the authoritative schema for your installed version.

### Example Basic Auth `config.json`

```json
{
  "start_date": "2000-01-01T00:00:00Z",
  "base_url": "https://atlas-api.cmiccloud.com/cmicprod",
  "client_id": "Client_ID",
  "user_id": "User_ID",
  "password": "YOUR_PASSWORD",
  "comp_code": "001"
}
```

### Example OAuth `config.json`

```json
{
  "start_date": "2000-01-01T00:00:00Z",
  "base_url": "https://atlas-api-oauth.cmiccloud.com/cmicprod",
  "client_id": "ENTRA_APPLICATION_CLIENT_ID",
  "client_secret": "ENTRA_CLIENT_SECRET",
  "tenant_id": "ENTRA_TENANT_ID",
  "comp_code": "001"
}
```

Mint or refresh a token into the config file:

```bash
tap-cmic --config config.json --access-token
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
