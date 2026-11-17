/* Shrinking places — population decline dashboard
 * Vanilla JS + D3 v7. No build step. Data built by scripts/build_data.py. */
(() => {
  "use strict";

  // ---------------------------------------------------------------- content
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const FAM = {
    persistent: { label: "Persistent", color: css("--t-persistent") },
    accelerating: { label: "Accelerating", color: css("--t-accelerating") },
    decelerating: { label: "Slowing", color: css("--t-decelerating") },
    temporary: { label: "Temporary", color: css("--t-temporary") },
  };
  // order matches regions.json "trajectories"
  const TRAJ = [
    { name: "Persistent Decline", fam: "persistent", severe: true, loss: 23.75,
      desc: "Unbroken fast decline (more than 1% a year) throughout. The largest losses; concentrated in the Baltics, the Balkans and former East Germany." },
    { name: "Accelerating Decline", fam: "accelerating", severe: true, loss: 14.96,
      desc: "Moderate decline speeding up into fast decline. Mainly Croatia and Romania, plus inland Spain and Portugal." },
    { name: "Diminishing Decline", fam: "decelerating", severe: true, loss: 15.04,
      desc: "Fast decline slowing to a moderate pace. Mostly former Soviet states (Belarus, Estonia, Russia, Ukraine) and eastern Germany." },
    { name: "Persistent Moderate Decline", fam: "persistent", severe: false, loss: 9.30,
      desc: "Steady losses of 0.3–1% a year. The most common pathway; dominant in Austria, Finland, Hungary, Poland, Romania and Serbia." },
    { name: "Accelerating Moderate Decline", fam: "accelerating", severe: false, loss: 5.84,
      desc: "Stability tipping into moderate decline — a recent onset. Typical of southern Europe: France, Greece, Italy, Spain, Portugal." },
    { name: "Diminished Decline", fam: "decelerating", severe: false, loss: 3.68,
      desc: "Moderate decline easing back to stability — decline coming to an end. Common in Czechia, Slovakia, Sweden and the UK." },
    { name: "Temporary Decline", fam: "temporary", severe: false, loss: 4.03,
      desc: "A short spell of decline followed by growth, returning to stability. 101 of these 131 areas are in Germany." },
  ];
  const SIG = {
    4: { name: "Steady Dual Deficit", color: css("--s4"),
      desc: "More deaths than births throughout, with fertility adding to losses from 2010; migration swings both ways. The most common signature." },
    3: { name: "Volatile Dual Deficit", color: css("--s3"),
      desc: "Natural decline compounded by frequent, intense migration losses. Most strongly associated with rural areas." },
    2: { name: "Natural Reversal", color: css("--s2"),
      desc: "Births and deaths dominate (82% of losses): fertility’s support fades into decline while mortality turns from drag to support after 2005." },
    1: { name: "Migration & Fertility Reversal", color: css("--s1"),
      desc: "Migration and fertility first supported growth, then flipped to drive decline (from about 2006–07). The likeliest path for declining urban areas." },
    5: { name: "Migration Resurgence", color: css("--s5"),
      desc: "Migration turns from loss to gain until about 2015, then reverts; ageing and rising mortality keep natural change negative." },
  };
  const SIG_ORDER = [4, 3, 2, 1, 5];
  const STATE = {
    "-2": { name: "Decline", rule: "≤ −0.99% a year", color: css("--st-m2") },
    "-1": { name: "Moderate decline", rule: "−0.99% to −0.3%", color: css("--st-m1") },
    "0": { name: "Stable", rule: "−0.3% to +0.3%", color: css("--st-0") },
    "1": { name: "Moderate growth", rule: "+0.3% to +0.99%", color: css("--st-p1") },
    "2": { name: "Growth", rule: "≥ +0.99% a year", color: css("--st-p2") },
  };
  const STATE_ORDER = [-2, -1, 0, 1, 2];
  const NODATA = css("--land-nodata");
  const COMP = { fert: css("--c-fert"), mort: css("--c-mort"), mig: css("--c-mig"), nat: css("--c-nat") };

  const CONFIG = { showCoast: false };
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const fmt = d3.format(",");
  const fmt1 = d3.format("+.1f");
  const isMobile = () => window.matchMedia("(max-width: 899px)").matches;

  // ---------------------------------------------------------------- state
  const S = { mode: "traj", year: 2001, sel: null, filter: null, playing: null, k: 1 };
  let DATA, BY_ID, SIGDATA, paths, gMap, svg, zoom, path, features, placeStats, refreshMapReference;

  const $ = (s) => document.querySelector(s);
  const el = (tag, attrs = {}, html = "") => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (html) e.innerHTML = html;
    return e;
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------------------------------------------------------------- encodings
  const trajFill = (t) => {
    const T = TRAJ[t];
    return T.severe ? FAM[T.fam].color : `url(#hatch-${T.fam})`;
  };
  const swatch = (t) => {
    const T = TRAJ[t], c = FAM[T.fam].color;
    return T.severe
      ? `<span class="sw" style="background:${c}"></span>`
      : `<span class="sw hatch" style="background:repeating-linear-gradient(135deg, ${c} 0 2.5px, ${tint(c)} 2.5px 5px)"></span>`;
  };
  function tint(hex, a = 0.28) {
    const c = d3.color(hex), w = d3.color("#ffffff");
    return d3.interpolateRgb(w, c)(a);
  }
  const yi = () => S.year - DATA.years.states[0];

  function category(r) {
    if (S.mode === "traj") return r.trajectory;
    if (S.mode === "sig") return r.signature ?? null;
    const v = r.states?.[yi()];
    return v ?? null;
  }
  function fillFor(r) {
    const c = category(r);
    if (c === null || c === undefined) return NODATA;
    if (S.mode === "traj") return trajFill(c);
    if (S.mode === "sig") return SIG[c].color;
    return STATE[c].color;
  }
  function labelFor(r) {
    if (S.mode === "traj") return r.trajectory != null ? TRAJ[r.trajectory].name : "Grew overall, 2000–18";
    if (S.mode === "sig") return r.signature ? SIG[r.signature].name : "Grew overall, 2000–18";
    const v = r.states?.[yi()];
    return v != null ? `${STATE[v].name} in ${S.year}` : "Not in the decline analysis";
  }

  // ---------------------------------------------------------------- load
  async function loadJSON(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
    return response.json();
  }
  Promise.all([
    loadJSON("data/regions.topo.json"),
    loadJSON("data/regions.json"),
    loadJSON("data/signatures.json"),
  ]).then(([topo, data, sig]) => {
    DATA = data; SIGDATA = sig;
    placeStats = summarisePlaces(data.regions);
    BY_ID = new Map(data.regions.map((r) => [r.id, r]));
    features = topojson.feature(topo, topo.objects.regions).features
      .filter((f) => BY_ID.has(f.properties.id));
    readHash();
    const borders = topojson.mesh(topo, topo.objects.regions, (a, b) =>
      a !== b && BY_ID.get(a.properties.id)?.country !== BY_ID.get(b.properties.id)?.country);
    initMap(borders);
    initUI();
    render();
    $("#loading").remove();
    document.body.dataset.ready = "1";
  }).catch((err) => {
    console.error(err);
    $("#loading").textContent = "Sorry — the data could not be loaded.";
  });

  // ---------------------------------------------------------------- map
  function initMap(borders) {
    const box = $("#map");
    let W = box.clientWidth, H = box.clientHeight;
    svg = d3.select(box).append("svg").attr("viewBox", `0 0 ${W} ${H}`);
    const defs = svg.append("defs");
    for (const [key, f] of Object.entries(FAM)) {
      const p = defs.append("pattern").attr("id", `hatch-${key}`).attr("patternUnits", "userSpaceOnUse")
        .attr("width", 5).attr("height", 5).attr("patternTransform", "rotate(45)");
      p.append("rect").attr("width", 5).attr("height", 5).attr("fill", tint(f.color));
      p.append("rect").attr("width", 2.5).attr("height", 5).attr("fill", f.color);
    }

    const proj = d3.geoAzimuthalEqualArea().rotate([-15, -52]);
    const frame = { type: "Feature", geometry: { type: "MultiPoint", coordinates: [[-10, 34], [30, 34], [-10, 70], [38, 70], [44, 48]] } };
    const fit = () => {
      const pad = isMobile() ? 5 : 12;
      proj.fitExtent([[pad, pad], [W - pad, H - pad]], frame);
    };
    fit();
    path = d3.geoPath(proj);

    gMap = svg.append("g");
    const grid = gMap.append("path").attr("class", "graticule").attr("aria-hidden", "true")
      .datum(d3.geoGraticule().extent([[-65, 5], [150, 85]]).step([10, 10])()).attr("d", path);
    paths = gMap.append("g").selectAll("path").data(features, (d) => d.properties.id).join("path")
      .attr("class", "region hit").attr("d", path)
      .on("pointermove", onHover).on("pointerleave", hideTip)
      .on("click", (ev, d) => { ev.stopPropagation(); select(d.properties.id); });
    const outlines = gMap.append("path").datum(borders).attr("class", "country-lines").attr("d", path);
    const seas = [
      { name: "Atlantic Ocean", at: [-20, 48] }, { name: "Norwegian Sea", at: [-1, 67] },
      { name: "North Sea", at: [2.0, 57] }, { name: "Black Sea", at: [34, 43.3] },
      { name: "Mediterranean Sea", at: [17, 34.7] },
    ];
    const labels = gMap.append("g").attr("class", "sea-names").attr("aria-hidden", "true")
      .selectAll("text").data(seas).join("text").attr("class", "sea-label")
      .text((d) => d.name);
    const positionLabels = () => labels.attr("transform", (d) => `translate(${proj(d.at)})`);
    function showLabels(transform) {
      labels.attr("visibility", (d) => {
        const [x, y] = transform.apply(proj(d.at));
        const halfWidth = d.name.length * (isMobile() ? 3 : 4.5) * transform.k;
        const inFrame = x - halfWidth > 4 && x + halfWidth < W - 4 && y > 14 && y < H - 7;
        const byTools = x + halfWidth > W - 64 && y < 158;
        const bySlider = S.mode === "year" && y > H - 74;
        return inFrame && !byTools && !bySlider && transform.k <= 1.6 ? null : "hidden";
      });
    }
    positionLabels();
    gMap.append("path").attr("class", "sel-halo");
    gMap.append("path").attr("class", "sel");

    zoom = d3.zoom().duration(reducedMotion.matches ? 0 : 250).scaleExtent([0.6, 40]).translateExtent([[-W, -H], [2 * W, 2 * H]])
      .on("zoom", (ev) => {
        gMap.attr("transform", ev.transform);
        updateReference(ev.transform);
        if (S.k !== ev.transform.k) {
          S.k = ev.transform.k;
          defs.selectAll("pattern").attr("patternTransform", `rotate(45) scale(${1 / Math.max(1, S.k ** 0.85)})`);
        }
        hideTip();
      });
    svg.call(zoom).on("dblclick.zoom", null);
    svg.on("click", () => { if (S.sel != null) select(null); });

    // The scale refers to the parallel through the centre of the visible map.
    function updateReference(transform) {
      showLabels(transform);
      const centre = [W / 2, H / 2], sample = 80;
      const at = (dx) => proj.invert(transform.invert([centre[0] + dx, centre[1]]));
      const perPixel = 6371.0088 * d3.geoDistance(at(-sample / 2), at(sample / 2)) / sample;
      const scale = $(".scale");
      scale.hidden = !Number.isFinite(perPixel) || perPixel <= 0;
      if (scale.hidden) return;
      const limit = perPixel * sample;
      const unit = 10 ** Math.floor(Math.log10(limit));
      const km = (limit >= 5 * unit ? 5 : limit >= 2 * unit ? 2 : 1) * unit;
      $(".scale i").style.width = `${km / perPixel}px`;
      $("#scale-label").textContent = `${fmt(km)} km`;
    }
    updateReference(d3.zoomIdentity);
    refreshMapReference = () => updateReference(svg.node().__zoom);

    new ResizeObserver(() => {
      const w = box.clientWidth, h = box.clientHeight;
      if (!w || !h || (w === W && h === H)) return;
      const transform = svg.node().__zoom;
      const centre = proj.invert(transform.invert([W / 2, H / 2]));
      W = w; H = h;
      fit();
      svg.attr("viewBox", `0 0 ${W} ${H}`);
      grid.attr("d", path);
      outlines.attr("d", path);
      paths.attr("d", path);
      positionLabels();
      paintMap();
      zoom.translateExtent([[-W, -H], [2 * W, 2 * H]]);
      const [cx, cy] = proj(centre);
      const next = transform.k === 1 && transform.x === 0 && transform.y === 0
        ? d3.zoomIdentity
        : d3.zoomIdentity.translate(W / 2, H / 2).scale(transform.k).translate(-cx, -cy);
      svg.interrupt().call(zoom.transform, next);
    }).observe(box);

    $("#pill").onclick = () => $("#content").scrollIntoView({
      behavior: reducedMotion.matches ? "instant" : "smooth", block: "start",
    });
    $("#zin").onclick = () => moveMap(250, zoom.scaleBy, 1.8);
    $("#zout").onclick = () => moveMap(250, zoom.scaleBy, 1 / 1.8);
    $("#zreset").onclick = () => moveMap(350, zoom.transform, d3.zoomIdentity);
  }

  function moveMap(duration, action, ...args) {
    (reducedMotion.matches ? svg.interrupt() : svg.transition().duration(duration)).call(action, ...args);
  }

  function paintMap() {
    paths.attr("fill", (d) => fillFor(BY_ID.get(d.properties.id)))
      .classed("dim", (d) => S.filter != null && category(BY_ID.get(d.properties.id)) !== S.filter);
    const f = S.sel != null ? features.find((x) => x.properties.id === S.sel) : null;
    gMap.select(".sel").attr("d", f ? path(f) : null);
    gMap.select(".sel-halo").attr("d", f ? path(f) : null);
  }

  function zoomTo(id) {
    const f = features.find((x) => x.properties.id === id);
    if (!f) return;
    const box = $("#map"), W = box.clientWidth, H = box.clientHeight;
    const [[x0, y0], [x1, y1]] = path.bounds(f);
    const k = Math.min(10, 0.35 / Math.max((x1 - x0) / W, (y1 - y0) / H));
    const kk = Math.max(k, 2.2);
    moveMap(600, zoom.transform,
      d3.zoomIdentity.translate(W / 2, H / 2).scale(kk).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
  }

  // ---------------------------------------------------------------- tooltip
  function onHover(ev, d) {
    if (ev.pointerType === "touch") return;
    const r = BY_ID.get(d.properties.id);
    const tip = $("#tip");
    tip.innerHTML = `<b>${esc(r.name)}</b><span class="k">${esc(r.countryName || r.country || "")}</span><br>${esc(labelFor(r))}`;
    tip.hidden = false;
    const box = $("#map").getBoundingClientRect();
    let x = ev.clientX - box.left + 14, y = ev.clientY - box.top + 14;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    if (x + tw > box.width - 8) x = ev.clientX - box.left - tw - 14;
    if (y + th > box.height - 8) y = ev.clientY - box.top - th - 14;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  }
  function hideTip() { $("#tip").hidden = true; }

  // ---------------------------------------------------------------- UI wiring
  function initUI() {
    const compact = matchMedia("(max-width: 899px)");
    const setKeyLayout = () => { $("#legend").open = !compact.matches; };
    setKeyLayout();
    compact.addEventListener("change", setKeyLayout);
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => setMode(tab.dataset.mode));
      tab.addEventListener("keydown", (event) => {
        const destinations = {
          ArrowLeft: (index + tabs.length - 1) % tabs.length,
          ArrowRight: (index + 1) % tabs.length,
          Home: 0,
          End: tabs.length - 1,
        };
        if (!Object.hasOwn(destinations, event.key)) return;
        event.preventDefault();
        const next = tabs[destinations[event.key]];
        setMode(next.dataset.mode);
        next.focus();
      });
    });
    const updateMotion = () => {
      zoom.duration(reducedMotion.matches ? 0 : 250);
      $("#play").disabled = reducedMotion.matches;
      if (reducedMotion.matches) {
        svg.interrupt();
        stop();
      }
    };
    reducedMotion.addEventListener("change", updateMotion);
    updateMotion();

    $(".skip").addEventListener("click", (event) => {
      event.preventDefault();
      $("#panel").focus();
    });
    $("#about-open").addEventListener("click", () => $("#about").showModal());
    const yr = $("#year");
    yr.addEventListener("input", () => { setYear(+yr.value); stop(); });
    $("#play").addEventListener("click", () => (S.playing ? stop() : play()));

    const dl = $("#names");
    const opts = DATA.regions.map((r) => ({ r, label: `${r.name} — ${r.countryName || r.country || ""}` }))
      .sort((a, b) => a.label.localeCompare(b.label));
    dl.innerHTML = opts.map((o) => `<option value="${esc(o.label)}"></option>`).join("");
    const byLabel = new Map(opts.map((o) => [o.label.toLowerCase(), o.r.id]));
    const q = $("#q");
    let handlingSearch = false;
    const go = () => {
      const v = q.value.trim().toLowerCase();
      if (!v || handlingSearch) return;
      let id = byLabel.get(v);
      if (id == null) {
        const hit = opts.find((o) => o.label.toLowerCase().startsWith(v)) || opts.find((o) => o.label.toLowerCase().includes(v));
        id = hit?.r.id;
      }
      if (id != null) {
        handlingSearch = true;
        try {
          select(id, true);
          $(".place h2.name").focus();
        } finally {
          handlingSearch = false;
        }
      }
    };
    q.addEventListener("change", go);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });

    window.addEventListener("hashchange", () => { readHash(); render(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#about").open && S.sel != null) select(null); });
  }

  function setMode(m) {
    if (m === S.mode) return;
    S.mode = m; S.filter = null; stop();
    writeHash(); render();
    $("#panel").scrollTop = 0;
  }
  function setYear(y) {
    S.year = y; $("#year").value = y; $("#yearout").textContent = y;
    paintMap();
    if (S.mode === "year") {
      const focusedChip = document.activeElement.closest("#legend .chip")?.dataset.k;
      renderLegend();
      if (focusedChip != null) $(`#legend .chip[data-k="${focusedChip}"]`)?.focus({ preventScroll: true });
      if (S.sel == null) renderOverview(); else highlightYear();
    }
    writeHash();
  }
  function play() {
    if (reducedMotion.matches) return;
    if (S.year >= 2018) setYear(2001);
    $("#play").textContent = "❚❚"; $("#play").setAttribute("aria-label", "Pause");
    S.playing = setInterval(() => { if (S.year >= 2018) return stop(); setYear(S.year + 1); }, 750);
  }
  function stop() {
    if (S.playing) clearInterval(S.playing);
    S.playing = null; $("#play").textContent = "▶"; $("#play").setAttribute("aria-label", "Play years");
  }
  function select(id, zoomIn = false) {
    S.sel = id; writeHash(); paintMap(); renderPanel();
    if (!isMobile()) $("#panel").scrollTop = 0;
    if (id != null && zoomIn) zoomTo(id);
  }
  function setFilter(c) {
    const active = document.activeElement;
    const selector = active.matches(".chip") ? ".chip" : active.matches(".rowbtn") ? ".rowbtn" : null;
    const focusedKey = active.dataset.k;
    S.filter = S.filter === c ? null : c;
    paintMap();
    renderLegend();
    if (S.sel == null) renderOverview();
    if (selector) $(`${selector}[data-k="${focusedKey}"]`)?.focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- hash
  function readHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (["traj", "year", "sig"].includes(p.get("v"))) S.mode = p.get("v");
    const y = +p.get("y"); if (y >= 2001 && y <= 2018) S.year = y;
    const r = p.get("r"); S.sel = r != null && BY_ID?.has(+r) ? +r : null;
  }
  function writeHash() {
    const p = new URLSearchParams({ v: S.mode });
    if (S.mode === "year") p.set("y", S.year);
    if (S.sel != null) p.set("r", S.sel);
    history.replaceState(null, "", `#${p}`);
  }

  // ---------------------------------------------------------------- render
  function render() {
    document.querySelectorAll('[role="tab"]').forEach((tab) => {
      const selected = tab.dataset.mode === S.mode;
      tab.setAttribute("aria-selected", selected);
      tab.tabIndex = selected ? 0 : -1;
    });
    $("#panel").setAttribute("aria-labelledby", `tab-${S.mode}`);
    $("#yearbar").hidden = S.mode !== "year";
    refreshMapReference();
    $("#year").value = S.year; $("#yearout").textContent = S.year;
    paintMap(); renderPanel();
  }
  function renderPanel() {
    const selected = S.sel != null;
    $("#panel").classList.toggle("has-place", selected);
    $("#pill").hidden = !selected;
    $("#statistics").innerHTML = selected ? "" : kpis();
    renderLegend();
    if (selected) renderPlace(BY_ID.get(S.sel)); else renderOverview();
  }

  function renderLegend() {
    const L = $("#legend-body");
    const chip = (key, sw, label, count) =>
      `<button class="chip${S.filter != null && S.filter !== key ? " off" : ""}" data-k="${key}" aria-pressed="${S.filter === key}">${sw}<span>${label}</span><span class="count" aria-label="${count} areas">${count}</span></button>`;
    const counts = d3.rollup(DATA.regions, (v) => v.length, category);
    let title, caption, rows, note;
    if (S.mode === "traj") {
      title = "Trajectory of decline";
      caption = "Population trajectories, 2000–2018";
      rows = TRAJ.map((t, i) => chip(i, swatch(i), t.name, counts.get(i) ?? 0));
      note = "Solid colours mark fast decline (over 1% a year). Stripes mark the more moderate pathways.";
    } else if (S.mode === "sig") {
      title = "Demographic signatures";
      caption = "Demographic drivers of decline, 2000–2018";
      rows = SIG_ORDER.map((k) => chip(k, `<span class="sw" style="background:${SIG[k].color}"></span>`, SIG[k].name, counts.get(k) ?? 0));
      note = "Each signature describes how births, deaths and migration contributed to population loss.";
    } else {
      title = `Population change in ${S.year}`;
      caption = `Annual population change, ${S.year - 1}–${S.year}`;
      rows = STATE_ORDER.map((k) => chip(k, `<span class="sw" style="background:${STATE[k].color}"></span>`, STATE[k].name, counts.get(k) ?? 0));
      note = "Annual change is shown for areas that declined over the full study period.";
    }
    $("#legend h2").textContent = title;
    $("#map-title").textContent = caption;
    L.innerHTML = `<div class="chips">${rows.join("")}</div><p class="note">${note} Grey areas fall outside this classification. Select a label to filter the map.</p>`;
    L.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => setFilter(+b.dataset.k)));
  }

  function kpis() {
    const nT = DATA.regions.filter((r) => r.trajectory != null).length;
    const nS = DATA.regions.filter((r) => r.signature != null).length;
    const nAll = DATA.regions.length;
    return `<div class="kpis">
      <div class="kpi"><div class="v">${fmt(nAll)}</div><div class="l">areas mapped</div></div>
      <div class="kpi"><div class="v">${fmt(S.mode === "sig" ? nS : nT)}</div><div class="l">declining areas</div></div>
      <div class="kpi"><div class="v">${S.mode === "sig" ? 5 : S.mode === "traj" ? 7 : 18}</div><div class="l">${S.mode === "sig" ? "signatures" : S.mode === "traj" ? "trajectories" : "years"}</div></div>
    </div>`;
  }

  function renderOverview() {
    const C = $("#content");
    if (S.mode === "traj") {
      const n = d3.rollup(DATA.regions, (v) => v.length, (r) => r.trajectory);
      const max = d3.max(TRAJ, (_, i) => n.get(i));
      C.innerHTML = `<p class="lead">The seven trajectories trace how the pace of population loss changed across Europe. Select a region to explore its history.</p>
        <h2>The seven pathways</h2><ul class="rows">${TRAJ.map((t, i) => `<li><button class="rowbtn" data-k="${i}" aria-pressed="${S.filter === i}">
          ${swatch(i)}<span class="n">${t.name}</span><span>${n.get(i)} areas · −${t.loss}%</span>
          <span class="bar"><i style="width:${(100 * n.get(i)) / max}%;background:${FAM[t.fam].color}"></i></span>
          <span class="d">${t.desc}</span></button></li>`).join("")}</ul>
        <p class="muted">Percentages give the combined population loss of each pathway, 2000–2018. Select any area on the map for its own story.</p>`;
    } else if (S.mode === "sig") {
      const n = d3.rollup(DATA.regions, (v) => v.length, (r) => r.signature);
      C.innerHTML = `<p class="lead">Why did places shrink? Decomposing each area’s annual change into fertility, mortality and migration reveals five signatures. Natural decline (more deaths than births) is almost universal; migration decides how fast places lose people.</p>
        <h2>Five signatures</h2><div class="small-multiples">${SIG_ORDER.map((k) => `<div class="card">
          <button class="rowbtn" data-k="${k}" aria-pressed="${S.filter === k}" style="padding:0 0 6px"><span class="sw" style="background:${SIG[k].color}"></span><span class="n">${SIG[k].name}</span><span>${n.get(k)} areas</span></button>
          <p>${SIG[k].desc}</p><div class="sigchart" data-k="${k}"></div></div>`).join("")}</div>
        <div class="keyrow"><span><i style="background:${COMP.fert}"></i>Fertility</span><span><i style="background:${COMP.mort}"></i>Mortality</span><span><i style="background:${COMP.mig}"></i>Migration</span></div>
        <p class="muted">Lines show each component’s contribution to the year-on-year change in the growth rate (per 1,000, three-year average). Above zero pushes towards growth; below zero towards decline.</p>`;
      C.querySelectorAll(".sigchart").forEach((d) => sigChart(d, SIGDATA[d.dataset.k]));
      if (placeStats) C.insertAdjacentHTML("beforeend", characteristicsOverview());
    } else {
      C.innerHTML = `<p class="lead">Each year, every declining area is classed by its rate of change. In most years, between half and two-thirds of these areas were losing population. Two years stand out: 2011, when fast decline jumped to a third of areas, and 2016, when one in five briefly grew — much of it in Germany.</p>
        <h2>Share of declining areas by annual state</h2><div id="statechart"></div>
        <p class="muted">Thresholds follow the median (0.3%) and standard deviation (0.99%) of annual change across European regions. The 2011 jump coincides with the census round, so part of it may reflect re-estimated populations rather than real change.</p>`;
      stateChart($("#statechart"));
    }
    C.querySelectorAll(".rowbtn").forEach((b) => b.addEventListener("click", () => setFilter(+b.dataset.k)));
  }

  function renderPlace(r) {
    const C = $("#content");
    const where = [r.countryName || r.country, r.code].filter(Boolean).join(" · ");
    const tags = [];
    if (r.trajectory != null) tags.push(`<span class="tag">${swatch(r.trajectory)}${TRAJ[r.trajectory].name}</span>`);
    if (r.signature != null) tags.push(`<span class="tag"><span class="sw" style="background:${SIG[r.signature].color}"></span>${SIG[r.signature].name}</span>`);
    const declined = r.trajectory != null || r.signature != null || r.states;
    let html = `<button class="back" id="back">← All areas</button><div class="place">
      <h2 class="name" tabindex="-1">${esc(r.name)}</h2><p class="where">${esc(where)}</p><div class="tags">${tags.join("")}</div>`;
    if (!declined) {
      html += `<div class="card"><p>This area’s population grew overall between 2000 and 2018, so it is not part of the decline analyses. It is shown in pale grey for context.</p></div>`;
    } else {
      if (r.change != null) html += `<div class="kpis" style="grid-template-columns:1fr 1fr"><div class="kpi"><div class="v">${r.change > 0 ? "+" : "−"}${fmt(Math.abs(r.change))}</div><div class="l">people, 2000–2018</div></div>${r.states ? `<div class="kpi"><div class="v">${r.states.filter((s) => s != null && s < 0).length}<span style="font-size:1rem"> of ${r.states.filter((s) => s != null).length}</span></div><div class="l">years in decline</div></div>` : ""}</div>`;
      if (r.states) html += `<h2>Year by year</h2><div id="seq"></div>`;
      if (r.trajectory != null) html += `<div class="card"><h3>${TRAJ[r.trajectory].name}</h3><p>${TRAJ[r.trajectory].desc}</p></div>`;
      if (r.rates) html += `<h2>What drove the change</h2><div id="drivers"></div>
        <div class="keyrow"><span><i style="background:${COMP.nat}"></i>Births minus deaths</span><span><i style="background:${COMP.mig}"></i>Net migration</span><span><i style="background:var(--ink);border-radius:50%"></i>Total change</span></div>
        <p class="muted">Per 1,000 residents each year.</p><div id="drvtable"></div>`;
      if (r.signature != null) html += `<div class="card" style="margin-top:14px"><h3>${SIG[r.signature].name}</h3><p>${SIG[r.signature].desc}</p></div>`;
    }
    if (r.place) html += placeCharacteristics(r);
    if (CONFIG.showCoast && r.coast_km != null) {
      html += `<p>Distance to the Natural Earth shoreline: ${r.coast_km} km.
        Boundary file coastal flag: ${r.coast == null ? "unavailable" : r.coast ? "yes" : "no"}.</p>`;
    }
    html += `</div>`;
    C.innerHTML = html;
    $("#back").addEventListener("click", () => select(null));
    if (r.states) seqChart($("#seq"), r.states);
    if (r.rates) driverChart($("#drivers"), r.rates);
    const pill = $("#pill");
    pill.textContent = `${r.name} · details ↓`;
  }
  function highlightYear() {
    d3.selectAll("#seq rect.cell").attr("stroke", (d) => (d.year === S.year ? "var(--ink)" : "none"));
  }

  // ---------------------------------------------------------------- place characteristics (2011)
  const PLACE_FIELDS = [
    ["aged_65_pct", "Aged 65 or over", "%"],
    ["foreign_born_pct", "Foreign-born", "%"],
    ["unemployment_pct", "Unemployment", "%"],
    ["distance_city_1m_km", "Distance to a city of over 1 million", " km"],
    ["distance_coast_km", "Distance to the coast", " km"],
    ["mean_altitude_m", "Mean altitude", " m"],
  ];
  const PLACE_TYPES = ["urban", "intermediate", "rural"];
  const placeValue = (value, unit) => value == null ? "—" : `${d3.format(",.1~f")(value)}${unit}`;
  const percentile = (sample, value) => 100 * sample.reduce(
    (rank, item) => rank + (item < value ? 1 : item === value ? 0.5 : 0), 0
  ) / sample.length;

  function summarisePlaces(regions) {
    const areas = regions.filter((region) => region.signature != null && region.place);
    if (!areas.length) return null;
    const samples = Object.fromEntries(PLACE_FIELDS.map(([key]) => [
      key, areas.map((region) => region.place[key]).filter(Number.isFinite),
    ]));
    const bySignature = Object.fromEntries(SIG_ORDER.map((signature) => {
      const members = areas.filter((region) => region.signature === signature);
      const medians = Object.fromEntries(PLACE_FIELDS.map(([key]) => [
        key, d3.median(members, (region) => region.place[key]),
      ]));
      const types = PLACE_TYPES.map((type) => members.filter((region) => region.place.settlement_type === type).length);
      const largest = Math.max(...types);
      const typical = largest ? PLACE_TYPES.filter((_, i) => types[i] === largest).join(", ") : "—";
      return [signature, { medians, typical }];
    }));
    return { samples, bySignature, areaCount: areas.length };
  }

  function placeCharacteristics(region) {
    const { place, signature } = region;
    const medians = placeStats.bySignature[signature].medians;
    const rows = PLACE_FIELDS.filter(([key]) => Number.isFinite(place[key])).map(([key, label, unit]) => {
      const value = place[key], middle = medians[key], sample = placeStats.samples[key];
      return { label, value: placeValue(value, unit), median: placeValue(middle, unit),
               rank: percentile(sample, value), medianRank: percentile(sample, middle), n: sample.length };
    });
    const type = place.settlement_type;
    return `<section class="characteristics" aria-labelledby="place-characteristics-title">
      <h2 id="place-characteristics-title">What sort of place is this?</h2>
      ${rows.length ? `<p class="muted">2011. Dots show percentiles among declining areas with data. Ticks mark the median of this area’s signature.</p>
        <ul class="rank-list">${rows.map(({ label, value, rank, medianRank }) => `
          <li><span>${label}</span><strong>${value}</strong>
          <span class="rank-strip" aria-hidden="true"><i style="left:${medianRank}%"></i><b style="left:${rank}%"></b></span></li>`).join("")}</ul>` : ""}
      ${type ? `<p>Settlement type: <strong>${esc(type)}</strong></p>` : ""}
      <details class="table"><summary>Show place characteristics as a table</summary>
        <table aria-label="Place characteristics in 2011">
          <thead><tr><th scope="col">Indicator</th><th scope="col">Area</th><th scope="col">Percentile</th><th scope="col">Signature median</th><th scope="col">Areas</th></tr></thead>
          <tbody>${rows.map(({ label, value, rank, median, n }) => `<tr><th scope="row">${label}</th><td>${value}</td><td>${Math.round(rank)}</td><td>${median}</td><td>${n}</td></tr>`).join("")}
            ${type ? `<tr><th scope="row">Settlement type</th><td>${esc(type)}</td><td>—</td><td>—</td><td>—</td></tr>` : ""}
          </tbody>
        </table>
      </details>
    </section>`;
  }

  function characteristicsOverview() {
    const headings = { 4: "Steady", 3: "Volatile", 2: "Natural", 1: "Migration &amp; fertility", 5: "Migration resurgence" };
    return `<section class="characteristics" aria-labelledby="characteristics-overview-title">
      <h2 id="characteristics-overview-title">Place characteristics in 2011</h2>
      <p class="muted">Medians and most common settlement type by signature, using available values from ${fmt(placeStats.areaCount)} areas.</p>
      <div class="characteristics-table" tabindex="0" role="region" aria-label="Scrollable signature comparison">
        <table aria-labelledby="characteristics-overview-title">
          <thead><tr><th scope="col">Indicator</th>${SIG_ORDER.map((key) =>
            `<th scope="col" aria-label="${esc(SIG[key].name)}">${headings[key]}</th>`).join("")}</tr></thead>
          <tbody>${PLACE_FIELDS.map(([field, label, unit]) =>
            `<tr><th scope="row">${label}</th>${SIG_ORDER.map((key) =>
              `<td>${placeValue(placeStats.bySignature[key].medians[field], unit)}</td>`).join("")}</tr>`).join("")}
            <tr><th scope="row">Settlement type</th>${SIG_ORDER.map((key) =>
              `<td>${placeStats.bySignature[key].typical}</td>`).join("")}</tr>
          </tbody>
        </table>
      </div>
    </section>`;
  }

  // ---------------------------------------------------------------- charts
  const width = (node) => Math.max(260, node.clientWidth || $("#panel").clientWidth - 40);

  function seqChart(node, states) {
    const W = width(node), H = 46, m = { l: 0, r: 0, t: 4, b: 18 };
    const years = DATA.years.states;
    const x = d3.scaleBand().domain(years).range([m.l, W - m.r]).paddingInner(0.12);
    const s = d3.select(node).append("svg").attr("class", "chart").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", "Annual population change state, 2001 to 2018");
    s.selectAll("rect").data(years.map((y, i) => ({ year: y, v: states[i] }))).join("rect")
      .attr("class", "cell").attr("x", (d) => x(d.year)).attr("y", m.t).attr("width", x.bandwidth()).attr("height", H - m.t - m.b)
      .attr("rx", 3).attr("fill", (d) => (d.v == null ? "#fff" : STATE[d.v].color))
      .attr("stroke", (d) => (S.mode === "year" && d.year === S.year ? "var(--ink)" : d.v == null ? "var(--rule)" : "none"))
      .attr("stroke-width", 1.5)
      .append("title").text((d) => `${d.year}: ${d.v == null ? "no data" : `${STATE[d.v].name} (${STATE[d.v].rule})`}`);
    s.selectAll("text").data([2001, 2005, 2010, 2015, 2018]).join("text")
      .attr("x", (d) => x(d) + x.bandwidth() / 2).attr("y", H - 4).attr("text-anchor", "middle").text((d) => d);
    const k = d3.select(node).append("div").attr("class", "keyrow");
    STATE_ORDER.forEach((v) => k.append("span").html(`<i style="background:${STATE[v].color}"></i>${STATE[v].name}`));
  }

  function driverChart(node, R) {
    const years = DATA.years.rates;
    const rows = years.map((y, i) => {
      const nat = R.birth[i] != null && R.death[i] != null ? +(R.birth[i] - R.death[i]).toFixed(1) : null;
      return { year: y, nat, mig: R.mig[i], tot: R.change[i] };
    });
    const W = width(node), H = 210, m = { l: 34, r: 8, t: 10, b: 22 };
    const lo = d3.min(rows, (d) => Math.min(0, (d.nat < 0 ? d.nat : 0) + (d.mig < 0 ? d.mig : 0), d.tot ?? 0));
    const hi = d3.max(rows, (d) => Math.max(0, (d.nat > 0 ? d.nat : 0) + (d.mig > 0 ? d.mig : 0), d.tot ?? 0));
    const x = d3.scaleBand().domain(years).range([m.l, W - m.r]).paddingInner(0.25);
    const y = d3.scaleLinear().domain([lo, hi]).nice(4).range([H - m.b, m.t]);
    const s = d3.select(node).append("svg").attr("class", "chart").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", "Natural change, net migration and total change per 1,000, 2000 to 2018");
    s.append("g").attr("class", "grid").selectAll("line").data(y.ticks(4)).join("line")
      .attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y);
    s.append("g").selectAll("text").data(y.ticks(4)).join("text").attr("x", m.l - 6).attr("y", (d) => y(d) + 4)
      .attr("text-anchor", "end").text(d3.format("~s"));
    // stacked diverging bars: positives stack up, negatives stack down
    const segs = [];
    rows.forEach((d) => {
      let up = 0, dn = 0;
      [["nat", COMP.nat], ["mig", COMP.mig]].forEach(([k, c]) => {
        const v = d[k]; if (v == null || v === 0) return;
        const a = v > 0 ? up : dn, b = a + v;
        if (v > 0) up = b; else dn = b;
        segs.push({ year: d.year, a, b, c, k, v });
      });
    });
    const bw = x.bandwidth();
    s.append("g").selectAll("rect").data(segs).join("rect")
      .attr("x", (d) => x(d.year)).attr("width", bw)
      .attr("y", (d) => y(Math.max(d.a, d.b)) + (d.a !== 0 ? 1 : 0))
      .attr("height", (d) => Math.max(0.5, Math.abs(y(d.a) - y(d.b)) - (d.a !== 0 ? 1 : 0)))
      .attr("rx", Math.min(3, bw / 3)).attr("fill", (d) => d.c);
    s.append("line").attr("class", "zero").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0));
    const tot = rows.filter((d) => d.tot != null);
    s.append("path").datum(tot).attr("fill", "none").attr("stroke", "var(--ink)").attr("stroke-width", 1.5)
      .attr("d", d3.line().x((d) => x(d.year) + bw / 2).y((d) => y(d.tot)));
    s.append("g").selectAll("circle").data(tot).join("circle").attr("cx", (d) => x(d.year) + bw / 2).attr("cy", (d) => y(d.tot))
      .attr("r", 3).attr("fill", "var(--ink)").attr("stroke", "#fff").attr("stroke-width", 1.5);
    s.append("g").selectAll("text").data([2000, 2005, 2010, 2015, 2018]).join("text")
      .attr("x", (d) => x(d) + bw / 2).attr("y", H - 6).attr("text-anchor", "middle").text((d) => d);
    // hover column with tooltip
    const tip = d3.select(node).style("position", "relative").append("div").attr("class", "tip").attr("hidden", true);
    s.append("g").selectAll("rect").data(rows).join("rect").attr("x", (d) => x(d.year) - 2).attr("width", bw + 4)
      .attr("y", m.t).attr("height", H - m.t - m.b).attr("fill", "transparent")
      .on("pointerenter pointermove", (ev, d) => {
        const f = (v) => (v == null ? "n/a" : fmt1(v));
        tip.attr("hidden", null).html(`<b>${d.year}</b>Births − deaths: ${f(d.nat)}<br>Net migration: ${f(d.mig)}<br>Total: ${f(d.tot)}`);
        const left = Math.min(W - 170, Math.max(0, x(d.year) - 70));
        tip.style("left", `${left}px`).style("top", `${-8}px`).style("transform", "translateY(-100%)");
      })
      .on("pointerleave", () => tip.attr("hidden", true));
    // accessible table
    const t = d3.select("#drvtable").append("details").attr("class", "table");
    t.append("summary").text("Show as table");
    t.append("table").html(`<thead><tr><th>Year</th><th>Births − deaths</th><th>Net migration</th><th>Total</th></tr></thead><tbody>${rows.map((d) =>
      `<tr><td>${d.year}</td><td>${d.nat ?? "–"}</td><td>${d.mig ?? "–"}</td><td>${d.tot ?? "–"}</td></tr>`).join("")}</tbody>`);
  }

  function sigChart(node, D) {
    const W = width(node), H = 120, m = { l: 30, r: 64, t: 8, b: 18 };
    const series = [["fertility", "Fertility", COMP.fert], ["mortality", "Mortality", COMP.mort], ["migration", "Migration", COMP.mig]];
    const all = series.flatMap(([k]) => D[k]);
    const x = d3.scaleLinear().domain(d3.extent(D.years)).range([m.l, W - m.r]);
    const ext = d3.max(all, Math.abs);
    const y = d3.scaleLinear().domain([-ext, ext]).nice(3).range([H - m.b, m.t]);
    const s = d3.select(node).append("svg").attr("class", "chart").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", `Component contributions for ${D.label}`);
    s.append("g").selectAll("text").data(y.ticks(3)).join("text").attr("x", m.l - 6).attr("y", (d) => y(d) + 4)
      .attr("text-anchor", "end").text(d3.format("~g"));
    s.append("line").attr("class", "zero").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0));
    const line = d3.line().x((_, i) => x(D.years[i])).y((v) => y(v)).curve(d3.curveMonotoneX);
    series.forEach(([k, lab, c]) => {
      s.append("path").attr("fill", "none").attr("stroke", c).attr("stroke-width", 2).attr("d", line(D[k]));
    });
    // direct labels at line ends, de-collided
    const ends = series.map(([k, lab, c]) => ({ lab, c, y: y(D[k][D[k].length - 1]) })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 12) ends[i].y = ends[i - 1].y + 12;
    s.append("g").selectAll("text").data(ends).join("text").attr("class", "lab").attr("x", W - m.r + 6).attr("y", (d) => d.y + 4)
      .text((d) => d.lab);
    s.append("g").selectAll("text").data([2001, 2010, 2018]).join("text").attr("x", x).attr("y", H - 4)
      .attr("text-anchor", "middle").text((d) => d);
  }

  function stateChart(node) {
    const years = DATA.years.states;
    const decl = DATA.regions.filter((r) => r.states);
    const rows = years.map((yv, i) => {
      const o = { year: yv }; let n = 0;
      STATE_ORDER.forEach((s) => (o[s] = 0));
      decl.forEach((r) => { const v = r.states[i]; if (v != null) { o[v]++; n++; } });
      STATE_ORDER.forEach((s) => (o[s] = n ? o[s] / n : 0));
      return o;
    });
    const W = width(node), H = 220, m = { l: 34, r: 6, t: 8, b: 22 };
    const x = d3.scaleBand().domain(years).range([m.l, W - m.r]).paddingInner(0.18);
    const y = d3.scaleLinear().domain([0, 1]).range([H - m.b, m.t]);
    const stack = d3.stack().keys(STATE_ORDER)(rows);
    const s = d3.select(node).append("svg").attr("class", "chart").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", "Share of declining areas in each annual state, 2001 to 2018");
    s.append("g").selectAll("g").data(stack).join("g").attr("fill", (d) => STATE[d.key].color)
      .selectAll("rect").data((d) => d).join("rect")
      .attr("x", (d) => x(d.data.year)).attr("width", x.bandwidth())
      .attr("y", (d) => y(d[1]) + 1).attr("height", (d) => Math.max(0, y(d[0]) - y(d[1]) - 1))
      .attr("opacity", (d) => (d.data.year === S.year ? 1 : 0.55))
      .append("title").text(function (d) { const k = d3.select(this.parentNode.parentNode).datum().key; return `${d.data.year} · ${STATE[k].name}: ${Math.round((d[1] - d[0]) * 100)}%`; });
    s.append("g").selectAll("text").data([0, 0.5, 1]).join("text").attr("x", m.l - 6).attr("y", (d) => y(d) + 4)
      .attr("text-anchor", "end").text(d3.format(".0%"));
    s.append("g").selectAll("text").data([2001, 2005, 2010, 2015, 2018]).join("text")
      .attr("x", (d) => x(d) + x.bandwidth() / 2).attr("y", H - 6).attr("text-anchor", "middle").text((d) => d);
    s.append("rect").attr("x", x(S.year) - 2).attr("width", x.bandwidth() + 4).attr("y", m.t - 2).attr("height", H - m.t - m.b + 4)
      .attr("fill", "none").attr("stroke", "var(--ink)").attr("stroke-width", 1.5).attr("rx", 3);
    s.selectAll("rect").filter(function () { return this.parentNode.tagName === "g"; }).on("click", (ev, d) => setYear(d.data.year)).style("cursor", "pointer");
    const k = d3.select(node).append("div").attr("class", "keyrow");
    STATE_ORDER.slice().reverse().forEach((v) => k.append("span").html(`<i style="background:${STATE[v].color}"></i>${STATE[v].name}`));
  }
})();
