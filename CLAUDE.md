# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo builds a Microsoft Power Platform custom connector for the Business Fitness "Active" API. No Microsoft-published connector exists. The API's endpoints come only from Business Fitness's Postman collection. **Never invent endpoints, paths or schemas**; everything is generated from the real collection.

The collection JSON can be downloaded directly from `https://development.businessfitness.com/api/collections/31711831/2s9Yynm4V5?segregateAuth=true&versionTag=latest`. Its folder and request descriptions are the API documentation: auth, scopes, rate limits, pagination and error format. The environment template that holds `auth_url`, `access_token_url` and `scopes` is not public. README.md records the API facts and the open questions for Business Fitness.

The work follows an earlier BGL SF360 connector (that repo is not included here). Its conventions are `x-ms-summary` on fields, tags taken from Postman folders, operationIds taken from request names, and `x-ms-dynamic-values` on ID parameters.

## Commands

```bash
pip install -r requirements.txt
python3 -m unittest discover -s tests                     # all tests
python3 -m unittest tests.test_postman2pp.EndToEnd        # one test class

python3 postman2pp.py <collection.json> --title "Business Fitness Active" \
    --env <environment.json> --out ./connector [--host ...] [--website ... --privacy-url ...]

pac connector create --api-definition-file connector/apiDefinition.swagger.json \
    --api-properties-file connector/apiProperties.json --environment <env-id>
```

- The converter exits with status 1 in three cases:
  - Auth settings still contain undefined `{{variables}}`.
  - Swagger validation fails.
  - `apiDefinition.swagger.json` is 1 MB or larger, which Power Platform rejects. Indented JSON falls back to compact form before this limit is hit.
- `pac connector create` has no client-secret option, so the OAuth secret is entered on the connector's Security tab after creation.

## How `postman2pp.py` works

`main()` loads the collection and environment, then calls `build_security`, `build_paths`, `build_spec` and `validate`.

- **Two input formats.** It accepts both a Postman v2.1 export and the Documenter JSON. The Documenter JSON stores `oauth2` settings as `{basicConfig, advancedConfig}`, the URL as a raw string plus `urlObject`, and descriptions as HTML. `auth_config()`, `request_url()` and `text()` hide those differences.
- **Auth** (`build_security`). It uses the first auth block found: collection level, then folders, then requests. OAuth2 scopes are the union of every block's scopes plus `--extra-scopes`, which defaults to `x-api offline_access`. OAuth2 uses `redirectMode: GlobalPerConnector`.
- **Operations** (`build_paths` / `build_operation`).
  - Folders become tags. Nested folders are flattened, with the innermost folder winning, and tags with no operations are dropped.
  - Typed placeholders such as `<uuid>`, `<integer>` and `<dateTime>` in query values, path variables and example bodies become Swagger types and formats (`PLACEHOLDER_TYPES`).
  - A query key repeated in the collection means the API takes a list, so it becomes one `array` parameter with `collectionFormat: multi`.
  - 2xx example bodies get inferred schemas. Every other status code points at the shared `Error` definition, which is the API's `{type, title, detail, status, traceId}` body.
  - Requests are skipped with a `WARNING:` line in two cases: when they duplicate an earlier method and path, or when their URL is a runtime variable rather than an API path (e.g. the Documents API's `{{upload_url}}` blob upload).
- **Labels.** `label()` builds every `x-ms-summary` from the field name in Title Case, keeping acronyms in capitals (`clientID` → "Client ID"). Parameter `name`s and property keys are never changed.
- **Example parsing.** `parse_json_loose()` scans character by character. It turns `{{vars}}` into strings and strips `//` and `/* */` comments only outside string literals, so URLs in examples survive.

## Manual review after generation

README.md, step 4, lists the hand edits to make before deploying: `clientId`, the redirect URL registration, tightening inferred types, `x-ms-dynamic-values`, and advanced visibility.
