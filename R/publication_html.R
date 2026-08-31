publication_scalar <- function(value) {
  if (length(value) == 0L || is.na(value[[1L]])) {
    return("")
  }
  trimws(enc2utf8(as.character(value[[1L]])))
}

publication_escape_text <- function(value) {
  text <- gsub("[[:cntrl:]]+", " ", publication_scalar(value), perl = TRUE)
  replacements <- list(
    c("&", "&amp;"),
    c("<", "&lt;"),
    c(">", "&gt;"),
    c('"', "&quot;"),
    c("'", "&rsquo;"),
    c("[", "&#91;"),
    c("]", "&#93;"),
    c("(", "&#40;"),
    c(")", "&#41;"),
    c("!", "&#33;"),
    c("*", "&#42;"),
    c("_", "&#95;"),
    c("`", "&#96;"),
    c("\\", "&#92;"),
    c("{", "&#123;"),
    c("}", "&#125;")
  )
  for (replacement in replacements) {
    text <- gsub(replacement[[1L]], replacement[[2L]], text, fixed = TRUE)
  }
  text
}

publication_https_url <- function(value) {
  url <- publication_scalar(value)
  if (!nzchar(url) || grepl("[[:space:]<>\"'\\\\]", url, perl = TRUE)) {
    return("")
  }
  if (!grepl(
    "^https://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::[0-9]{1,5})?(?:[/?#].*)?$",
    url,
    perl = TRUE,
    ignore.case = TRUE
  )) {
    return("")
  }
  url
}

publication_doi <- function(value) {
  doi <- publication_scalar(value)
  if (!grepl("^10[.][0-9]{4,9}/[-._;()/:A-Za-z0-9%+]+$", doi, perl = TRUE)) {
    return("")
  }
  doi
}

publication_platform <- function(link, doi, source) {
  url <- tolower(publication_scalar(link))
  doi <- tolower(publication_scalar(doi))
  source <- tolower(publication_scalar(source))
  if (grepl("arxiv[.]org", url) || grepl("^10[.]48550/arxiv[.]", doi)) return("arXiv")
  if (grepl("osf[.]io", url) || grepl("^10[.]312(19|35)/osf[.]io/", doi)) return("OSF Preprints")
  if (grepl("ssrn[.]com", url) || grepl("^10[.]2139/ssrn[.]", doi)) return("SSRN")
  if (grepl("medrxiv[.]org", url)) return("medRxiv")
  if (grepl("biorxiv[.]org", url)) return("bioRxiv")
  if (grepl("researchsquare[.]com", url)) return("Research Square")
  if (grepl("zenodo[.]org", url) || grepl("^10[.]5281/zenodo[.]", doi)) return("Zenodo")
  if (source == "scholar") return("Google Scholar")
  "Preprint/Working Paper"
}

publication_journal_html <- function(value) {
  journal <- publication_scalar(value)
  if (grepl("^'[*][^*]+[*]'$", journal, perl = TRUE)) {
    inner <- substr(journal, 3L, nchar(journal) - 2L)
    return(paste0("&lsquo;<em>", publication_escape_text(inner), "</em>&rsquo;"))
  }
  if (grepl("^[*][^*]+[*]$", journal, perl = TRUE)) {
    inner <- substr(journal, 2L, nchar(journal) - 1L)
    return(paste0("<em>", publication_escape_text(inner), "</em>"))
  }
  publication_escape_text(journal)
}

publication_tab <- function(label, url) {
  safe_url <- publication_https_url(url)
  safe_label <- publication_escape_text(label)
  if (!nzchar(safe_url)) {
    return(paste0('<span class="paper-tab is-disabled">', safe_label, "</span>"))
  }
  paste0('<a class="paper-tab" href="', publication_escape_text(safe_url), '">', safe_label, "</a>")
}

render_publication_card <- function(paper) {
  paper_no <- suppressWarnings(as.integer(paper$paper_no[[1L]]))
  if (is.na(paper_no) || paper_no < 1L) {
    stop("Publication card number must be a positive integer.")
  }

  journal_link <- publication_scalar(paper$journal_link)
  doi <- publication_doi(paper$doi)
  pdf_link <- publication_scalar(paper$pdf_link)
  journal <- publication_scalar(paper$journal)
  if (!nzchar(journal)) {
    journal <- publication_platform(journal_link, doi, paper$source)
  }

  journal_tab <- publication_tab("Journal page", journal_link)
  doi_tab <- publication_tab("DOI", if (nzchar(doi)) paste0("https://doi.org/", doi) else "")
  pdf_tab <- publication_tab("PDF", pdf_link)

  paste0(
    '<li class="paper-card" value="', paper_no, '">\n',
    "<strong>", publication_escape_text(paper$title), "</strong><br>\n",
    '<span class="meta">', publication_escape_text(paper$authors), " · ",
    publication_journal_html(journal), " · ", publication_escape_text(paper$year_label), "</span><br>\n",
    '<span class="paper-links">', journal_tab, doi_tab, pdf_tab, "</span>\n",
    "</li>"
  )
}
