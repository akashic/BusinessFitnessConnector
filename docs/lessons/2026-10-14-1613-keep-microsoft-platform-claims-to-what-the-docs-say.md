---
id: 2026-10-14-1613-keep-microsoft-platform-claims-to-what-the-docs-say
title: Claims about Power Platform behaviour were widened beyond what Microsoft's docs say
applies_when: >
  turning a Microsoft Learn rule or limit into generator code, a warning message or connector
  documentation, e.g. a validator rule, a default setting or a size limit
rule: >
  When encoding or documenting Power Platform behaviour, scope the check and the wording to exactly
  what the cited Microsoft page says and quote the rule name, and mark anything wider as unverified,
  because widened claims dropped valid data and put wrong advice into the docs.
lesson_type: anti-pattern
phase: implementation
domain: [process, integration]
tech: [power-platform-custom-connectors, power-automate]
scope: this-org
cost_if_ignored: rework
confidence: one-off
status: active
superseded_by:
expires:
provenance:
  projects: [business-fitness-connector]
  date: 2026-10-14
  source: pr-review
  evidence: >
    commit a03d07a dropped request bodies on every method except POST/PUT/PATCH, with the warning
    "Power Platform connectors can only send bodies with POST, PUT and PATCH"; Microsoft's rule
    BodyOrFormDataParameterInFetchOperationNotAllowed covers fetch (GET) operations only
    (https://learn.microsoft.com/connectors/custom-connectors/certification-swagger-validator-rules).
    Corrected in build_operation (FETCH_METHODS) with test RequestHandling.test_body_on_a_delete_is_kept.
    Earlier, commit 1c292fa ("Correct the flow concurrency guidance: Apply to each is sequential by
    default") reworded the guide and README after a review claimed loops exceed 10 concurrent requests
    "at default concurrency"; Microsoft's limits page says the default is 1
    (https://learn.microsoft.com/power-automate/limits-and-config).
  author:
related:
  - 2026-10-14-1552-openapi-spec-validator-misses-power-platform-rules
  - 2026-10-14-1529-active-api-firm-limit-is-10-concurrent-requests
proposed_tags: []
---

When a Microsoft Learn rule or limit is turned into generator code, a warning or documentation, it's easy to widen it into a broader claim the docs don't make. That widened claim then drops valid data or gives users wrong advice.

## What happened
Twice in this project, a Power Platform claim was stated more strongly than its source:
- **Request bodies.** Microsoft's validator rule "BodyOrFormDataParameterInFetchOperationNotAllowed" forbids bodies on fetch operations (`GET`). `postman2pp.py` (commit a03d07a) instead dropped bodies on every method except POST/PUT/PATCH, including `DELETE`. Its warning and the connector guide told users "Power Platform connectors can only send bodies with POST, PUT and PATCH". A synthetic bulk-delete request lost its body, and a fourth review found nothing in Microsoft's docs to support the wider rule.
- **Loop concurrency.** A review stated that an "Apply to each" loop "at default concurrency will easily exceed 10 concurrent requests". Microsoft's limits page says Apply to each defaults to concurrency 1. The guide and README were reworded in commit 1c292fa before the wrong claim spread further.

## Why it happened
In both cases the stronger claim was written from memory of how the platform "usually" behaves, not from the page being cited. The code and the docs then repeated it confidently.

## What to do instead
- Quote the rule name or limit in the code comment and warning text (as `FETCH_METHODS` now does), and implement exactly that scope.
- If something wider seems likely, say so as unverified in the docs ("Microsoft's docs don't confirm…"), not as fact. This repo already does that for `collectionFormat: multi` and `format: uuid`.
- Before writing a platform default or limit into docs, look it up on Microsoft Learn in the same session.

## How to recognise it early
Warning text or docs that state platform behaviour ("connectors can only…", "by default…") with no Microsoft rule name or page behind it.
