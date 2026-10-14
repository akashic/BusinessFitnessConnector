---
id: 2026-10-14-1703-paconn-login-code-hidden-in-non-interactive-shells
title: paconn login's device code is hidden until it expires when output isn't a terminal
applies_when: >
  running `paconn login` from a non-interactive shell (an agent's shell tool, a `!` command in Claude
  Code, a pipe, a CI job or a backgrounded process) where stdout is not a TTY
rule: >
  When running `paconn login` outside a real terminal, set PYTHONUNBUFFERED=1 (or run it in a terminal
  window) and read the device code from the output as soon as it appears, because Python block-buffers
  the "enter the code" line and it only shows up after the code has expired.
lesson_type: pitfall
phase: testing
domain: [tooling, identity]
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
    paconn 0.0.21 (adal device-code flow), 14 Oct 2026: `paconn login` run as a Claude Code `!` command
    printed nothing for 120 s, then failed with "adal.adal_error.AdalError: Unexpected polling state
    code_expired", with the "To sign in, use a web browser to open the page
    https://login.microsoft.com/device and enter the code ..." line appearing only after the traceback.
    Rerun with PYTHONUNBUFFERED=1 showed the code immediately and "Login successful." followed.
    Documented in docs/guides/paconn-connector-testing.md
  author:
related: [2026-10-14-1703-paconn-validate-always-applies-certification-rules]
proposed_tags: []
---

When `paconn login` runs somewhere its output isn't a terminal, the device-code prompt is held in Python's output buffer. It only appears once the process exits, which is after the code has already expired, so the sign-in can't be completed.

## What happened
`paconn login` was run as a `!` command in Claude Code. Nothing appeared for 120 seconds, the command was moved to the background, and it then failed with `AdalError: Unexpected polling state code_expired`. Only then did the "open https://login.microsoft.com/device and enter the code …" line appear, below the traceback. Running it again in the background with `PYTHONUNBUFFERED=1` showed the code within seconds. The user signed in and paconn printed "Login successful."

## Why it happened
Python block-buffers stdout when it isn't a TTY. paconn prints the prompt with a normal print, then blocks while it polls for sign-in, so the buffered prompt is only flushed at exit.

## What to do instead
- Run `PYTHONUNBUFFERED=1 paconn login` whenever the shell isn't an interactive terminal. Watch the output, or a file it's redirected to, for the code.
- For an agent: start the login in the background with `PYTHONUNBUFFERED=1`, read the code from its output file, and give it to the user straight away. The code is only valid for a limited time set by the sign-in service.
- Simplest of all: run `paconn login` yourself in a normal terminal window.

## How to recognise it early
`paconn login` that prints nothing for more than a few seconds is almost certainly waiting on a code you can't see.
