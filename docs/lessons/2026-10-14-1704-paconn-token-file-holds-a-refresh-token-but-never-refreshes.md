---
id: 2026-10-14-1704-paconn-token-file-holds-a-refresh-token-but-never-refreshes
title: paconn stores a refresh token on disk but never uses it; sessions end after about an hour
applies_when: >
  using paconn for more than a single short session, scripting paconn commands, or deciding how to
  handle the ~/.paconn token file on a shared or managed machine
rule: >
  When working with paconn, expect to run `paconn login` again roughly hourly and run `paconn logout`
  when finished, because paconn treats its access token as expired 10 minutes before its ~1-hour
  lifetime and never refreshes it, yet leaves a refresh token in ~/.paconn/accessTokens.json.
lesson_type: pitfall
phase: testing
domain: [tooling, security]
tech: [paconn]
scope: this-stack
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
    paconn 0.0.21 source: authentication/tokenmanager.py (TOKEN_FILE accessTokens.json in ~/.paconn,
    written with mode 0o600; TOKEN_BUFFER_SECONDS = 600; is_expired() only compares expires_on);
    authentication/auth.py re-runs the device-code flow when expired, and other commands raise "Access
    token invalid. Please login again." The token file written on 14 Oct 2026 contained access_token,
    refresh_token and expires_in 3913. Documented in docs/guides/paconn-connector-testing.md
  author:
related: [2026-10-14-1703-paconn-login-code-hidden-in-non-interactive-shells]
proposed_tags: []
---

When paconn is used for longer than about an hour, its commands start failing with "Access token invalid. Please login again." It never uses the refresh token it saved, but that refresh token stays on disk until you log out.

## What happened
After `paconn login`, `~/.paconn/accessTokens.json` held an `access_token` with `expires_in` 3913 seconds, plus a `refresh_token`. paconn's `is_expired()` treats the token as expired 600 seconds before `expires_on`, so a session lasts about 55 minutes. After that, `validate`, `create`, `update` and `download` fail with "Access token invalid. Please login again." (the same error you get before ever logging in), and only `paconn login` fixes it.

## Why it happened
paconn 0.0.21 is built on the retired `adal` library. Its token manager checks expiry but has no refresh path. It stores whatever the sign-in service returned, including the refresh token, in a file readable only by your user account (mode 0600).

## What to do instead
- Re-run `paconn login` when you see "Access token invalid". On a non-interactive shell, use `PYTHONUNBUFFERED=1` (see the related lesson).
- Run `paconn logout` when finished; it deletes the token file. Treat that file as a credential: never copy it, commit it or include it in support bundles.
- Scripts that call the validation endpoint with paconn's token (`docs/guides/paconn-connector-testing.md`) inherit the same roughly one-hour limit.

## When this does NOT apply
`pac` (the Power Platform CLI) manages its own auth profiles and refreshes them. This applies to paconn only.
