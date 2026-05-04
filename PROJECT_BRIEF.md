# Project Brief

This repo powers [franciscorowe.com](https://franciscorowe.com) as a Quarto website with committed static output in `_site/`.

## What Matters Most

- Source pages are rendered from root `.qmd` files listed in [`_quarto.yml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/_quarto.yml).
- Netlify deploys the committed `_site/` output, not a fresh build.
- The Netlify build command in [`netlify.toml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/netlify.toml) runs [`scripts/netlify-preflight.sh`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/scripts/netlify-preflight.sh), which only checks that `_site/` exists and is complete enough to publish.
- If source content changes, `_site/` must usually be re-rendered and committed too.

## Core Structure

- Root pages:
  - `index.qmd`
  - `bio.qmd`
  - `projects.qmd`
  - `migration-sentiment-digital-technology-ai.qmd`
  - `human-mobility-and-hazards.qmd`
  - `papers.qmd`
  - `courses.qmd`
  - `blog.qmd`
  - `talks.qmd`
  - `resources.qmd`
- Blog content lives in `content/post/`
- Talks content lives in `content/talks/`
- Styles and shared assets live mainly in `assets/`
- Rendered static output is tracked in `_site/`

## Custom Systems

### Blog

[`blog.qmd`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/blog.qmd) is not a simple Quarto listing page. It contains custom R code that:

- scans `content/post/`
- builds the blog index page
- renders standalone post pages to `_site/post/<slug>/index.html`
- generates summaries and estimated reading time
- supports `subtitle:` in front matter
- injects a reusable `Suggested citation` block
- injects a BibTeX block
- supports optional `doi:` front matter
- shows a DOI badge when a DOI exists

Useful front matter fields for posts:

```yaml
---
title: "Post title"
subtitle: "Optional subtitle"
author: "Francisco Rowe"
date: "2026-04-09"
categories: ["reflections"]
archive: "zenodo"
doi: "10.5281/zenodo.xxxxxxx"
---
```

Important gotcha:

- Some older posts have both `.qmd` and `.html` files in `content/post/`
- The custom blog logic can end up preferring stale companion HTML
- If a post edit does not show up, check whether a same-name `.html` file is overriding the `.qmd`

### Talks

[`talks.qmd`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/talks.qmd) is also custom. It reads `content/talks/**/index.md` and renders:

- a talks card grid
- talk descriptions below
- optional links for slides, video, and related pages
- YouTube embeds when `url_video` is present

Per-talk media convention:

- each talk folder can include `featured.png`, `featured.jpg`, `featured.jpeg`, or `featured.webp`

Important gotcha:

- the repo uses Quarto freeze globally with `execute: freeze: auto`
- if talk updates do not appear, the stale cache is often `_freeze/talks/execute-results/html.json`
- deleting that file and re-running `quarto render` usually fixes missing talk updates

## DOI Work In Progress

There is already a scaffold for future post-level DOI automation with Zenodo:

- workflow: [`.github/workflows/zenodo-post-doi.yml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/.github/workflows/zenodo-post-doi.yml)
- helper script: [`scripts/zenodo_stage_post.py`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/scripts/zenodo_stage_post.py)

Current status:

- it does not mint DOIs yet
- it stages posts marked `archive: zenodo` that do not yet have a DOI
- it writes candidate metadata to `tmp/zenodo-post-candidates.json`

## Deployment Model

- Deployment happens by pushing to `main`
- Netlify publishes the committed `_site/`
- This means broken or partial local renders can be deployed if `_site/` is committed in a bad state

Practical implication:

- treat `_site/` as a deploy artifact that still needs review
- if a render fails midway, do not blindly stage the resulting `_site/` diff

## Known Failure Modes

- Dropbox-backed filesystem can sometimes interfere with render moves and leave a half-rendered `_site/`
- stale `_freeze` output can hide changes, especially on `talks.qmd`
- stale `.html` files in `content/post/` can shadow updated `.qmd` posts
- updating a source asset is not enough if the deployed version comes from `_site/`

## Normal Working Pattern

1. Edit source content.
2. Run `quarto render`.
3. Inspect the resulting `_site/` diff carefully.
4. Commit both the source changes and the corresponding `_site/` updates.
5. Push to `main` to trigger Netlify deployment.

Useful commands:

```bash
quarto render
quarto preview --no-browser --port 4200
git status --short
```

When talks look stale:

```bash
rm -f _freeze/talks/execute-results/html.json
quarto render
```

## Recent High-Value Content Added

Blog posts:

- `content/post/2026-03-31-debias-workshop-symposium.qmd`
- `content/post/2026-04-04-reliefweb-iran-digital-trace-report.qmd`
- `content/post/2026-04-05-when-good-work-doesnt-travel.qmd`
- `content/post/2026-04-07-worldpop-scale-sustainability.qmd`
- refreshed `content/post/2021-02-08-count_data_modelling.qmd`

Talks:

- updated `content/talks/2026_hnpw_panel/index.md`
- added `content/talks/2026_uy_social_sciences/index.md`

## Good Starter Files For A Fresh Chat

If opening a new chat for feature work, point it first at:

- [`_quarto.yml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/_quarto.yml)
- [`netlify.toml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/netlify.toml)
- [`blog.qmd`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/blog.qmd)
- [`talks.qmd`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/talks.qmd)
- [`.github/workflows/zenodo-post-doi.yml`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/.github/workflows/zenodo-post-doi.yml)
- [`scripts/zenodo_stage_post.py`](/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/scripts/zenodo_stage_post.py)

## Current Caution

At the time this brief was written, the working tree already had unrelated local changes under `_site/` from a render diff. Any new work should inspect `git status` first and avoid mixing unrelated render artifacts into future commits.
