---
id: 2026-10-14-1603-connector-has-one-host-so-other-hosts-are-misrouted
title: A connector has one host, so requests to other hosts get silently sent to the wrong one
applies_when: >
  generating a custom connector from a Postman collection whose requests use more than one host,
  or overriding the host with --host for a sandbox
rule: >
  When requests in a collection use several hosts, skip and report every request whose host differs
  from the collection's own API host (the first absolute URL's host, not --host), because a Swagger
  2.0 connector has a single host and those requests would otherwise be sent to the wrong server.
lesson_type: pitfall
phase: implementation
domain: [api, integration]
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
    postman2pp.py build_paths (host_guess check); tests/test_postman2pp.py
    RequestHandling.test_requests_on_another_host_are_skipped and
    test_host_override_does_not_skip_the_collections_requests. Before the fix, a synthetic request
    to https://other.example.org/b became the path /b on api.example.com with no warning.
  author:
related: [2026-10-14-1552-postman-environment-values-leak-into-connector-paths]
proposed_tags: []
---

When a Postman collection's requests use more than one host, a generated connector silently puts them all on one host, because Swagger 2.0 has a single `host`. A request meant for another server is then sent to the API host, to whatever path happens to match there.

## What happened
`postman2pp.py` took the host of the first absolute URL and used only the path of every later request. In the third review, a synthetic collection with `https://api.example.com/a` and `https://other.example.org/b` produced paths `/a` and `/b`, both on `api.example.com`, and exited 0. The Business Fitness collection uses one API host (some requests via an unresolved `{{base_url}}`), so its output wasn't affected. Collections that mix in an identity, storage or partner host would be.

## Why it happened
Postman requests each carry a full URL; a connector definition carries one `host` plus paths. Taking only the path throws away the information that the request belongs elsewhere.

## What to do instead
- Treat the first absolute URL's host as the collection's API host. Skip any request on another host with a `WARNING:` line, and add those as a separate connector if they're needed.
- Compare against the collection's host, **not** `--host`. `--host` is an override (e.g. a sandbox), and comparing against it would skip every request.
- Compare hosts case-insensitively.

## How to recognise it early
`grep -oE 'https?://[^/"]+' collection.json | sort | uniq -c` shows more than one API-looking host.

## When this does NOT apply
Collections where all requests share one host or one `{{base_url}}` variable.
