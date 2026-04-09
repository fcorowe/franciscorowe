#!/usr/bin/env Rscript

required_quarto <- "1.8.26"

if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv", repos = "https://cloud.r-project.org")
}

renv::restore(prompt = FALSE)

quarto_bin <- Sys.which("quarto")
if (!nzchar(quarto_bin)) {
  stop("Quarto is not installed or not on PATH. Install Quarto ", required_quarto, " and retry.", call. = FALSE)
}

quarto_version <- system2(quarto_bin, "--version", stdout = TRUE, stderr = FALSE)
quarto_version <- trimws(quarto_version[1])

if (!identical(quarto_version, required_quarto)) {
  warning(
    "Expected Quarto ", required_quarto, " but found ", quarto_version,
    ". The site may still render, but committed _site assets are expected to come from Quarto ",
    required_quarto, ".",
    call. = FALSE
  )
}

message("Environment restore complete.")
