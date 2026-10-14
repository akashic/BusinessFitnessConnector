---
id: 2026-10-14-1703-power-platform-validator-reports-in-stages
title: Power Platform's connector validator reports in stages, hiding later rule failures
applies_when: >
  reading Power Platform's validateApiSwagger results (via `paconn validate` or a direct call) for a
  custom connector definition that fails on missing descriptions, contact or other required properties
rule: >
  When the validator reports first-stage failures (required properties such as description,
  x-ms-summary or info.contact), fill them in temporarily on a copy and validate again before
  concluding what else is wrong, because later rules such as DefaultResponseHasSchema only appear
  once the earlier stage passes.
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
    validateApiSwagger with certification rules, 14 Oct 2026. A copy of the Business Fitness definition
    with a planted schema on a 'default' response returned only 91 required-property errors and 9
    'Multi' errors. After filling descriptions/contact and removing 'multi', the same planted mistake was
    reported (DefaultResponseHasSchema), plus OperationHasManyResponsesWithSchema and 25
    PartialDuplicateOperationPath warnings instead of 9. Recorded in docs/connector-guide.md step 4
    and docs/guides/paconn-connector-testing.md
  author:
related:
  - 2026-10-14-1703-paconn-validate-always-applies-certification-rules
  - 2026-10-14-1703-certification-off-validation-is-lenient
proposed_tags: []
---

When Power Platform's connector validator rejects a definition, it reports only the failures of the first stage it gets stuck on. Rules checked in later stages stay silent until the earlier failures are fixed, so the first error list is not the full picture.

## What happened
To check what the validator actually catches, a copy of the Business Fitness definition had a schema planted on a `default` response, which Microsoft's rules list as the DefaultResponseHasSchema error. With certification rules on, the response listed:
- 91 "property is required" errors (descriptions, contact, and the planted parameter's `x-ms-summary`);
- 9 'Multi' errors.

The planted error wasn't among them. Filling in descriptions and contact and replacing `multi` on that copy made the next stage appear: the DefaultResponseHasSchema error, an OperationHasManyResponsesWithSchema warning, and 25 PartialDuplicateOperationPath warnings, where the first pass had shown 9. The connector guide had briefly been corrected to "9 warnings" from the first pass, which was wrong.

## Why it happened
The service's error text says "Please validate again after fixing following errors". It validates required structure first and stops there.

## What to do instead
- Probe past stage one on a throwaway copy: add placeholder `description`s, an `info.contact`, and `x-ms-summary` where flagged, and remove `collectionFormat: multi`. Then validate with certification rules on.
- Report counts only after the probe. The real Business Fitness definition probed this way had 0 errors and 25 warnings.
- Never ship the placeholder text; real descriptions belong in `connector-overrides.yaml`.

## How to recognise it early
The error list contains only "property is required" or format errors, and the message says "Please validate again after fixing following errors".
