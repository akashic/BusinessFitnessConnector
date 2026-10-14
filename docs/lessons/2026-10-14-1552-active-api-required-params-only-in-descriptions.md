---
id: 2026-10-14-1552-active-api-required-params-only-in-descriptions
title: The Active API collection marks required parameters only with a "(Required)" description
applies_when: >
  generating connector parameters from the Business Fitness Active API Postman collection, or
  deciding which query parameters a flow must fill in
rule: >
  When converting the Active API collection, mark a parameter required when its description starts
  with "(Required)" and drop that prefix, because Postman has no required flag for query
  parameters and the collection records requiredness only in that text.
lesson_type: pitfall
phase: implementation
domain: [api]
tech: [power-platform-custom-connectors, postman]
scope: this-project
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
    Business Fitness collection (development.businessfitness.com/api/collections/31711831/2s9Yynm4V5):
    73 parameter descriptions start "(Required)", none say "(Optional)"; 11 of them are query
    parameters, e.g. binderId on the Records queries, sourceId on Source Accounts, jurisdiction on
    Account Types. Fixed in postman2pp.py typed_param / REQUIRED_PREFIX_RE; covered by
    tests/test_postman2pp.py EndToEnd.test_collection (OfficeId)
  author:
related: [2026-10-14-1529-postman-documenter-placeholders-infer-as-strings]
proposed_tags: []
---

When a connector is generated from the Business Fitness Active API collection, required query parameters look optional, because the collection records requiredness only as a "(Required)" prefix in the parameter's description.

## What happened
The generator marked every query parameter `required: false`. The second review found 11 query parameters that Business Fitness documents as "(Required) …", including `binderId` on both Records queries, `sourceId` on Source Accounts and `jurisdiction` on Account Types. In Power Automate those would show as optional fields, so a flow maker could leave them blank and only find out from a 400 at runtime.

## Why it happened
Postman's request model has no required flag for query parameters. Business Fitness's generated docs carry the API's requiredness in description text instead. All 73 marked parameters, path and query, use exactly "(Required)"; none use "(Optional)".

## What to do instead
- Treat a description starting with "(Required)" (case-insensitive) as `required: true`, and remove the prefix so the description reads cleanly in the designer.
- Leave unmarked parameters optional. That's how the collection expresses optional.
- If Business Fitness changes the wording, the test fixture's `OfficeId` parameter shows the expected behaviour; check the collection's prefixes again.

## How to recognise it early
`grep -c '(Required)'` on the collection versus the number of `"required": true` query parameters in the output.

## When this does NOT apply
Path parameters are always required in Swagger regardless. Other vendors' collections may mark requiredness differently or not at all.
