source("R/publication_html.R")

assert_true <- function(condition, message) {
  if (!isTRUE(condition)) stop(message, call. = FALSE)
}

malicious <- data.frame(
  paper_no = 1,
  title = '<img id="xss-proof" src="x" onerror="alert(1)"> [click](javascript:alert(2))',
  authors = '<svg onload="alert(3)"></svg>',
  journal = '*<script>alert(4)</script>*',
  year_label = '2026</span><img src=x onerror=alert(5)>',
  journal_link = 'javascript:alert(6)',
  doi = '10.1234/x" onmouseover="alert(7)',
  pdf_link = 'http://example.org/malware.pdf',
  source = 'openalex_recent',
  stringsAsFactors = FALSE
)
rendered <- render_publication_card(malicious)

assert_true(!grepl('<(?:img|svg|script)\\b', rendered, perl = TRUE, ignore.case = TRUE), "Markup payload became an element")
assert_true(!grepl('href="(?:javascript:|data:|http://)', rendered, perl = TRUE, ignore.case = TRUE), "Unsafe URL became active")
assert_true(!grepl('\\son(?:error|load|mouseover)="', rendered, perl = TRUE, ignore.case = TRUE), "Quoted event-handler attribute became active")
assert_true(grepl('&#91;click&#93;&#40;javascript:alert&#40;2&#41;&#41;', rendered, fixed = TRUE), "Markdown payload was not made inert")
assert_true(lengths(regmatches(rendered, gregexpr('paper-tab is-disabled', rendered, fixed = TRUE))) == 3L, "Unsafe tabs should be disabled")

legitimate <- data.frame(
  paper_no = 199,
  title = "Mobility & migration (revisited)",
  authors = "Rowe, Francisco & Collaborator",
  journal = "'*Journal of Mobility*'",
  year_label = "2026",
  journal_link = "https://example.org/article?x=1&y=2",
  doi = "10.1234/example.1",
  pdf_link = "https://example.org/article.pdf",
  source = "local",
  stringsAsFactors = FALSE
)
rendered_legitimate <- render_publication_card(legitimate)

assert_true(grepl('value="199"', rendered_legitimate, fixed = TRUE), "Card numbering changed")
assert_true(grepl('Mobility &amp; migration &#40;revisited&#41;', rendered_legitimate, fixed = TRUE), "Visible title was not encoded safely")
assert_true(grepl('&lsquo;<em>Journal of Mobility</em>&rsquo;', rendered_legitimate, fixed = TRUE), "Allowlisted journal emphasis changed")
assert_true(grepl('href="https://example.org/article?x=1&amp;y=2"', rendered_legitimate, fixed = TRUE), "HTTPS query link changed")
assert_true(grepl('href="https://doi.org/10.1234/example.1"', rendered_legitimate, fixed = TRUE), "Valid DOI link changed")

cat("Publication renderer security tests passed\n")
