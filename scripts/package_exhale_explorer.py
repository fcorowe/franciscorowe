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
        b'Open Geography portal from the Office for National Statistics (ONS)</a>.</p>\n'
        b'      <a href="/exhale-privacy.html">Privacy notice</a>\n    </div>'
    )
    html = html[:catalogue.start()] + sources + html[catalogue.end():]

    water_key_end = b"Lakes and reservoirs</div>\n  </div>"
    if html.count(water_key_end) != 1:
        raise ValueError("Expected the water key at the end of the EXHALE sidebar")
    boundary_credits = """Lakes and reservoirs</div>
    <section class="help-note" style="margin-top: 16px" aria-labelledby="boundary-credits">
      <h2 id="boundary-credits" tabindex="-1">Boundary credits</h2>
      <p><strong>England and Wales.</strong> Source: Office for National Statistics licensed under the
        <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v.3.0</a>.
        Contains OS data © Crown copyright and database right 2024.
        <a href="https://www.ons.gov.uk/methodology/geography/licences/">ONS licensing requirements</a></p>
      <p><strong>Scotland.</strong> Copyright Scottish Government, contains Ordnance Survey data © Crown
        copyright and database right (2024). Ordnance Survey (OS Licence number AC0000849451).
        <a href="https://www.arcgis.com/home/item.html?id=033861da4bb4485d9cad527a841d0eb3">Scottish Government boundary source</a></p>
      <p><strong>Northern Ireland.</strong> Contains Ordnance Survey of Northern Ireland information licensed under the
        <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>.
        <a href="https://www.nisra.gov.uk/publications/super-data-zone-boundaries-gis-format">NISRA boundary source</a></p>
    </section>
  </div>"""
    html = html.replace(water_key_end, boundary_credits.encode("utf-8"))

    attribution = (
        b"  map.attributionControl.addAttribution('Boundaries: ONS, Scottish Government, NISRA; "
        b"contains OS and OSNI data, Crown copyright and database rights. Lakes: Natural Earth.');"
    )
    if html.count(attribution) != 1:
        raise ValueError("Expected a single boundary attribution in the EXHALE map")
    credit = (
        b"""  map.attributionControl.addAttribution('<a href="https://github.com/Imago-SDRUK/DataProduct-EXHALE">Imago EXHALE</a> (<a href="license.txt">licence</a>)');\n"""
        b"""  map.attributionControl.addAttribution('<a href="#boundary-credits">Boundary credits</a>. Lakes: Natural Earth.');"""
    )
    files["index.html"] = html.replace(attribution, credit)
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
