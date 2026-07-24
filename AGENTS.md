# Repository guidance

- This is a Quarto website deployed by Netlify from committed `_site` output.
- For fresh clones or environment repair, run `Rscript scripts/setup_site.R`; it restores `renv` packages and checks for Quarto 1.8.26.
- Before pushing content changes, run `quarto render` and commit both the source edits and updated `_site/` files.
- For local preview, use `quarto preview --no-browser --port 4200` or inspect rendered files under `_site/`.
- Blog posts live in `content/post/YYYY-MM-DD-slug.qmd`; rendering updates the matching `_site/post/.../index.html`, `_site/blog.html`, and `_site/blog.xml`.
- Use `bash scripts/netlify-preflight.sh` to check that the committed `_site` output exists before deploy.
- Publication maintenance uses `python scripts/update_publications.py --dry-run`, `python scripts/test_publication_workflow.py`, and `python scripts/verify_publications_page.py` after rendering.
- `python scripts/zenodo_stage_post.py` only stages candidate metadata for posts with `archive: zenodo` and no DOI; it does not mint DOIs.
- For completed website updates, commit and push directly to `main` unless the user explicitly requests a branch or pull request.
