---
id: 2026-10-14-1703-certification-off-validation-is-lenient
title: Validation with certification rules off passed definitions that break documented rules
applies_when: >
  using Power Platform's validateApiSwagger with certification rules off (a private custom connector
  check) as evidence that a connector definition follows Microsoft's swagger rules
rule: >
  When a definition passes validation with certification rules off, treat that only as "the service
  accepts it", not as rule compliance, and also run the certification check probed past stage one,
  because in testing the certification-off check passed a schema on 'default' and form data on a GET.
lesson_type: pitfall
phase: testing
domain: [tooling, integration]
tech: [power-platform-custom-connectors, paconn]
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
    validateApiSwagger without enableConnectorCertificationRules, 14 Oct 2026: a copy of the Business
    Fitness definition with a planted schema on GET /core/v1/offices 'default' and a formData parameter
    on GET /core/v1/users/profile returned HTTP 200, 0 errors, 0 warnings. The certification check
    later reported the 'default' schema error but never flagged the GET form data. Recorded in
    docs/guides/paconn-connector-testing.md
  author:
related:
  - 2026-10-14-1703-paconn-validate-always-applies-certification-rules
  - 2026-10-14-1703-power-platform-validator-reports-in-stages
  - 2026-10-14-1552-openapi-spec-validator-misses-power-platform-rules
proposed_tags: []
---

When a custom connector definition passes Power Platform's validation with certification rules off, that doesn't show it follows Microsoft's published swagger rules. The certification-off check accepted planted violations of two of them.

## What happened
To see how much the private-connector check enforces, two mistakes from Microsoft's "Fix Swagger Validator errors" page were planted in a copy of the Business Fitness definition:
- a schema on a `default` response (DefaultResponseHasSchema);
- a form-data parameter on a `GET` (BodyOrFormDataParameterInFetchOperationNotAllowed).

With certification rules off, the validator returned HTTP 200 with 0 errors and 0 warnings. With certification rules on, probed past stage one, it reported the `default` schema as an error. It never flagged the form data on the `GET` at any stage tested.

## Why it happened
Not documented. The certification-off mode appears to check little beyond basic structure. Some rules on Microsoft's list weren't enforced by this endpoint in either mode, at least for this case. Whether importing in the maker portal or using the connector at runtime enforces more is untested.

## What to do instead
- Keep the generator's own checks for Microsoft's rules (single response schema, no body on GET/HEAD, `connectionId` and so on), and its tests. Don't rely on the service to catch them.
- Use certification-off as an "is it accepted" check, and certification-on (probed past stage one) as the rule check.
- Still deploy to a test environment and run the actions. Neither check exercises runtime behaviour, such as how list filters are sent.

## When this does NOT apply
Connectors validated only for certification, where the certification mode is the one that matters.
