# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo builds a Microsoft Power Platform custom connector for the Business Fitness "Active" API. No Microsoft-published connector exists. The API's endpoints come only from Business Fitness's Postman collection. **Never invent endpoints, paths or schemas**; everything is generated from the real collection.

The collection JSON can be downloaded directly from `https://development.businessfitness.com/api/collections/31711831/2s9Yynm4V5?segregateAuth=true&versionTag=latest`. Its folder and request descriptions are the API documentation: auth, scopes, rate limits, pagination and error format. The environment template that holds `auth_url`, `access_token_url` and `scopes` is not public. docs/connector-guide.md records the API facts and the open questions for Business Fitness.

The work follows an earlier BGL SF360 connector (that repo is not included here). Its conventions are `x-ms-summary` on fields, tags taken from Postman folders, operationIds taken from request names, and `x-ms-dynamic-values` on ID parameters.

## Commands

```bash
pip install -r requirements.txt
python3 -m unittest                                        # all tests (run from the repo root)
python3 -m unittest tests.test_postman2pp.EndToEnd         # one test class
```

CI (`.github/workflows/tests.yml`) runs the same `python -m unittest` on Python 3.10 and 3.14 for every push and pull request. Keep the code working on 3.10+ (the suite also passes on 3.9).

```bash
python3 postman2pp.py <collection.json> --title "Business Fitness Active" \
    --env <environment.json> [--out ./connector] [--description ...] [--host ...] [--website ... --privacy-url ...]

pac connector create --api-definition-file connector/apiDefinition.swagger.json \
    --api-properties-file connector/apiProperties.json --environment <env-id>
```

- The converter exits with status 1 when:
  - auth settings still contain undefined `{{variables}}`, or an OAuth URL isn't `https`;
  - no request has an absolute URL and `--host` isn't given;
  - Swagger validation fails;
  - `apiDefinition.swagger.json` is 1 MB or larger, which Power Platform rejects. Indented JSON falls back to compact form before this limit is hit.

  Input problems are raised as `ConfigError`. All errors go to stderr; summary, notes and warnings go to stdout.
- Output goes to `--out` (default `connector/`, git-ignored) only when generation succeeds. If validation or the size check fails, `--out` is left untouched and the files go to a `postman2pp-failed-*` temp folder named in the error.
- openapi-spec-validator checks only generic Swagger. Power Platform's own rules (e.g. DefaultResponseHasSchema, OperationHasManyResponsesWithSchema) need Power Platform's validator. `paconn validate --api-def ...` always runs it with certification rules on (`enableConnectorCertificationRules=true`), which also demands descriptions, `info.contact` and no `collectionFormat: multi`. Those are certification-only. The validator also reports in stages, and certification-off checks are lenient. On 14 Oct 2026 the real definition passed with certification rules off, and passed the full certification rule set once those three were filled in, apart from 25 PartialDuplicateOperationPath warnings. See docs/connector-guide.md, step 4, and docs/guides/paconn-connector-testing.md.
- `pac connector create` has no client-secret option, so the OAuth secret is entered on the connector's Security tab after creation.

## How `postman2pp.py` works

`main()` loads the collection and environment, then calls `build_security`, `build_paths`, `build_spec` and `validate`.

