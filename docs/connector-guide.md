# Build, deploy and use the Business Fitness Active connector

## Findings (23 Sep 2026, updated 14 Oct 2026)

- **No Microsoft-published connector exists.** Microsoft's connector reference has no entry for Business Fitness, Active, Active Ledger, Active Workpapers or HowNow. Business Fitness's only Microsoft marketplace listing is the *Active Ledger & Reporting* Excel add-in (an Office add-in, not a Power Platform connector).
- **Business Fitness does publish an API** ("Active API"), documented at https://development.businessfitness.com/ and on the Postman API Network under the publisher *business-fitness* (workspace "Business Fitness APIs", collection "Active API - Documentation", collection ID `d6eb89b7-b41a-4051-a9e0-4b8197eeec0d`).
- **The collection can be downloaded directly** as JSON from `https://development.businessfitness.com/api/collections/31711831/2s9Yynm4V5?segregateAuth=true&versionTag=latest` (135 requests across the Core, Workflow, Workpapers, Ledger and Reporting, and Documents APIs). The environment template is not public; it has to be forked in Postman. **No endpoints have been invented**; the connector is generated from this collection.
- **Auth:** OAuth 2.0 authorisation code with PKCE against `https://identity.businessfitness.com.au/connect/authorize` and `/connect/token`. Every request needs the `x-api` scope; `offline_access` gives refresh tokens; the other scopes are `core`, `workflow`, `workpapers`, `ledger` and `documents`, each with `.read` / `.write` variants.
- **Only "service accounts" can call the API.** A service account must be an Active user with the Admin or Owner role, so every connection to this connector is made by a privileged account. Plan connection sharing and DLP (data loss prevention) policies around that.

## Build the connector (same method as BGL, automated)

1. Get the collection, either:
   - download the JSON above, or
   - open https://development.businessfitness.com/, click **Run in Postman**, fork it, and use **... > Export > Collection v2.1** → `active-api.postman_collection.json`.
