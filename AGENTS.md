# Repository guidance

- This is a Quarto website deployed by Netlify from committed `_site` output.
- Before pushing content changes, run `quarto render` and commit both the source edits and updated `_site/` files.
- Blog posts live in `content/post/YYYY-MM-DD-slug.qmd`; rendering updates the matching `_site/post/.../index.html`, `_site/blog.html`, and `_site/blog.xml`.
- Use `bash scripts/netlify-preflight.sh` to check that the committed `_site` output exists before deploy.
- For completed website updates, commit and push directly to `main` unless the user explicitly requests a branch or pull request.
