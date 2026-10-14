# Next steps

Recommendations as of 14 Oct 2026, in priority order.

## Where things stand

- **Generator:** `postman2pp.py` turns the Business Fitness Active API collection into a valid connector, with 133 actions. It has 42 tests, which CI runs on every non-documentation push.
- **Power Platform validation:** the definition passes Power Platform's validator for a private connector. Past the first stage, it also passes the full certification rule set, apart from 25 path warnings that come from the API's design. Results are in [docs/connector-guide.md](docs/connector-guide.md), step 4.
- **Hand edits:** these now go in [connector-overrides.yaml](connector-overrides.yaml) and survive regeneration.
- **Not yet done:** the connector hasn't been deployed or called against the live API. No validator can check how it behaves at runtime.

## 1. Send the Business Fitness email (blocker)

The draft is in [docs/business-fitness-questions-email.md](docs/business-fitness-questions-email.md). Send it now; it's the longest wait and the biggest risk.

- **PKCE versus client secret.** Business Fitness documents a PKCE sign-in, but Power Platform custom connectors use the authorization code flow with a client secret, and PKCE isn't documented for them. If Business Fitness can't issue a confidential client, the connector can't sign in.
- **Other questions in the email:**
  - the per-connector redirect URL and post-logout URL;
  - sandbox access;
  - token lifetimes;
  - the format for list filters;
  - conflicts with Active Sync;
  - the "Create document" request mislabelled as `GET`.
- **Then submit the integration request:** integration name, scopes (least privilege, plus `x-api` and `offline_access`), logo, the service-account user (Admin or Owner) and the redirect URL.

## 2. Deploy to a test environment

Once Business Fitness issues a client:

1. **Generate** with a real environment file (auth URLs and scopes) and `--website` / `--privacy-url`. See [docs/connector-guide.md](docs/connector-guide.md), step 3.
2. **Create the connector in a test environment.** Use `pac connector create … --solution-unique-name …` so it can move from dev to test to prod, or `paconn create --env …`. See [docs/guides/paconn-connector-testing.md](docs/guides/paconn-connector-testing.md), §7.
3. **Enter the client ID** in `apiProperties.json` and the **client secret** on the connector's Security tab.
4. **Register the Redirect URL** shown on the Security tab (`https://global.consent.azure-apim.net/redirect/<connector-id>`) with Business Fitness.

## 3. Test behaviour the validators can't see

Follow [docs/guides/paconn-connector-testing.md](docs/guides/paconn-connector-testing.md), §8, against the sandbox if possible:

- [ ] Sign in, then reuse the connection after an hour (token refresh via `offline_access`).
- [ ] A list filter with two values, e.g. two `ExternalId`s on deliverables. This settles how `collectionFormat: multi` is actually sent.
- [ ] Paging with `Page`/`PageSize` (or `page`/`pageSize` in Workpapers and Ledger) in a flow loop.
- [ ] A required parameter left blank, and an error body read from the action's outputs.
- [ ] A loop with raised concurrency stays under the firm-wide limit of 10 concurrent requests, and 429 responses are handled.

## 4. Fill in `connector-overrides.yaml`

- **Response schemas** for the 7 Documents API operations listed in the file, written from documented or observed responses, never invented.
- **Dropdowns** (`x-ms-dynamic-values`) on ID parameters, e.g. client ID → list clients and job ID → list jobs.
- **Descriptions** where an action's name isn't self-explanatory (62 have none), and `x-ms-visibility: advanced` on rarely used parameters.

Regenerate after each change; CI and the generator's errors catch overrides that no longer match.

## 5. Decide governance before anyone else uses it

- **Connections:** every connection is a Business Fitness Admin or Owner service account. Decide who owns the connection, and whether and with whom it's shared.
- **Data loss prevention (DLP):** decide which policy group the connector belongs in.
- **Scopes:** consider a separate read-only connector (only `.read` scopes) for flows that don't need to write.
- **Production:** plan how the connector moves to production through the solution.

## 6. Housekeeping

- **CI runner change:** GitHub moves `ubuntu-latest` to Ubuntu 26 from 19 Oct 2026; check the first CI run after that.
- **BGL connector:** check whether it still uses the old global OAuth redirect (`redirectMode: Global`), which no longer works for new connections.
- **paconn:** it was only installed in a temporary folder. Reinstall it when needed (guide §2), and run `paconn logout` after each use.
- **Collection updates:** when Business Fitness updates the collection, regenerate, review the `WARNING:` lines, and re-run validation.

## Not recommended now

- **Microsoft certification.** It would need descriptions on every action and parameter, `info.contact`, and a different list-filter format. It's only worth doing if the connector is to be published beyond your organisation.
- **More code review passes.** The last review found only polish. The remaining risks are in the steps above.
