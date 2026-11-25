#!/usr/bin/env python3
"""Package the EXHALE standalone build for this site.

Run with the path to a DataProduct-EXHALE checkout, then render with Quarto.
Source: https://github.com/Imago-SDRUK/DataProduct-EXHALE
"""

import argparse
import json
import re
from pathlib import Path


SOURCE = Path("code/static-indicators-census-year/5-INTERACTIVE_EXPLORER")
OUTPUT = Path(__file__).resolve().parents[1] / "atlas/exhale"
MAX_FILE_BYTES = 9_000_000
CHUNK_BYTES = 8_000_000


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def package(source_repo):
    preview = source_repo / SOURCE / "preview/static-census-year-exposure-explorer.html"
    html = preview.read_bytes()
    geometry = re.search(rb"<script>\nconst GEOJSON = ([^\n]+);\n", html)
    if geometry is None:
        raise ValueError("No embedded GEOJSON declaration in the EXHALE build")

    collection = json.loads(geometry[1])
    features = collection["features"]
    if collection["type"] != "FeatureCollection" or not features:
        raise ValueError("Expected a nonempty EXHALE boundary FeatureCollection")
    collection["features"] = []

    files = {"boundaries.js": b"const GEOJSON = " + encode(collection) + b";\n"}
    chunk = []
    chunk_size = 0
    for feature in features:
        encoded = encode(feature)
        size = len(encoded) + len(b",\n")
        if size > CHUNK_BYTES:
            raise ValueError("A single EXHALE boundary exceeds the chunk size")
        if chunk_size + size > CHUNK_BYTES:
            files[f"boundaries-{len(files)}.js"] = write_features(chunk)
            chunk = []
            chunk_size = 0
        chunk.append(encoded)
        chunk_size += size
    files[f"boundaries-{len(files)}.js"] = write_features(chunk)

    scripts = b"".join(f'<script src="{name}"></script>\n'.encode() for name in files)
    html = html[:geometry.start()] + scripts + b"<script>\n" + html[geometry.end():]

    catalogue = re.search(
        rb"<br><br>(Find this data product and related indicators in the [^\n]+HASP data catalogue</a>\.)</div>",
        html,
    )
    if catalogue is None:
        raise ValueError("Expected the data catalogue sentence at the end of the EXHALE help note")
    sources = (
        b"\n    <p>" + catalogue[1] + b" Sign in for free and explore the indicators. "
        b'The indicators combine modelled air pollution grids from the '
        b'<a href="https://compliance-data.defra.gov.uk/" title="https://compliance-data.defra.gov.uk/" '
        b'target="_blank" rel="noopener noreferrer">UK Department for Environment, Food &amp; Rural Affairs (DEFRA)</a> '
        b'with synthetic population data produced by the '
        b'<a href="https://data.hasp.ac.uk/" title="https://data.hasp.ac.uk/" target="_blank" '
        b'rel="noopener noreferrer">Healthy and Sustainable Places Data Service (HASP)</a>, '
        b'including demographic, socioeconomic, household and health attributes. '
        b'The inputs refer to 2021 for England, Wales and Northern Ireland, and 2022 for Scotland. '
        b'Official statistical boundaries and geographic lookups support the calculation of indicators '
        b'at lower and upper geography levels. Geographic boundary datasets are available from the '
        b'<a href="https://geoportal.statistics.gov.uk/" target="_blank" rel="noopener noreferrer">'
        b'Open Geography portal from the Office for National Statistics (ONS)</a>.</p>\n    </div>'
    )
    html = html[:catalogue.start()] + sources + html[catalogue.end():]

    attribution = b"  map.attributionControl.addAttribution("
    if html.count(attribution) != 1:
        raise ValueError("Expected a single map attribution in the EXHALE build")
    credit = (
        attribution
        + b"""'<a href="https://github.com/Imago-SDRUK/DataProduct-EXHALE">Imago EXHALE</a> (<a href="license.txt">licence</a>)');\n"""
    )
    files["index.html"] = html.replace(attribution, credit + attribution)
    files["license.txt"] = (source_repo / "LICENSE").read_bytes()

    for name, content in files.items():
        if len(content) > MAX_FILE_BYTES:
            raise ValueError(f"{name} exceeds this deployment's static file size limit")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUTPUT / name).write_bytes(content)
    for path in OUTPUT.glob("boundaries-*.js"):
        if path.name not in files:
            path.unlink()


def write_features(features):
    return b"GEOJSON.features.push(\n" + b",\n".join(features) + b"\n);\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_repo", type=Path)
    package(parser.parse_args().source_repo)
