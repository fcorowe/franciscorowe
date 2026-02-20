# Rebuild Specification: Francisco Rowe Website (Current Version)

## Project fingerprint
- Recreate behavior/content style of commit `5724a59` on branch `main`.
- This is a Quarto website (not the legacy Hugo/Wowchemy site still present in the repo).

## Source of truth files
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/_quarto.yml`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/assets/styles.scss`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/assets/menu.html`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/assets/menu.js`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/index.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/bio.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/projects.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/papers.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/courses.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/blog.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/talks.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/resources.qmd`
- `/Users/franciscorowe/Library/CloudStorage/Dropbox/Francisco/Research/github_projects/websites/franciscorowe/scripts/update_publications.py`

## Core stack
- Quarto website (`project.type: website`) output to `_site`.
- Quarto HTML format with `flatly` + custom SCSS.
- R code chunks inside QMD pages generate dynamic lists/cards.
- Optional Python script updates publication dataset from local `content/publication` + Scholar/OpenAlex fallback.
- Tested environment in repo: Quarto `1.6.39`, R `4.4.2`.

## Site IA and pages
- Navbar (pinned): Home, Bio, Projects, Papers, Courses, Blog, Talks, Resources.
- Pages rendered explicitly: `index.qmd`, `bio.qmd`, `projects.qmd`, `papers.qmd`, `courses.qmd`, `blog.qmd`, `talks.qmd`, `resources.qmd`.
- Footer: left `© 2026 Francisco Rowe`, right `Built with Quarto + R`.

## Visual design requirements
- Typography: Google Fonts `Open Sans` (body), `Oswald` (headings/nav title).
- Palette: light neutral background with yellow link highlight effect, subtle borders/shadows.
- Header/nav: translucent white, blurred, thin bottom border.
- Card-heavy layout for projects, courses, resources, talks, blog, papers.
- Responsive rules at mobile breakpoint (max-width 768px).
- Keep grayscale-to-color hover behavior on project images.
- Keep accessibility focus outlines and keyboard-visible states.

## Critical functional behaviors
- Home page:
  - Intro card with headshot + bio links + social icon row.
  - Featured YouTube video: fallback thumbnail link if not `http/https`, iframe embed otherwise.
  - Selected Projects cards.
- Papers page:
  - Reads `/data/papers_master.csv`.
  - Filters year range 2008–2026.
  - Renders ordered numbered paper cards with tabs: Journal page / DOI / PDF.
  - If CSV missing/empty, fail with explicit error.
- Blog page:
  - Discovers posts from `/content/post` (`*.Rmd`, `*.qmd`, recursive `index.md`).
  - Parses front matter, estimates read time, creates excerpts.
  - Publishes per-post HTML into `_site/post/<slug>/index.html`.
  - Uses `commonmark` for markdown-to-html fallback conversion.
- Talks page:
  - Reads recursive talk front matter from `/content/talks/**/index.md`.
  - Renders talks grid + detailed sections below.
  - Supports YouTube embedding with thumbnail fallback.
- Projects/Courses/Resources/Bio pages:
  - Static card/text pages using existing images and external links.

## Data contracts
- `papers_master.csv` columns must be:
  - `title,authors,journal,year,journal_link,doi,pdf_link,source`
- Publication source directory:
  - `/content/publication/<slug>/index.md` + optional `cite.bib`
- Talks source directory:
  - `/content/talks/<slug>/index.md` + optional `featured.(png|jpg|jpeg|webp)`
- Posts source directory:
  - `/content/post` with mixed `.Rmd`, `.qmd`, and folder `index.md` posts.

## Build/update workflow
- Publication update (optional but expected):
  - Run `/scripts/update_publications.py` to refresh `data/papers_master.csv`, `data/citations_by_year.csv`, `data/papers_update_meta.json`.
- Site build:
  - Run `quarto render`.
- Output folder:
  - `_site`.

## Important non-goals / avoid confusion
- Do not rebuild from legacy Hugo/Wowchemy config (`config.yaml`, `themes/`, `content/home/*`) for the current version.
- Keep `netlify.toml` as legacy unless explicitly migrating deploy pipeline; current active build logic is Quarto.

## Acceptance criteria
- All 8 top-level pages render and are linked in navbar.
- Custom styling matches current card-based light theme and typography.
- Papers list renders from CSV with working tab links and correct ordering/filtering.
- Blog index populates and generates individual `_site/post/.../index.html` pages.
- Talks grid and detail sections render; YouTube embeds/fallbacks work.
- Mobile layout remains readable and consistent with desktop behavior.
