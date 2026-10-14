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
           --env active.postman_environment.json \
           --website <your connector website> --privacy-url <your privacy policy URL> \
           --out ./connector

   Output: `apiDefinition.swagger.yaml` / `.json` (Swagger 2.0, validated) and `apiProperties.json`. The exit code is non-zero if validation fails or the definition is 1 MB or larger.
   - The script stops if the auth URLs or scopes still contain undefined `{{variables}}`.
   - `x-api` and `offline_access` are always added to the scopes (change with `--extra-scopes`).
   - Read the `WARNING:` lines. Requests that aren't API calls (the Documents API's blob upload URL) or that duplicate an existing method + path are skipped and listed there. In the current collection, "Create document" is listed as `GET /documents/v1/documents`, the same as "List documents (minimal)", so it is skipped. Report that to Business Fitness.

4. Review the YAML before deploying:
   - Check `securityDefinitions`: the script maps Postman OAuth2 → `accessCode` flow, API key → header key, and Bearer → an Authorization header connection parameter. Fill `clientId` in `apiProperties.json`. The connector uses a per-connector redirect URI (`redirectMode: GlobalPerConnector`): after creating the connector, copy the Redirect URL from its Security tab and register that exact URL with Business Fitness. The shared global redirect `https://global.consent.azure-apim.net/redirect` no longer works for new connections.
   - Tighten inferred schemas. Types come from the example bodies in the collection: typed placeholders such as `"<boolean>"` are honoured, but a field that is `null` in the example is typed as string.
   - Add `x-ms-dynamic-values` on ID parameters (e.g. client ID → list-clients operation) as done for BGL's `fundId`.
   - Mark rarely used parameters `x-ms-visibility: advanced`.
   - 62 operations have no description in the collection; add one where the summary isn't self-explanatory.

5. Deploy:

       pac connector create --api-definition-file connector/apiDefinition.swagger.json \
           --api-properties-file connector/apiProperties.json --environment <env-id>

   `pac connector create` has no option for the OAuth client secret, so enter it on the connector's Security tab after creation. (The older `paconn create` CLI accepts `--secret`.)

6. Test a list endpoint with a repeated filter (e.g. deliverables with two `ExternalId` values). Repeated query keys are generated as arrays with `collectionFormat: multi`, and Microsoft's docs don't confirm Power Platform sends those as repeated keys.

## Using the connector in flows

- **Rate limits** (as published 21 Jun 2024): per firm 120 requests per 60 s and **10 concurrent**; per app 1,200 per 60 s and 100 concurrent. The firm limit is shared by every app the firm uses. "Apply to each" runs one item at a time by default. If you raise its concurrency, keep total parallelism (loops, parallel branches and simultaneous flow runs) at 10 or less, and expect 429 responses (with `Retry-After`) on bulk work.
- **Pagination** uses `Page` / `PageSize` and returns `records`, `recordsCount`, `page`, `pages`, `pageSize`. Power Automate's built-in pagination needs a `nextLink`, so flows must loop over pages themselves. Max `PageSize` is 100 on `/detailed` endpoints.
- **Errors** come back as `{type, title, detail, status, traceId}`, modelled as the `Error` definition. A 402 means the firm has no subscription for that product (e.g. Workflow).
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
