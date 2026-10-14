---
id: 2026-10-14-1528-custom-connector-oauth-needs-per-connector-redirect
title: OAuth custom connectors need the per-connector redirect, not the global consent URL
applies_when: >
  generating or editing apiProperties.json for a Power Platform custom connector that uses
  OAuth 2.0, or telling an API vendor which redirect URI to register for it
rule: >
  When a custom connector uses OAuth 2.0, set "redirectMode": "GlobalPerConnector" (with no
  redirectUrl) and register the Redirect URL shown on the connector's Security tab after
  creation, because the shared https://global.consent.azure-apim.net/redirect stopped working
  for new connections once Microsoft enforced per-connector redirect URIs.
lesson_type: pitfall
phase: deployment
domain: [identity, integration]
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
    commit e0b9db3 (postman2pp.py build_security; docs/connector-guide.md step 4);
    Microsoft Learn "Custom connectors overview", section 2.1 OAuth 2.0
    (https://learn.microsoft.com/connectors/custom-connectors/)
  author:
related: []
proposed_tags: []
---

When a Power Platform custom connector uses OAuth 2.0, an `apiProperties.json` set to `"redirectMode": "Global"` uses the shared global consent URL. Microsoft says that URL no longer works for new connections.

## What happened
`postman2pp.py` follows the BGL connector's conventions. It emitted `"redirectMode": "Global"` with `redirectUrl: https://global.consent.azure-apim.net/redirect`, and the README told users to register that URL with Business Fitness. This was caught by checking the generated file against Microsoft Learn during review, before any deployment. Business Fitness also only accepts redirect URIs that are HTTPS and "either under your own control or a Microsoft first-party endpoint tied to your tenant".

## Why it happened
Microsoft moved OAuth custom connectors to a per-connector redirect URI. Per the overview page, connectors created before February 2024 with the global URI "were updated or stopped working for new connections". Templates copied from older connectors still carry `Global`.

## What to do instead
- Use `"redirectMode": "GlobalPerConnector"` and drop `redirectUrl`. The certification example in Microsoft Learn does the same.
- Create the connector first, then copy the Redirect URL from its Security tab. It takes the form `https://global.consent.azure-apim.net/redirect/<connector-id>`. Register that exact URL with the identity provider.
- Check any other connector generated from the BGL conventions for the same setting. The BGL repo isn't here, so this hasn't been verified.

## How to recognise it early
`grep redirectMode apiProperties.json` returns `"Global"`, or the identity provider reports a redirect URI mismatch when a connection is created.

## When this does NOT apply
API-key, basic-auth or no-auth connectors.