2. Get an environment file that defines `auth_url`, `access_token_url` and `scopes`. Fork the "Active API Environment Template" in Postman, fill it in, and export it (Environments > ... > Export) → `active.postman_environment.json`.
3. Generate the connector files:

       pip install -r requirements.txt
       python3 postman2pp.py active-api.postman_collection.json \
           --title "Business Fitness Active" \
           --description "Work with clients, jobs, workpapers, ledgers and documents in Business Fitness Active." \
           --env active.postman_environment.json \
           --website <your connector website> --privacy-url <your privacy policy URL>

   Output goes to `./connector` (change with `--out`): `apiDefinition.swagger.yaml` / `.json` (Swagger 2.0, validated) and `apiProperties.json`. `connector/` and `*.postman_environment.json` are git-ignored; environments can hold client IDs, test record IDs or tokens.
   - The script exits with an error (code 1, message on stderr) if:
     - the auth URLs or scopes still contain undefined `{{variables}}`;
     - an OAuth URL isn't `https`;
     - no request has an absolute URL and `--host` isn't given;
     - validation fails, or the definition is 1 MB or larger.

     In the last two cases the output folder is left unchanged, so a later deploy can't pick up a broken definition. The failed output is written to a temporary folder named in the error, for inspection.
   - `x-api` and `offline_access` are always added to the scopes (change with `--extra-scopes`). Every connection requests every scope in the environment, so if read-only flows don't need write access, put only `.read` scopes in the environment.
   - Only a URL's leading `{{base_url}}`-style variable is filled from the environment. Variables inside paths stay as path parameters, so test values from the environment never end up in the connector.
   - Query parameters whose description starts with "(Required)" are marked required.
   - From the Active API docs: `Search` parameters get `maxLength: 64`, and `PageSize` on `/detailed` endpoints gets `maximum: 100`.
   - Read the `WARNING:` lines:
     - Some requests are skipped:
       - requests that aren't API calls (the Documents API's blob upload URL);
       - requests on a different host from the collection's API host;
       - requests that duplicate an existing method + path, or differ from one only in letter case.

       In the current collection, "Create document" is listed as `GET /documents/v1/documents`, the same as "List documents (minimal)", so it is skipped. Report that to Business Fitness.
     - Operations with no usable example success response are listed. The collection has no example responses for the 7 Documents API actions, so their output is untyped until you add a response schema by hand.
     - A body on a request other than `POST`, `PUT` or `PATCH` is dropped and listed, because Power Platform connectors can't send it.
     - A `--title` over 30 characters is flagged (Microsoft's limit).

4. Review the YAML before deploying:
   - Check `securityDefinitions`: the script maps Postman OAuth2 → `accessCode` flow, API key → header key, and Bearer → an Authorization header connection parameter. Fill `clientId` in `apiProperties.json`. The connector uses a per-connector redirect URI (`redirectMode: GlobalPerConnector`): after creating the connector, copy the Redirect URL from its Security tab and register that exact URL with Business Fitness. The shared global redirect `https://global.consent.azure-apim.net/redirect` no longer works for new connections.
   - Tighten inferred schemas. Types come from the example bodies in the collection: typed placeholders such as `"<boolean>"` are honoured, but a field that is `null` in the example is typed as string.
   - Add `x-ms-dynamic-values` on ID parameters (e.g. client ID → list-clients operation) as done for BGL's `fundId`.
   - Mark rarely used parameters `x-ms-visibility: advanced`.
   - 62 operations have no description in the collection; add one where the summary isn't self-explanatory.
   - Run Power Platform's own validator, which checks rules that `openapi-spec-validator` doesn't: `paconn validate --api-def connector/apiDefinition.swagger.json` (needs `paconn login`).
     - Expect about 25 "PartialDuplicateOperationPath" warnings. They come from the API's design, with pairs like `/clients/entities/{id}` and `/clients/entities/detailed`, and can't be avoided.
     - Watch for "UnrecognizedTypeFormat" (the output uses `format: uuid`) and "CollectionFormatValueNotSupported" (`multi`). Microsoft's docs don't say whether these are supported.

5. Deploy:

       pac connector create --api-definition-file connector/apiDefinition.swagger.json \
           --api-properties-file connector/apiProperties.json --environment <env-id>

   `pac connector create` has no option for the OAuth client secret, so enter it on the connector's Security tab after creation. (The older `paconn create` CLI accepts `--secret`.)

6. Test a list endpoint with a repeated filter (e.g. deliverables with two `ExternalId` values). Repeated query keys are generated as arrays with `collectionFormat: multi`, and Microsoft's docs don't confirm Power Platform sends those as repeated keys.

## Using the connector in flows

- **Rate limits** (as published 21 Jun 2024): per firm 120 requests per 60 s and **10 concurrent**; per app 1,200 per 60 s and 100 concurrent. The firm limit is shared by every app the firm uses. "Apply to each" runs one item at a time by default. If you raise its concurrency, keep total parallelism (loops, parallel branches and simultaneous flow runs) at 10 or less, and expect 429 responses (with `Retry-After`) on bulk work.
- **Pagination** uses `Page` / `PageSize` and returns `records`, `recordsCount`, `page`, `pages`, `pageSize`. Power Automate's built-in pagination needs a `nextLink`, so flows must loop over pages themselves. Max `PageSize` is 100 on `/detailed` endpoints.
- **Errors** come back as `{type, title, detail, status, traceId}`. Error responses aren't typed in the connector, because Power Platform only uses one response schema per action and flags schemas on `default`. Read the error from the failed action's outputs instead (e.g. `outputs('Get_a_client')?['body/detail']`). A 402 means the firm has no subscription for that product (e.g. Workflow).
- **Enums** accept either the integer or the name (`6` or `"SuperannuationFund"`).

## Questions for Business Fitness (developers@ / support@businessfitness.com)

- Is API access included in the firm's Active subscription, or partner-only?
- Their docs describe a PKCE flow. Will they issue a confidential client (client ID + secret) for a Power Platform connector? Microsoft's custom-connector docs don't document PKCE support for Generic OAuth 2.
- Will they accept the connector's per-connector redirect URL (`https://global.consent.azure-apim.net/redirect/<connector-id>`)?
- Sandbox availability and whether it can be seeded with demo clients.
- Token lifetimes, and whether grace periods can be arranged for bulk loads.
- Whether "Active Sync" (their practice-management import) would conflict with API writes to clients.
- The "Create document" request in the collection is listed as `GET`; should it be `POST`?

The BGL risk analysis (rate limits, idempotency, field ownership, DLP, gateway, outbox pattern) applies unchanged once the write endpoints are known.