- **Two input formats.** It accepts both a Postman v2.1 export and the Documenter JSON. The Documenter JSON stores `oauth2` settings as `{basicConfig, advancedConfig}`, the URL as a raw string plus `urlObject`, and descriptions as HTML. `auth_config()`, `request_url()` and `text()` hide those differences.
- **Auth** (`build_security`). It uses the first auth block found: collection level, then folders, then requests. OAuth2 scopes are the union of every block's scopes plus `--extra-scopes`, which defaults to `x-api offline_access`. OAuth2 uses `redirectMode: GlobalPerConnector`.
- **Operations** (`build_paths` / `build_operation`).
  - Folders become tags. Nested folders are flattened, with the innermost folder winning, and tags with no operations are dropped.
  - Typed placeholders such as `<uuid>`, `<integer>` and `<dateTime>` in query values, path variables and example bodies become Swagger types and formats (`PLACEHOLDER_TYPES`).
  - A query key repeated in the collection means the API takes a list, so it becomes one `array` parameter with `collectionFormat: multi`.
  - Only the first non-empty 2xx example gets a schema. Error codes and `default` get a description only, because Power Platform uses one response schema per action and flags schemas on `default`. There is no `definitions` section.
  - A parameter description starting "(Required)" (Business Fitness's convention) marks the parameter required, and the prefix is dropped.
  - URLs are resolved against the environment only for their leading `{{base_url}}`-style variable (`resolve(..., leading_only=True)`), so environment test values never get baked into paths.
  - `summary_text()` makes action names follow Microsoft's string guidance: no '/', at most 80 characters, ending alphanumeric. A trailing "(x)" becomes " - x".
  - `WARNING:` lines cover several cases.
    - A request is skipped when it:
      - duplicates an earlier method and path, or differs from one only in letter case (Power Platform's PathRedefined rule);
      - uses a host other than the collection's API host (the first absolute URL's host, not `--host`);
      - has a runtime variable as its URL rather than an API path (e.g. the Documents API's `{{upload_url}}` blob upload).
    - A request body on GET/HEAD is dropped and listed (BodyOrFormDataParameterInFetchOperationNotAllowed); DELETE bodies are kept.
    - Body modes other than `raw` and `formdata` (urlencoded, file, graphql) are listed as not converted.
  - Schemas with no usable example use a copy of `UNTYPED`. Never share one dict object between places in the spec, or PyYAML writes `&id001` anchors into the YAML.
    - A non-delete operation with no usable example success response is listed, because its output is untyped.
    - `check_options()` lists a `--title` over 30 characters and a `--brand-color` that isn't `#RRGGBB`. It raises `ConfigError` for a `--website`/`--privacy-url` that isn't an absolute URL (UrlNotValid).
    - A `connectionId` parameter (reserved: ConnectionIdParameterNotAllowed) is dropped, or the request is skipped if it's a path parameter (`build_operation` returns `None`).
    - Missing OAuth scopes are listed; no placeholder scope is invented.
  - `load_json()` / `load_variables()` turn unreadable, non-object or keyless input into `ConfigError`, so bad files give one `ERROR:` line, not a traceback.
  - Business Fitness limits from its docs are applied to query parameters: `Search` gets `maxLength: 64`, and `PageSize` (any case) on `/detailed` paths gets `maximum: 100`.
  - A plain-string URL with no structured query has its query parsed from the raw string (`request_url`).
- **Labels and text.** `text()` strips only real HTML tags (so "a < b" survives) and flattens markdown. `label()` builds every `x-ms-summary` from the field name in Title Case, keeping acronyms in capitals (`clientID` → "Client ID"). Parameter `name`s and property keys are never changed.
- **Example parsing.** `parse_json_loose()` scans character by character. It turns `{{vars}}` into strings and strips `//` and `/* */` comments only outside string literals, so URLs in examples survive.

## Overrides

Hand edits never go in the generated `connector/` folder. They go in `connector-overrides.yaml`, which `main()` applies after `build_spec` and before validation.
- **Where it's found:** next to the collection file automatically, or via `--overrides`.
- **How it's applied** (`load_overrides` / `apply_overrides` / `merge`): operations are keyed by `operationId` and parameters by name. Mappings merge, `null` deletes a key, and a `schema` is replaced whole. `definitions` are added to the spec.
- **When it fails:** an unknown operation or parameter, removing a path parameter, or changing an `operationId` is a `ConfigError`, so a Business Fitness rename can't make an override silently stop applying.
- **Warnings after merging:** the "untyped output" warnings are computed after overrides (`build_paths` returns `untyped`; `is_untyped`). `response_rule_warnings` flags overrides that put a schema on `default` or on several responses.

## Manual review after generation

docs/connector-guide.md, step 4, lists the review before deploying: `clientId`, the redirect URL registration, `paconn validate`, and which edits belong in `connector-overrides.yaml` (response schemas, tighter types, `x-ms-dynamic-values`, advanced visibility, descriptions).
