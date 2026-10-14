---
id: 2026-10-14-1703-paconn-validate-always-applies-certification-rules
title: paconn validate always applies certification rules, overstating private connector needs
applies_when: >
  running `paconn validate` on a custom connector definition that will be imported privately
  (not submitted to Microsoft for certification) and reading its errors as import blockers
rule: >
  When validating a private custom connector, don't treat `paconn validate` errors about missing
  descriptions, info.contact or collectionFormat 'Multi' as blockers; call validateApiSwagger with
  certification rules off (docs/guides/paconn-connector-testing.md) as well, because paconn
  hard-codes enableConnectorCertificationRules=true and reports certification-only failures.
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
    paconn 0.0.21 source: paconn/operations/validate.py calls validate_connector(...,
    enable_certification_rules=True), and paconn/apimanager/powerappsrp.py adds
    enableConnectorCertificationRules=true to the validateApiSwagger URL. On 14 Oct 2026 the Business
    Fitness definition failed `paconn validate` with 100 errors but passed with 0 errors when the same
    endpoint was called with the flag off (docs/connector-guide.md step 4; docs/guides/paconn-connector-testing.md)
  author:
related:
  - 2026-10-14-1703-power-platform-validator-reports-in-stages
  - 2026-10-14-1703-certification-off-validation-is-lenient
  - 2026-10-14-1552-openapi-spec-validator-misses-power-platform-rules
proposed_tags: []
---

When `paconn validate` is run on a definition for a private custom connector, it reports errors that only matter for Microsoft certification. It always applies the certification rule set, so its errors overstate what the connector actually needs.

## What happened
`paconn validate` on the generated Business Fitness definition failed with 100 errors and HTTP 400 (`SwaggerCertificationFailedWithErrors`):
- 90 "The 'description' property is required";
- 1 "The 'contact' property is required";
- 9 "The 'collectionFormat' keyword value 'Multi' is not supported".

That looked like the definition and the list-filter design were broken. Calling the same `validateApiSwagger` endpoint without the certification flag returned HTTP 200 with 0 errors and 0 warnings.

## Why it happened
paconn's `validate` operation passes `enable_certification_rules=True` unconditionally, and its help text says "Validate the swagger for certification". There's no option to turn it off. The endpoint itself accepts the flag either way.

## What to do instead
- Run both checks:
  - `paconn validate` for the certification view;
  - the certification-off call (script in `docs/guides/paconn-connector-testing.md`) for the private-connector view.
- Treat "description required", "contact required" and "'Multi' is not supported" as certification-only, unless the connector is going to Microsoft.
- A certification-off pass is lenient and is only stage one, so don't stop there. See the related lessons.

## When this does NOT apply
Connectors being submitted for certification, where every `paconn validate` error must be fixed.
