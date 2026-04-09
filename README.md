# Francisco Rowe Website

[![Netlify Status](https://api.netlify.com/api/v1/badges/2c50b051-db82-498b-b6d5-59b9c6d346cd/deploy-status)](https://app.netlify.com/sites/ecstatic-hoover-1143a1/deploys)

Source code for [franciscorowe.com](https://franciscorowe.com), built with Quarto and deployed on Netlify.

This repository update and migration were completed collaboratively by Francisco Rowe and Codex.

## Stack

- Quarto website project (`_quarto.yml`)
- R-powered page generation for selected sections (`blog.qmd`, `papers.qmd`, `talks.qmd`)
- Netlify deployment from committed static output in `_site`

## Key Files

- `_quarto.yml`: Quarto project config, page list, and output dir (`_site`)
- `netlify.toml`: Netlify publish settings and preflight command
- `scripts/netlify-preflight.sh`: build-time check that `_site` exists
- `assets/styles.scss`: Site styling overrides
- `data/papers_master.csv`: publication source data

## Local Development

Render the full site:

```bash
quarto render
```

Render without executing code chunks:

```bash
quarto render --no-execute
```

Preview the built homepage:

```bash
open _site/index.html
```

Set up a fresh clone with the expected R dependencies:

```bash
Rscript scripts/setup_site.R
```

This project currently expects:

- Quarto `1.8.26`
- R `4.5.x`
- R packages restored from `renv.lock`

Recommended fresh-clone workflow:

```bash
git clone git@github.com:fcorowe/franciscorowe.git
cd franciscorowe
Rscript scripts/setup_site.R
quarto render
```

Notes on reproducibility:

- `renv.lock` pins the R package set used to render the site.
- `.renvignore` excludes generated and legacy content from dependency scanning.
- The repo no longer sources a user-specific `~/.Rprofile`, which previously made local behaviour machine-dependent.
- Quarto itself is not managed by `renv`, so install the expected Quarto version separately.

## Deployment

- Deploys are triggered by pushes to `main`.
- Netlify publishes from `_site` (pre-rendered locally).
- Netlify runs `bash scripts/netlify-preflight.sh` and does not render Quarto in the cloud.
- Before pushing content changes, run `quarto render` and commit both source files and updated `_site/`.
- GitHub Pages is intentionally disabled for this repository.

## Notes

- `_freeze/` is generated and ignored by Git.
- `_site/` is committed on purpose for reliable static deploys.
- If deployment fails, check the latest Netlify deploy logs first.
