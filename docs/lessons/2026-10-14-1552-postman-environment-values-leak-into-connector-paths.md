---
id: 2026-10-14-1552-postman-environment-values-leak-into-connector-paths
title: Resolving whole request URLs against a Postman environment bakes test values into paths
applies_when: >
  converting a Postman collection to a connector definition with a Postman environment file, where
  request paths contain {{variables}} such as {{clientId}} that the environment gives test values
rule: >
  When converting Postman requests, fill only the URL's leading {{base_url}}-style variable from
  the environment and turn every other {{var}} into a path parameter, because resolving the whole
  URL hard-wires each action to the tester's record and copies that ID into a shareable definition.
lesson_type: pitfall
phase: implementation
domain: [api, security]
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
  source: pr-review
  evidence: >
    postman2pp.py resolve(..., leading_only=True) in build_paths; tests/test_postman2pp.py
    EndToEnd.test_collection asserts '/core/v1/clients/{clientId}/notes' and that
    'test-client-guid-from-postman' is absent. Before the fix (commit 1c292fa) a synthetic request
    '.../clients/{{clientId}}' produced the path '/clients/8f3c-real-client-guid'
  author:
related: []
proposed_tags: []
---

When a Postman collection is converted with its environment file, filling every `{{variable}}` in a request URL from the environment turns path variables like `{{clientId}}` into whatever test value the environment holds. The action is then hard-wired to one record, and that record's ID ends up in the connector definition.

## What happened
`postman2pp.py` resolved the whole raw URL against the collection and environment variables before converting path variables to `{param}`. In review, a request to `https://api.example.com/clients/{{clientId}}` with an environment value `8f3c-real-client-guid` produced the operation path `/clients/8f3c-real-client-guid`, with no parameter. The Business Fitness collection uses `:id`-style path variables, so its output wasn't affected. A forked collection that uses `{{...}}` in paths, with a well-used test environment, would have been.

## Why it happened
Postman environments serve two purposes: configuration (`base_url`, `auth_url`) and test data (IDs of records being poked at). Resolving everything treats test data as configuration.

## What to do instead
- Resolve only a leading `{{var}}` (the host or base URL). Leave the rest, so `{{clientId}}` becomes the path parameter `{clientId}`.
- Keep `*.postman_environment.json` out of git; it's in this repo's `.gitignore`.
- Add a test with a recognisable environment value and assert it never appears in the output.

## How to recognise it early
An operation path containing a GUID, number or name instead of `{param}`, or fewer path parameters than the collection's request shows.

## When this does NOT apply
Auth settings (`authUrl`, `accessTokenUrl`, `scope`) should be resolved from the environment. They are configuration, and the generator stops if any are left undefined.
