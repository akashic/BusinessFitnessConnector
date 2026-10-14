---
id: 2026-10-14-1529-postman-repeated-query-keys-break-swagger
title: Repeated query keys in a Postman collection make generated Swagger invalid
applies_when: >
  converting a Postman collection into a Swagger 2.0 custom connector definition and a
  request URL repeats a query key, e.g. ExternalId=<string>&ExternalId=<string>
rule: >
  When a Postman request repeats a query key, emit one array parameter with
  collectionFormat: multi instead of one parameter per occurrence, because duplicate
  parameters fail Swagger validation and the repetition is how Postman shows a filter that
  takes a list.
lesson_type: pitfall
phase: implementation
domain: [api, integration]
tech: [power-platform-custom-connectors, postman]
scope: this-stack
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
    commit e0b9db3 (postman2pp.py build_operation / typed_param;
    tests/test_postman2pp.py EndToEnd.test_collection); Business Fitness collection request
    GET /workflow/v1/deliverables, which repeats ExternalId and Code
  author:
related: [2026-10-14-1529-review-generator-against-real-collection, 2026-10-14-1703-paconn-validate-always-applies-certification-rules]
proposed_tags: []
---

When a Postman collection is converted to a Swagger 2.0 custom connector, a query key repeated in a request URL produces duplicate parameters and the whole definition fails validation.

## What happened
The original `postman2pp.py` added one parameter for each query entry. In the Business Fitness collection, `GET /workflow/v1/deliverables` lists `ExternalId` and `Code` twice each. openapi-spec-validator then rejected the whole definition with `VALIDATION FAILED`, quoting that operation's parameter list. Nothing could be deployed until this was fixed. It only showed up when the script was run on the real collection.

## Why it happened
Postman has no array type for query parameters, so its generated docs show a list-valued filter by repeating the key. Swagger requires each (name, in) pair to be unique per operation.

## What to do instead
- Count keys per request. When a key appears more than once, emit a single `type: array` parameter with `items` typed from the placeholder and `collectionFormat: multi`, which sends `?Key=a&Key=b`.
- Power Platform's validator (14 Oct 2026) accepts `collectionFormat: multi` for a private custom connector but rejects it under certification rules ("The 'collectionFormat' keyword value 'Multi' is not supported"). For certification use `csv`, no `collectionFormat`, or a single-value string; all three passed. See [paconn-validate-always-applies-certification-rules](2026-10-14-1703-paconn-validate-always-applies-certification-rules.md).
- Still untested: whether Power Platform actually sends `multi` arrays as repeated keys at runtime. Test a call with two values on the deployed connector (docs/connector-guide.md, step 6). If it doesn't, the fallback is a single string parameter.

## How to recognise it early
The validator error names a query parameter that appears twice, or `grep -o 'Key=' <raw url> | sort | uniq -d` finds repeats.
