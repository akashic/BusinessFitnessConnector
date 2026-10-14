---
id: 2026-10-14-1528-postman-documenter-collection-json-is-downloadable
title: Postman Documenter API docs look unreadable, but the collection JSON is downloadable
applies_when: >
  a vendor API is documented only on a Postman Documenter site (such as
  development.businessfitness.com) and you need its endpoints, auth settings or examples
  without forking the collection in Postman
rule: >
  When a vendor's API docs are a Postman Documenter site, read the ownerId and publishedId
  meta tags from the page HTML and fetch <site>/api/collections/<ownerId>/<publishedId>,
  because the page renders in the browser and looks empty to curl and web fetchers.
lesson_type: pitfall
phase: scoping
domain: [api, tooling]
tech: [postman]
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
    commit e0b9db3; docs/connector-guide.md "Findings" (23 Sep claim that the endpoint list
    could not be read, corrected 14 Oct); Business Fitness page meta tags ownerId 31711831,
    publishedId 2s9Yynm4V5
  author:
related: []
proposed_tags: []
---

When a vendor API is documented only on a Postman Documenter site, the page renders in the browser and looks empty to curl and web fetchers, which makes it seem the endpoints can't be read automatically. In fact, the full collection JSON is served from the same host.

## What happened
On 23 Sep the README recorded that the Business Fitness endpoint list "could not be read automatically", so the build plan relied on forking the collection in Postman and exporting it by hand. On 14 Oct, the page HTML contained `ownerId` 31711831 and `publishedId` 2s9Yynm4V5. `GET https://development.businessfitness.com/api/collections/31711831/2s9Yynm4V5?segregateAuth=true&versionTag=latest` returned the whole 1.26 MB collection. It held 135 requests plus the auth, rate-limit, pagination and error documentation.

## Why it happened
A Documenter page is a script shell (`<div id="root"/>`) that loads the collection JSON from its own `/api/collections/...` path. WebFetch on the page returned only the title. A guessed `documenter.gw.postman.com` URL returned 400.

## What to do instead
- `curl -s <site> | grep -oE 'collections/[0-9]+/[A-Za-z0-9]+'`, then fetch that path on the same host with `?segregateAuth=true&versionTag=latest`.
- `postman2pp.py` reads this JSON directly. Its format differs from a v2.1 export: OAuth settings are nested in `basicConfig`/`advancedConfig`, the URL is a raw string plus `urlObject`, and descriptions are HTML.
- The environment the page links to (`/api/environments/<id>`) returned 404. Expect to fork the environment template in Postman for `auth_url`, `access_token_url` and `scopes`.

## When this does NOT apply
Private collections, or Documenter sites behind a sign-in.
