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

echo "Preflight check passed."
