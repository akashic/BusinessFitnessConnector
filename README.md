# Business Fitness Active connector for Power Platform

A Microsoft Power Platform custom connector for the [Business Fitness](https://www.businessfitness.com.au/) **Active API**, so Power Automate flows, Power Apps and Copilot Studio can work with Active's clients, workflow jobs, workpapers, ledgers and documents.

Microsoft doesn't publish a connector for Business Fitness. Business Fitness publishes its API only as a Postman collection. So this repo doesn't hand-write the connector: it **generates** the connector from that collection, which keeps it in step with the API and means no endpoints are invented.

## How it works

```
Business Fitness Postman collection ─┐
  (135 requests, public JSON)        │
                                     ├─► postman2pp.py ─► apiDefinition.swagger.json / .yaml
Postman environment ─────────────────┘                    apiProperties.json
  (auth URLs, scopes)                                            │
                                                                 ▼
                                          pac connector create ─► custom connector in your
                                                                  Power Platform environment
```

`postman2pp.py` reads the collection and writes the two files a custom connector needs:

- **`apiDefinition.swagger.json` / `.yaml`:** the API's operations in Swagger 2.0, the only OpenAPI version Power Platform accepts. Postman folders become groups (tags), request names become actions, and the example requests and responses determine parameter and field types.
- **`apiProperties.json`:** how users sign in. The Active API uses OAuth 2.0, with each connector getting its own redirect URL.

It also turns the collection into something Power Platform will accept:

- Field labels are made readable: `clientID` becomes "Client ID". Action names follow Microsoft's string guidance, with no trailing punctuation.
- Typed placeholders such as `<uuid>` and `<boolean>` become real types, and parameters documented as "(Required)" are required.
- Each action has a single response schema, which is what Power Platform's designer and validator expect.
- Requests that can't be connector actions are skipped with a warning, such as the direct blob upload, a duplicated route or a request on another host. Actions with no example response are flagged too.
- Hand edits (response schemas, dropdowns, descriptions) live in `connector-overrides.yaml` and are merged in on every run, so regenerating never loses them.
- It stops with an error if auth settings are missing or not `https`, if the API host is unknown, or if the result is invalid or too large for Power Platform (1 MB or more). A failed run never overwrites the output folder.

## Repository layout

| Path | What it is |
|---|---|
| `postman2pp.py` | The generator. |
| `tests/` | Unit and end-to-end tests for the generator (`unittest`, no network needed). |
| `connector-overrides.yaml` | Hand edits merged into the generated connector on every run. Keyed by operation ID; stale entries are an error. |
| `docs/connector-guide.md` | Full guide: build and deploy steps, review checklist, API facts (auth, rate limits, pagination, errors), and open questions for Business Fitness. |
| `requirements.txt` | Python dependencies (PyYAML, openapi-spec-validator). |
| `CLAUDE.md` | Notes for Claude Code working in this repo. |

The generated connector files aren't committed. Generate them into a folder such as `connector/`.

## Quick start

Requires Python 3 and, to deploy, the [Power Platform CLI](https://learn.microsoft.com/power-platform/developer/cli/introduction) (`pac`).

```bash
pip install -r requirements.txt

# 1. Get the collection (public)
curl -o active-api.json \
  "https://development.businessfitness.com/api/collections/31711831/2s9Yynm4V5?segregateAuth=true&versionTag=latest"

# 2. Get an environment file defining auth_url, access_token_url and scopes
#    (fork "Active API Environment Template" in Postman, fill it in, export it)

# 3. Generate the connector
python3 postman2pp.py active-api.json --title "Business Fitness Active" \
    --env active.postman_environment.json \
    --description "<what the connector is for>" \
    --website <your website> --privacy-url <your privacy policy URL>   # writes ./connector

# 4. Review, then deploy (see the guide for the review checklist)
pac connector create --api-definition-file connector/apiDefinition.swagger.json \
    --api-properties-file connector/apiProperties.json --environment <env-id>
```

Run the tests with `python3 -m unittest` from the repo root. GitHub Actions runs them on every push and pull request (`.github/workflows/tests.yml`, Python 3.10 and 3.14).

## Things to know before using it

- **API access:** Business Fitness has to provision an integration (client ID, scopes and redirect URL) for your firm. Only Active users with the Admin or Owner role can be API "service accounts", so every connection is a privileged account.
- **Rate limits:** each firm gets 120 requests a minute and 10 at a time, shared by every app the firm uses. If you parallelise flows (loop concurrency, parallel branches or simultaneous runs), keep the total at 10 or less.
- **Paging:** list endpoints use `Page` / `PageSize`, so flows have to loop over the pages themselves.

The [connector guide](docs/connector-guide.md) has the details.

## Status

The generator produces a valid connector definition from the current collection: 133 actions across the Core, Workflow, Workpapers, Ledger and Reporting, and Documents APIs. The connector hasn't been deployed or tested against the live API yet. Before relying on it:

- **Sign-in:** Business Fitness documents a PKCE sign-in flow, and Microsoft doesn't document PKCE support for custom connectors. Ask Business Fitness to confirm a client-secret integration and the per-connector redirect URL.
- **List filters:** check that filters taking several values (e.g. two `ExternalId`s) are sent correctly.
- **Create document:** the collection lists "Create document" as a `GET`, so it's currently skipped.

These questions are tracked in the [connector guide](docs/connector-guide.md#questions-for-business-fitness-developers--supportbusinessfitnesscom).
