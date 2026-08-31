#!/usr/bin/env bash
set -euo pipefail

echo "Netlify preflight: deploying committed static output from _site/"

if [ ! -d "_site" ]; then
  echo "ERROR: _site/ directory is missing."
  echo "Run: quarto render"
  echo "Then commit the updated _site/ and push again."
  exit 1
fi

if [ ! -f "_site/index.html" ]; then
  echo "ERROR: _site/index.html is missing."
  echo "Run: quarto render"
  echo "Then commit the updated _site/ and push again."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required for the static-site security checks."
  exit 1
fi

python3 scripts/check_site_security.py

echo "Preflight check passed."
