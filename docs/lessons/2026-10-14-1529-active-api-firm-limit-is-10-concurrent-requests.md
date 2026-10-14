---
id: 2026-10-14-1529-active-api-firm-limit-is-10-concurrent-requests
title: The Active API allows each firm only 10 concurrent requests across all its apps
applies_when: >
  building Power Automate flows that call the Business Fitness Active API in parallel,
  e.g. Apply to each with concurrency raised, parallel branches, or a trigger that starts
  many flow runs at once
rule: >
  When flows call the Active API, keep total parallelism at 10 or less (loop concurrency,
  parallel branches and simultaneous flow runs combined) and handle 429 with Retry-After,
  because Business Fitness limits each firm to 10 concurrent requests and 120 requests per
  60 seconds, shared by every app the firm uses.
lesson_type: pitfall
phase: operation
domain: [scaling, reliability]
tech: [power-automate]
scope: this-project
cost_if_ignored: rework
confidence: one-off
status: active
superseded_by:
expires:
provenance:
  projects: [business-fitness-connector]
  date: 2026-10-14
  source: handover-doc
  evidence: >
    Business Fitness Active API collection, "Documentation > Rate Limits" (API Limits as of
    21 June 2024); docs/connector-guide.md "Using the connector in flows"; Microsoft Learn
    "Limits of automated, scheduled, and instant flows" (Apply to each concurrency default 1)
  author:
related: []
proposed_tags: []
---

When Power Automate flows call the Business Fitness Active API in parallel, they share a firm-wide limit of 10 concurrent requests and 120 requests per minute. Exceeding either returns 429 for every app the firm uses, not just the flow.

## What happened
The Active API docs publish two levels of fixed-window and concurrency limits. Per app: 1,200 requests per 60 s and 100 concurrent. Per tenant (firm): 120 requests per 60 s and 10 concurrent. Power Platform allows up to 10,000 requests per minute per custom connector connection, so the connector itself won't hold anything back. The firm limit is the binding one.

## Why it happened
The limits are applied at the tenant level across all apps. A flow that raises "Apply to each" concurrency, or is triggered many times at once, can use up the firm's 10 concurrent slots on its own. Microsoft's limits page says Apply to each defaults to concurrency 1 and can go up to 50. Flow runs are unlimited when trigger concurrency control is off, which is the default.

## What to do instead
- Leave Apply to each sequential, or set its concurrency to 10 or less, and budget for other parallel branches and runs.
- Turn on trigger concurrency control for flows that can fire in bursts.
- Keep the default retry policy, or set an exponential one. The API returns `Retry-After` on 429.
- For bulk loads, ask Business Fitness about grace periods (e.g. a 2× weekend multiplier, set per app/tenant).

## How to recognise it early
429 responses, or the `X-RateLimit-Remaining-Tenant` response header nearing 0.

## When this does NOT apply
Limits "can change at any time". Recheck the Rate Limits page; these figures are as of 21 June 2024.
