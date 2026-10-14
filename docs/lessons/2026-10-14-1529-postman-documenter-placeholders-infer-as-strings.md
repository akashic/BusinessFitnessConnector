---
id: 2026-10-14-1529-postman-documenter-placeholders-infer-as-strings
title: Postman Documenter examples use "<type>" placeholders that infer as strings
applies_when: >
  inferring parameter or body schemas from a Postman Documenter collection whose example
  values are placeholders such as "inactive": "<boolean>" or Page=<integer>
rule: >
  When inferring types from Postman Documenter examples, map placeholders like <uuid>,
  <integer>, <boolean> and <dateTime> to their Swagger type and format, because taken
  literally every one of them is a string and the connector loses all its non-string types.
lesson_type: pitfall
phase: implementation
domain: [api]
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
    commit e0b9db3 (postman2pp.py PLACEHOLDER_TYPES / placeholder_schema;
    tests/test_postman2pp.py InferSchema.test_placeholders_are_typed); Business Fitness
    collection query strings contain 123 <uuid>, 113 <dateTime>, 93 <integer>, 33 <boolean>
  author:
related: [2026-10-14-1529-review-generator-against-real-collection]
proposed_tags: []
---

When a connector's schemas are inferred from a Postman Documenter collection, the example values are typed placeholders such as `"<boolean>"` or `<uuid>`. Inferring from the value's JSON type makes every one of them a string.

## What happened
Business Fitness's request bodies look like `"inactive": "<boolean>"`, and its query strings like `PageSize=<integer>&ModifiedSince=<dateTime>`. The original `postman2pp.py` inferred types from the JSON value, so all of these became `type: string`: booleans, integers, UUIDs and dates in both query parameters and bodies. Flow makers would get text boxes where they should get toggles, numbers and date pickers, and request bodies would carry strings where the API expects other types. This was found while inspecting the collection's format during the fix pass. It was missed by the initial code review.

## Why it happened
Documenter generates example requests from the API's own type metadata and writes the type name in angle brackets instead of a sample value. A v2.1 export of a hand-built collection usually has real sample values instead.

## What to do instead
- Treat a string matching `^<(\w+)>$` as a type hint: `string`, `uuid` (string/uuid), `integer`, `long` (integer/int64), `number`, `double`, `boolean`, `date`, `dateTime` (string/date-time). Fall back to string for unknown names such as `<token-name>`.
- Apply the same mapping to path variables (`urlObject.variable[].value`) and query values, not just bodies.

## How to recognise it early
A generated definition where nearly every field is `type: string`, or `grep -c '"<boolean>"'` returning hits in the collection.

## When this does NOT apply
Collections whose examples are real captured values. Those infer correctly from JSON types.
