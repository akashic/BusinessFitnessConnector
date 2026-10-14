---
id: 2026-10-14-1603-active-api-paging-parameter-names-differ-in-case
title: Active API paging and search parameters are PascalCase in some APIs, camelCase in others
applies_when: >
  writing generator rules, flow expressions or documentation that refer to the Business Fitness
  Active API's Page, PageSize or Search query parameters by name
rule: >
  When matching or documenting Active API paging and search parameters, match names
  case-insensitively and use each API's own spelling in flows (Page/PageSize/Search in Core and
  Workflow, page/pageSize/search in Workpapers and Ledger), because one spelling misses half
  the endpoints.
lesson_type: pitfall
phase: implementation
domain: [api]
tech: [power-platform-custom-connectors, postman]
scope: this-project
cost_if_ignored: minor
confidence: one-off
status: active
superseded_by:
expires:
provenance:
  projects: [business-fitness-connector]
  date: 2026-10-14
  source: direct-experience
  evidence: >
    Generated definition from the Business Fitness collection
    (development.businessfitness.com/api/collections/31711831/2s9Yynm4V5): Core 13 Page/PageSize and
    7 Search; Workflow 18 Page/PageSize and 6 Search; Workpapers 13 page/pageSize and 5 search;
    Ledger 2 page/pageSize. postman2pp.py build_operation applies the Search/PageSize limits with
    name.lower(); tests/test_postman2pp.py RequestHandling.test_active_api_search_and_page_size_limits
  author:
related: [2026-10-14-1552-active-api-required-params-only-in-descriptions]
proposed_tags: []
---

When code, flows or docs refer to the Active API's paging and search parameters by name, one spelling only covers half the API. Core and Workflow use `Page`, `PageSize` and `Search`, while Workpapers and Ledger use `page`, `pageSize` and `search`.

## What happened
Adding the documented limits (`Search` up to 64 characters, `PageSize` up to 100 on `/detailed` endpoints), a check of the generated definition showed the spellings split by API: Core and Workflow use PascalCase (31 `PageSize`, 13 `Search`), and Workpapers and Ledger use camelCase (15 `pageSize`, 5 `search`). An exact-name match would have capped only half of the `/detailed` endpoints. The Business Fitness docs' own Pagination example uses `Page=5&PageSize=100`, which only matches the PascalCase APIs.

## Why it happened
Each Active API area appears to have been built separately. The collection reflects each one's actual parameter names, and the generator keeps names exactly as given, which it must, since they're sent to the API.

## What to do instead
- Match parameter names case-insensitively in generator rules (`name.lower() == 'pagesize'`), but never rename them in the output.
- In flows, copy the parameter name from the action itself, not from the Business Fitness Pagination docs.
- The Documents API lists no paging parameters in the collection; check its docs before assuming either spelling.

## When this does NOT apply
Response fields: the paging envelope (`records`, `recordsCount`, `page`, `pages`, `pageSize`) is documented as camelCase across the API.
