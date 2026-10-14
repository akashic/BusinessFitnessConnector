---
id: 2026-10-14-1552-postman-request-names-break-connector-summary-rules
title: Postman request names used as action summaries break Microsoft's summary rules
applies_when: >
  using Postman request names as operation summaries (action names) in a generated Power Platform
  custom connector
rule: >
  When turning Postman request names into connector summaries, replace '/' with ' or ', rewrite a
  trailing "(x)" as " - x", cap at 80 characters and strip trailing punctuation, because
  Microsoft's string guidance says a summary shouldn't contain '/', exceed 80 characters or end
  with a non-alphanumeric character, and simply stripping punctuation breaks names like "List
  documents (minimal)".
lesson_type: pitfall
phase: implementation
domain: [api, integration]
tech: [power-platform-custom-connectors, postman]
scope: this-stack
cost_if_ignored: minor
confidence: one-off
status: active
superseded_by:
expires:
provenance:
  projects: [business-fitness-connector]
  date: 2026-10-14
  source: pr-review
  evidence: >
    Microsoft Learn "Learn best practices for string fields"
    (https://learn.microsoft.com/connectors/custom-connectors/connector-string-guidance);
    Business Fitness collection: 125 of 133 generated summaries ended in '.', and two end in ')';
    postman2pp.py summary_text(); tests/test_postman2pp.py
    Labels.test_summaries_follow_microsoft_string_guidance
  author:
related: []
proposed_tags: []
---

When Postman request names become connector action summaries, they usually read like sentences, ending in a full stop or a bracketed note. Microsoft's string guidance says a summary shouldn't do either.

## What happened
Business Fitness names its requests like "Create a Client Entity." and "List documents (minimal)". Used as summaries, 125 of 133 actions ended in a full stop. Microsoft's guidance says a summary "shouldn't end with a non-alphanumeric character, including punctuation or space", shouldn't contain '/', and shouldn't exceed 80 characters. Its validator also has "OperationSummaryTooLong" and "RestrictedCharactersInSummary" rules. The obvious fix, stripping trailing non-alphanumerics, would have turned "List documents (minimal)" into "List documents (minimal".

## Why it happened
Postman names are free text written for documentation readers. Connector summaries are UI labels with their own rules.

## What to do instead
- `summary_text()`: `/` → ` or `, a trailing `(x)` → ` - x`, truncate to 80 characters at a word boundary, then strip trailing non-alphanumerics.
- Don't force sentence case. Words like "Client Entity" are Business Fitness's product terms.
- Compare descriptions against the cleaned summary, so a description that only repeats the name is dropped (summary and description shouldn't be the same).

## When this does NOT apply
`operationId` follows different rules (PascalCase identifier). Parameter labels use `x-ms-summary` in Title Case, handled by `label()`.
