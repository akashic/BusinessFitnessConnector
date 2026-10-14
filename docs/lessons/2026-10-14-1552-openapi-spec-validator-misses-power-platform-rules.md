---
id: 2026-10-14-1552-openapi-spec-validator-misses-power-platform-rules
title: openapi-spec-validator passes connector definitions that break Power Platform's rules
applies_when: >
  checking a generated or hand-written Swagger 2.0 custom connector definition with
  openapi-spec-validator (or any generic Swagger validator) before deploying it to Power Platform
rule: >
  When validating a custom connector definition, also check it against Microsoft's "Fix Swagger
  Validator errors" rules or run `paconn validate --api-def`, and give only the success response
  a schema, because generic validators pass schemas on 'default' and on several responses, which
  Power Platform flags as DefaultResponseHasSchema and OperationHasManyResponsesWithSchema.
lesson_type: pitfall
phase: testing
domain: [api, integration]
tech: [power-platform-custom-connectors]
scope: this-stack
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
    Microsoft Learn "Fix Swagger Validator errors"
    (https://learn.microsoft.com/connectors/custom-connectors/certification-swagger-validator-rules);
    postman2pp.py build_operation (responses block) and tests/test_postman2pp.py
    EndToEnd.test_collection ("only one response per operation carries a schema"); a GET with form
    data also passed openapi-spec-validator despite BodyOrFormDataParameterInFetchOperationNotAllowed
    (fixed in build_operation, test RequestHandling.test_form_data_on_a_get_is_dropped_with_a_warning); a
    query parameter named connectionId (ConnectionIdParameterNotAllowed) and --website "not a url"
    (UrlNotValid) also exited 0 at commit 3925eaa (fixed in build_operation and check_options, tests
    InputChecks.test_reserved_connection_id_parameter and test_invalid_website_url_is_an_error); the definition
    at commit 1c292fa put an Error schema on 'default' and every error code for all 133 operations
  author:
related: [2026-10-14-1529-review-generator-against-real-collection, 2026-10-14-1703-paconn-validate-always-applies-certification-rules, 2026-10-14-1703-power-platform-validator-reports-in-stages, 2026-10-14-1703-certification-off-validation-is-lenient]
proposed_tags: []
---

When a custom connector definition is checked only with openapi-spec-validator, it can be reported as "valid Swagger 2.0" while breaking Power Platform's own validator rules, which the generic tool doesn't know about.

## What happened
To model Business Fitness's error body, `postman2pp.py` pointed `default` and every non-2xx response at a shared `Error` definition. openapi-spec-validator passed it, and so did the tests. A second review against Microsoft Learn's validator rules found all 133 operations broke two rules:
- "DefaultResponseHasSchema": the 'default' response should not have schema definition;
- "OperationHasManyResponsesWithSchema": only one schema will be used in the designer.

A later review found a third case: a `GET` with form data passed openapi-spec-validator, although Microsoft's "BodyOrFormDataParameterInFetchOperationNotAllowed" rule forbids it. A fifth review found two more: a parameter named `connectionId` ("ConnectionIdParameterNotAllowed") and a connector-metadata website that isn't an absolute URL ("UrlNotValid"). Running Power Platform's own validator later (14 Oct 2026) settled the open items. `format: uuid` was accepted. `multi` was rejected only under certification rules. The definition produced 25 "PartialDuplicateOperationPath" warnings from the API's routes. That validator has gaps of its own: it reports in stages, its certification-off mode is lenient, and it never flagged the GET form data. See the related lessons.

## Why it happened
openapi-spec-validator implements the OpenAPI 2.0 specification. Power Platform adds its own rules for its designer and runtime, published as Microsoft's error list and checked by Power Platform's validateApiSwagger endpoint (`paconn validate` always runs it in certification mode). Whether importing in the maker portal enforces the same rules is untested.

## What to do instead
- Give one response a schema: the first non-empty 2xx example. Give error codes and `default` a description only, and read error bodies from the action's outputs in flows.
- Before deploying, run `paconn validate --api-def connector/apiDefinition.swagger.json` (needs `paconn login`), or at least scan Microsoft's rule list for anything the generator emits.
- When adding a feature to the generator, look its constructs up in the rule list, not just the Swagger spec.

## How to recognise it early
Any `$ref` or `schema` under `default`, or more than one response with `schema` in an operation.

## When this does NOT apply
OpenAPI files used only outside Power Platform.
