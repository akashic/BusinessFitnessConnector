---
id: 2026-10-14-1529-review-generator-against-real-collection
title: Run the connector generator on the real collection before reviewing it
applies_when: >
  reviewing or changing postman2pp.py, or any spec generator, when the vendor's real input
  collection can be obtained
rule: >
  When reviewing a connector generator, run it on the real vendor collection and validate the
  output before reporting findings, because reading the code alone missed the defects that
  blocked deployment and produced claims that turned out wrong.
lesson_type: heuristic
phase: testing
domain: [process]
tech: [power-platform-custom-connectors]
scope: this-org
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
    commit e0b9db3, whose message and tests (tests/test_postman2pp.py) cover each defect
    found only on the real collection. The pre-fix postman2pp.py was never committed (it was
    untracked before e0b9db3), so the original failing run isn't reproducible from git.
  author:
related:
  - 2026-10-14-1529-postman-repeated-query-keys-break-swagger
  - 2026-10-14-1529-postman-documenter-placeholders-infer-as-strings
proposed_tags: []
---

When reviewing a connector generator like `postman2pp.py`, running it on the real vendor collection finds the deployment-blocking defects that reading the code misses, and it corrects review claims made from the code alone.

## What happened
A code-only read of `postman2pp.py` turned up style and robustness issues. Running it on the downloaded Business Fitness collection then showed the real blockers:
- the definition failed Swagger validation (repeated query keys);
- 135 requests produced 134 operations, because a duplicate method + path was silently overwritten;
- `{{auth_url}}` and `{{scopes}}` were written into the OAuth settings;
- a runtime blob-upload URL became a fake path.

A later pass on the same collection also found every typed placeholder (`"<boolean>"`) inferred as a string.

The real data also corrected two code-only claims. "clientID becomes Client i d" was true of the code, but 0 of 294 labels in the real output had that problem. The spec's size had been blamed on per-error schemas, but success-response schemas (303 KB) far outweighed error schemas (69 KB).

## Why it happened
The generator's behaviour depends on the input's shape: how URLs, auth and examples are written. A reviewer reading the code imagines inputs, and imagined inputs miss the vendor's actual quirks.

## What to do instead
- Fetch the real collection first (see the Documenter download lesson), run the generator, and check the summary line, `WARNING:` lines and validator result before writing findings.
- Measure claims about size or frequency against the output (count operations, labels and bytes) instead of reasoning from the code.
- Turn each real-input defect into a small synthetic test (`tests/test_postman2pp.py`) so it doesn't need the vendor file.

## When this does NOT apply
When no real input is available. In that case, say the findings are unverified against real data.
