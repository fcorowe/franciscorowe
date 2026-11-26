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
    files["index.html"] = add_accessible_views(html.replace(attribution, credit))
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


def replace_once(html, old, new):
    if html.count(old) != 1:
        raise ValueError(f"Unexpected EXHALE template near {old[:110]!r}")
    return html.replace(old, new, 1)


def add_accessible_views(html):
    # Keep the original filter IDs, map legend, and source notices in the published layout.
    original = re.search(
        rb'<div class="app-header">\n(?P<header>.*?)\n</div>\n'
        rb'<div class="app-body">\n  <div class="side-panel">\n(?P<filters>.*?)\n'
        rb'(?P<note>    <div class="help-note">.*?)\n\n'
        rb'(?P<legend>    <div id="legend">.*?Lakes and reservoirs</div>)\n'
        rb'(?P<credits>    <section .*?</section>)\n  </div>\n'
        rb'  <div class="map-panel"><div id="map"></div></div>\n</div>',
        html,
        re.DOTALL,
    )
    if original is None:
        raise ValueError("Expected the original EXHALE header, sidebar, legend and map")
    sections = {key: value.decode("utf-8") for key, value in original.groupdict().items()}
    layout = f"""<a class="skip-link" href="#neighbourhood-query">Skip to neighbourhood search</a>
<header class="app-header">
{sections["header"]}
</header>
<main class="app-body">
  <section class="side-panel" aria-labelledby="explorer-filters">
    <h2 id="explorer-filters" tabindex="-1">Map and table filters</h2>
    <p><a href="#neighbourhood-results">Find a neighbourhood</a></p>
{sections["filters"]}
{sections["legend"]}
  </section>
  <section class="map-panel" aria-label="Exposure map">
    <div id="map" role="group" aria-label="Air pollution exposure map"></div>
  </section>
  <section class="neighbourhood-results" aria-labelledby="neighbourhood-results">
    <h2 id="neighbourhood-results" tabindex="-1">Neighbourhood results</h2>
    <form id="neighbourhood-search" class="neighbourhood-form" role="search" aria-label="Find neighbourhoods">
      <label for="neighbourhood-query">Neighbourhood name or code</label>
      <div class="neighbourhood-controls">
        <input id="neighbourhood-query" type="text" enterkeyhint="search" autocomplete="off">
        <button type="submit">Search</button>
        <button type="button" id="neighbourhood-clear">Clear</button>
      </div>
    </form>
    <p id="neighbourhood-status" class="neighbourhood-status" role="status" aria-atomic="true"></p>
    <div id="neighbourhood-pages" class="neighbourhood-page-controls" role="group" aria-label="Neighbourhood result pages" hidden>
      <button type="button" id="neighbourhood-previous" aria-controls="neighbourhood-table">Previous page</button>
      <button type="button" id="neighbourhood-next" aria-controls="neighbourhood-table">Next page</button>
    </div>
    <table id="neighbourhood-table" class="neighbourhood-table" hidden>
      <caption>Selected exposure measures</caption>
      <thead><tr>
        <th scope="col">Neighbourhood</th>
        <th scope="col">Exposure</th>
        <th scope="col" id="neighbourhood-vulnerability" hidden>Age-based exposure</th>
      </tr></thead>
      <tbody></tbody>
    </table>
    <p><a href="#explorer-filters">Back to map and table filters</a></p>
  </section>
  <section class="explorer-notes" aria-labelledby="explorer-notes">
    <h2 id="explorer-notes">About the data</h2>
{sections["note"]}
{sections["credits"]}
  </section>
</main>""".encode("utf-8")
    html = html[:original.start()] + layout + html[original.end():]
    html = replace_once(html, b"</head>", b'<link rel="stylesheet" href="explorer-layout.css">\n</head>')
    html = replace_once(
        html, b"<script>\n(function () {\n  L.Icon.Default",
        b'<script src="neighbourhood-results.js"></script>\n<script>\n(function () {\n  L.Icon.Default',
    )

    # Native selects provide keyboard and screen-reader behaviour across browsers.
    dropdown_start = html.index(b"  function makeDropdown(sel) {")
    dropdown_end = html.index(b"  function populate(poll) {", dropdown_start)
    html = html[:dropdown_start] + html[dropdown_end:]
    html = replace_once(html, b"    document.getElementById('vulnerability-btn').disabled = unavailable;\n", b"")
    html = replace_once(html, b"    refreshAll();\n", b"")
    html = replace_once(
        html, b"'None (Color By Static Exposure Indicator)'", b"'None'",
    )
    html = replace_once(
        html, b"  dds = [makeDropdown(selPoll), makeDropdown(selInd), makeDropdown(selVul)];",
        b"  var updateResults = createNeighbourhoodResults(META, resultValues);",
    )
    html = replace_once(
        html, b"    return esc(v) + (suffix || '');",
        b"    return String(v) + (suffix || '');",
    )
    html = replace_once(
        html, b"  function infoHtml(i) {\n    var d = DATA[S.poll];",
        b"""  function resultValues(i) {
    var d = DATA[S.poll];
    return {
      indicator: fmt(d[S.ind][i], unitFor(S.poll, S.ind)),
      vulnerability: S.vul ? fmt(d[S.vul][i], '%') : null
    };
  }

  function infoHtml(i) {
    var values = resultValues(i);""",
    )
    html = replace_once(html, b" + fmt(d[S.ind][i], unitFor(S.poll, S.ind));", b" + esc(values.indicator);")
    html = replace_once(html, b" + fmt(d[S.vul][i], '%');", b" + esc(values.vulnerability);")
    html = replace_once(
        html, b"  var map = L.map('map', { preferCanvas: true, zoomSnap: 0.25, attributionControl: true });",
        b"""  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var map = L.map('map', { preferCanvas: true, zoomSnap: 0.25, attributionControl: true,
    scrollWheelZoom: false, zoomAnimation: !reduceMotion, fadeAnimation: !reduceMotion });
  var activePopup;""",
    )
    html = replace_once(
        html, b"        L.popup({ maxWidth: 500 }).setLatLng(e.latlng).setContent(infoHtml(i)).openOn(map);",
        b"""        var popup = L.popup({ maxWidth: 500 }).setLatLng(e.latlng).setContent(infoHtml(i)).openOn(map);
        activePopup = { popup: popup, index: i };""",
    )
    return replace_once(
        html, b"    renderLegend(lg);",
        b"""    renderLegend(lg);
    updateResults(S);
    if (activePopup && activePopup.popup.isOpen()) {
      activePopup.popup.setContent(infoHtml(activePopup.index));
    }""",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_repo", type=Path)
    package(parser.parse_args().source_repo)
