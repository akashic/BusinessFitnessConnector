---
id: 2026-10-14-1529-generate-connectors-from-vendor-postman-collection
title: Generate custom connectors from the vendor's Postman collection, not by hand
applies_when: >
  building a Power Platform custom connector for a vendor API that is published as a
  Postman collection
rule: >
  When a vendor publishes its API as a Postman collection, generate the Swagger 2.0
  definition and apiProperties.json with postman2pp.py and hand-edit only the review items,
  because a hand-written definition drifts from the API and invites invented endpoints.
lesson_type: convention
phase: design
domain: [integration, api]
tech: [power-platform-custom-connectors, postman]
scope: this-org
cost_if_ignored: rework
confidence: one-off
status: active
superseded_by:
expires:
provenance:
  projects: [business-fitness-connector]
  date: 2026-10-14
  source: direct-experience
  evidence: >
    commit e0b9db3 (postman2pp.py; docs/connector-guide.md "Build the connector (same method
    as BGL, automated)"); README.md "How it works"
  author:
related: [2026-10-14-1529-review-generator-against-real-collection]
proposed_tags: []
---

When a vendor publishes its API as a Postman collection, build the Power Platform custom connector by generating it from that collection with `postman2pp.py` rather than writing the Swagger by hand.

## What happened
Business Fitness publishes the Active API only as a Postman collection: 135 requests across five APIs. The connector is generated from it, following the method used for the BGL SF360 connector. The repo's ground rule is that no endpoints, paths or schemas are invented; everything comes from the collection. Regenerating picks up vendor changes, and the generator's warnings flag collection mistakes (e.g. "Create document" listed as `GET`) rather than copying them silently.

## Why it works
The collection is the vendor's own source of truth: paths, query parameters with descriptions, auth configuration and example responses. Hand-transcribing 135 operations would introduce typos and invented details. Generating makes the result reproducible and reviewable.

## What to do instead
- Fetch the collection (a Postman export or the Documenter JSON) and an environment that defines the auth variables.
- Run `python3 postman2pp.py <collection> --title ... --env ... --out ./connector` and read the warnings.
- Hand-edit only the review checklist (docs/connector-guide.md, step 4): `clientId`, redirect registration, tighter types, `x-ms-dynamic-values`, advanced visibility.
- When the generator gets a vendor quirk wrong, fix the generator and add a test, rather than patching the output.

## When this does NOT apply
Vendors that publish a good OpenAPI 2.0 file can import it directly. OpenAPI 3 needs converting, since Power Platform accepts only 2.0.
