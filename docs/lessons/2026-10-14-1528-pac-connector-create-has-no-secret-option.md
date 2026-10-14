---
id: 2026-10-14-1528-pac-connector-create-has-no-secret-option
title: pac connector create has no client-secret option, unlike paconn
applies_when: >
  deploying an OAuth 2.0 custom connector from apiDefinition.swagger.json and
  apiProperties.json with the Power Platform CLI (pac)
rule: >
  When deploying an OAuth custom connector with `pac connector create`, leave out --secret
  and enter the client secret on the connector's Security tab afterwards (or use the older
  `paconn create --secret`), because pac connector create has no secret parameter.
lesson_type: pitfall
phase: deployment
domain: [tooling]
tech: [power-platform-custom-connectors]
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
    commit e0b9db3 (docs/connector-guide.md step 5); Microsoft Learn "pac connector"
    reference (https://learn.microsoft.com/power-platform/developer/cli/reference/connector)
    and "Create a custom connector with the CLI" (paconn)
  author:
related: []
proposed_tags: [pac-cli]
---

When an OAuth 2.0 custom connector is deployed with `pac connector create`, there is no option for passing the client secret. The `--secret` flag belongs to the older `paconn` CLI.

## What happened
The README's deploy step was `pac connector create --api-definition-file ... --api-properties-file ... --secret "<client secret>" --environment <env-id>`, which mixes the two CLIs. This was found by checking the command against the Microsoft Learn reference, not by running it, so the exact error pac gives is unverified.

## Why it happened
`paconn create` takes `--api-prop`, `--api-def`, `--icon` and `--secret`. `pac connector create` takes `--api-definition-file`, `--api-properties-file`, `--environment`, `--icon-file`, `--script-file`, `--settings-file` and `--solution-unique-name`, with no secret. Instructions written from memory blend the two.

## What to do instead
- `pac connector create --api-definition-file connector/apiDefinition.swagger.json --api-properties-file connector/apiProperties.json --environment <env-id>`, then open the connector, go to Security and enter the client secret.
- Or use `paconn create ... --secret <secret>` if paconn is installed.
- Keep the secret out of `apiProperties.json` and out of the repo.

## When this does NOT apply
Connectors without OAuth (API key, basic, none) need no secret at deploy time.
