// Hazard map: fires, road problems and BoM warnings on a real NT base map, with layers you choose,
// a legend that follows them, and PNG / PDF export.
// Base maps (tiles, needs internet): Geoscience Australia National Base Map (CC BY 4.0, the default),
// Esri World Imagery and Esri World Topographic (Esri terms: attribution, non-commercial use).
// Hazard data: data/hazards.js, a snapshot of public feeds refreshed by scripts/hazards_snapshot.py.
// If the tiles cannot load (offline), the NT outline from data/nt_base.js is drawn instead.
(function () {
  "use strict";
  const H = window.HAZARDS, B = window.NT_BASE, L = window.L;
  const host = document.getElementById("hazard-map");
  if (!H || !host) return;
  const note = document.getElementById("hazard-note");
  if (!L) { if (note) note.textContent = "The map library could not load. Check the internet connection and reload."; return; }

  const BASES = [
    { id: "ga", label: "Topographic (Geoscience Australia)", max: 16,
      url: "https://services.ga.gov.au/gis/rest/services/NationalBaseMap/MapServer/tile/{z}/{y}/{x}",
      attr: "Base map © Commonwealth of Australia (Geoscience Australia), CC BY 4.0" },
    { id: "img", label: "Satellite imagery (Esri)", max: 17,
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attr: "Tiles © Esri. Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community" },
    { id: "topo", label: "Topographic (Esri)", max: 16,
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
      attr: "Tiles © Esri. Sources: Esri, HERE, Garmin, Intermap, USGS, FAO, NPS, NRCAN, GeoBase, IGN, (c) OpenStreetMap contributors, and the GIS User Community" },
  ];
  const LAYERS = [
    { id: "fire", label: "Fire hotspots, last 3 days", color: "#E4602E", on: true },
    { id: "flood", label: "Flooding on a road", color: "#1E6FD9", on: true },
    { id: "closed", label: "Road closed", color: "#A83A12", on: true },
    { id: "damage", label: "Road damage", color: "#F29A3F", on: true },
    { id: "works", label: "Roadworks", color: "#7B61D9", on: false },
    { id: "smoke", label: "Smoke on a road", color: "#5B6878", on: false },
    { id: "other", label: "Other road restrictions", color: "#8A96A3", on: false },
    { id: "floodarea", label: "Mapped 1% AEP flood areas (NT Planning Scheme)", color: "#2F6DB5", on: true, area: true },
    { id: "stand", label: "STAND satellite sites (evacuation centres, fire depots)", color: "#0E8FA8", on: true, square: true },
  ];
  const NT = [[-26.1, 128.9], [-10.8, 138.1]];
  const SOURCES = "Hazards: Geoscience Australia DEA Hotspots; NT Government Road Report; Bureau of Meteorology. Planning layers: NT Planning Scheme flood overlay (NTLIS); STAND sites (DITRDCSA). Fire points are grouped into cells of about 5 km and can include planned burns. Check the source before travelling.";
  const fmtTime = (iso) => { try { return new Date(iso).toLocaleString("en-AU", { timeZone: "Australia/Darwin", day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }) + " (Darwin time)"; } catch (e) { return iso; } };
  const roadCount = (k) => H.roads.filter((r) => r.kind === k).length;
  const standCount = ((window.UNDERLINK || {}).layers || {}).stand_sites_nt || (B && B.stand ? B.stand.length : 0);
  const count = (id) => (id === "fire" ? H.hotspots.length : id === "floodarea" ? "" : id === "stand" ? standCount : roadCount(id));
  const swatch = (l) => (l.id === "fire" ? "dot" : l.area ? "area" : l.square ? "sq" : "bar");
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const timeEl = document.getElementById("hazard-time");
  if (timeEl) timeEl.textContent = "Snapshot: " + fmtTime(H.generated);

  // ---- map, base layers ----------------------------------------------------------------------
  const map = L.map(host, { zoomSnap: 0.25, minZoom: 4, maxBounds: [[-32, 122], [-6, 144]], scrollWheelZoom: false });
  map.fitBounds(NT);
  map.attributionControl.setPrefix(false);
  let base = null, tileErrors = 0, outline = null;
  function setBase(id) {
    const b = BASES.find((x) => x.id === id) || BASES[0];
    if (base) map.removeLayer(base);
    tileErrors = 0;
    base = L.tileLayer(b.url, { attribution: b.attr, maxNativeZoom: b.max, maxZoom: 18, crossOrigin: "anonymous" });
    base.on("tileerror", () => { if (++tileErrors === 4) showOutline(); });
    base.on("load", () => { if (outline) { map.removeLayer(outline); outline = null; if (note) note.textContent = baseNote(); } });
    base.addTo(map); base.bringToBack();
    current = b;
  }
  function showOutline() {
    if (!B || outline) return;
    outline = L.layerGroup(B.outline.map((ring) => L.polygon(ring.map(([lo, la]) => [la, lo]), { color: "#16325C", weight: 1.2, fill: true, fillColor: "#EEF3F9", fillOpacity: 1, interactive: false }))).addTo(map);
    outline.eachLayer((l) => l.bringToBack());
    if (note) note.textContent = "The base map could not load (no internet?). Showing the NT outline instead; the hazard layers still work.";
  }
  const baseNote = () => Object.keys(H.errors || {}).length ? "Some feeds could not be read at the last snapshot: " + Object.keys(H.errors).join(", ") + "." : "";
  let current = BASES[0];
  setBase("ga");

  // ---- hazard layers -------------------------------------------------------------------------
  const groups = {};
  LAYERS.forEach((l) => { groups[l.id] = L.layerGroup(); });
  H.hotspots.forEach((h) => L.circleMarker([h.lat, h.lon], { radius: Math.min(7, 3 + Math.log2(h.n + 1) / 1.6), stroke: false, fillColor: "#E4602E", fillOpacity: 0.6 })
    .bindPopup(`<b>Fire hotspot</b><br>${h.n} satellite detection${h.n === 1 ? "" : "s"} in this 5 km cell<br>Latest: ${esc(fmtTime(h.latest + ":00Z"))}`).addTo(groups.fire));
  H.roads.forEach((r) => {
    const l = LAYERS.find((x) => x.id === r.kind) || LAYERS[LAYERS.length - 1];
    const a = [r.from[1], r.from[0]], b = [r.to[1], r.to[0]];
    const pop = `<b>${esc(r.what || l.label)}</b>${r.restriction ? "<br>" + esc(r.restriction) : ""}<br><small>Source: NT Road Report</small>`;
    L.polyline([a, b], { color: l.color, weight: 5, opacity: 0.9, lineCap: "round" }).bindPopup(pop).addTo(groups[l.id]);
    L.circleMarker(a, { radius: 4.5, color: "#fff", weight: 1.5, fillColor: l.color, fillOpacity: 1 }).bindPopup(pop).addTo(groups[l.id]);
  });
  // Planning layers: published 1% AEP flood study areas and STAND satellite sites (positions only, no names)
  if (B && B.flood) B.flood.forEach((ring) => L.polygon(ring.map(([lo, la]) => [la, lo]), { color: "#2F6DB5", weight: 1, fillColor: "#2F6DB5", fillOpacity: 0.3 })
    .bindPopup("<b>Mapped 1% AEP flood area</b><br>A published flood study in the NT Planning Scheme.<br><small>Source: NTLIS, NT Government</small>").addTo(groups.floodarea));
  if (B && B.stand) B.stand.forEach(([lo, la]) => L.marker([la, lo], { icon: L.divIcon({ className: "hz-sq", iconSize: [10, 10] }), keyboard: false })
    .bindPopup("<b>STAND satellite site</b><br>NBN satellite service at an evacuation centre or fire depot (layer 2).<br><small>Source: DITRDCSA</small>").addTo(groups.stand));
  const state = Object.fromEntries(LAYERS.map((l) => [l.id, l.on]));
  LAYERS.forEach((l) => { if (l.on) groups[l.id].addTo(map); });

  // ---- legend (inside the map, so the PDF carries it) ----------------------------------------
  const warnings = H.warnings.length ? H.warnings.map((w) => w.title) : ["None current for the NT"];
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => { const d = L.DomUtil.create("div", "hz-legend"); L.DomEvent.disableClickPropagation(d); return d; };
  legend.addTo(map);
  function drawLegend() {
    const d = legend.getContainer();
    const rows = LAYERS.filter((l) => state[l.id]).map((l) =>
      `<li><i class="${swatch(l)}" style="background:${l.color}"></i>${esc(l.label)} <b>${count(l.id)}</b></li>`).join("");
    const open = d.querySelector("details") ? d.querySelector("details").open : !window.matchMedia("(max-width: 720px)").matches;
    d.innerHTML = `<details${open ? " open" : ""}><summary class="hz-legend-t">Legend</summary><ul>${rows || "<li>No layer selected</li>"}</ul>` +
      `<p class="hz-legend-t">BoM warnings</p><ul class="hz-warn">${warnings.slice(0, 6).map((t) => `<li>${esc(t)}</li>`).join("")}</ul></details>`;
  }
  drawLegend();

  // ---- side panel: base map choice and layer switches ----------------------------------------
  const baseBox = document.getElementById("hazard-base");
  if (baseBox) BASES.forEach((b, k) => {
    const lab = document.createElement("label");
    lab.className = "layer-chip base-chip";
    lab.innerHTML = `<input type="radio" name="hz-base" value="${b.id}" ${k === 0 ? "checked" : ""}><span>${esc(b.label)}</span>`;
    lab.querySelector("input").addEventListener("change", () => setBase(b.id));
    baseBox.append(lab);
  });
  const ctl = document.getElementById("hazard-layers");
  LAYERS.forEach((l) => {
    const lab = document.createElement("label");
    lab.className = "layer-chip";
    lab.innerHTML = `<input type="checkbox" ${l.on ? "checked" : ""}><i style="background:${l.color}"></i><span>${esc(l.label)}</span><b>${count(l.id)}</b>`;
    lab.querySelector("input").addEventListener("change", (e) => {
      state[l.id] = e.target.checked;
      if (state[l.id]) groups[l.id].addTo(map); else map.removeLayer(groups[l.id]);
      drawLegend();
    });
    ctl.append(lab);
  });
  if (note) note.textContent = baseNote();

  // ---- PNG: base tiles, layers, title, legend and sources drawn onto one canvas ----------------
  function wrapText(ctx, text, width) {
    const out = []; let cur = "";
    for (const w of text.split(" ")) { const t = cur ? cur + " " + w : w; if (ctx.measureText(t).width > width && cur) { out.push(cur); cur = w; } else cur = t; }
    if (cur) out.push(cur); return out;
  }
  document.getElementById("hazard-png").addEventListener("click", () => {
    const size = map.getSize(), S = 2, TOP = 52, PAD = 14;
    const c = document.createElement("canvas"), ctx = c.getContext("2d");
    ctx.font = "11px Arial";
    const foot = wrapText(ctx, SOURCES + " " + current.attr + ".", size.x - 2 * PAD);
    const BOT = 14 + foot.length * 14;
    c.width = size.x * S; c.height = (TOP + size.y + BOT) * S;
    ctx.scale(S, S);
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, size.x, TOP + size.y + BOT);
    ctx.fillStyle = "#16325C"; ctx.font = "bold 17px Arial"; ctx.fillText("Northern Territory hazards now", PAD, 24);
    ctx.fillStyle = "#4F5E70"; ctx.font = "11px Arial"; ctx.fillText("Snapshot: " + fmtTime(H.generated), PAD, 42);
    ctx.save(); ctx.translate(0, TOP);
    ctx.beginPath(); ctx.rect(0, 0, size.x, size.y); ctx.clip();
    ctx.fillStyle = "#EEF3F9"; ctx.fillRect(0, 0, size.x, size.y);
    const box = host.getBoundingClientRect();
    host.querySelectorAll(".leaflet-tile-pane img.leaflet-tile-loaded").forEach((img) => {
      const r = img.getBoundingClientRect();
      try { ctx.drawImage(img, r.left - box.left, r.top - box.top, r.width, r.height); } catch (e) { /* skip a tile that cannot be drawn */ }
    });
    const pt = (ll) => map.latLngToContainerPoint(ll);
    LAYERS.filter((l) => state[l.id] && l.area).forEach((l) => groups[l.id].eachLayer((g) => {
      const p = g.getLatLngs()[0].map(pt);
      ctx.fillStyle = "rgba(47,109,181,0.3)"; ctx.strokeStyle = l.color; ctx.lineWidth = 1;
      ctx.beginPath(); p.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y))); ctx.closePath(); ctx.fill(); ctx.stroke();
    }));
    LAYERS.filter((l) => state[l.id] && l.square).forEach((l) => groups[l.id].eachLayer((g) => {
      const q = pt(g.getLatLng());
      ctx.fillStyle = l.color; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.fillRect(q.x - 4.5, q.y - 4.5, 9, 9); ctx.strokeRect(q.x - 4.5, q.y - 4.5, 9, 9);
    }));
    LAYERS.filter((l) => state[l.id] && l.id !== "fire" && !l.area && !l.square).forEach((l) => groups[l.id].eachLayer((g) => {
      if (g instanceof L.Polyline) {
        const p = g.getLatLngs().map(pt);
        ctx.strokeStyle = l.color; ctx.lineWidth = 5; ctx.lineCap = "round"; ctx.globalAlpha = 0.9;
        ctx.beginPath(); p.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y))); ctx.stroke(); ctx.globalAlpha = 1;
      } else {
        const q = pt(g.getLatLng());
        ctx.fillStyle = l.color; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(q.x, q.y, 4.5, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
      }
    }));
    if (state.fire) groups.fire.eachLayer((g) => {
      const q = pt(g.getLatLng());
      ctx.fillStyle = "rgba(228,96,46,0.6)"; ctx.beginPath(); ctx.arc(q.x, q.y, g.getRadius(), 0, 2 * Math.PI); ctx.fill();
    });
    // legend, bottom right, as on screen
    const items = LAYERS.filter((l) => state[l.id]);
    ctx.font = "11px Arial";
    const lw = Math.max(190, ...items.map((l) => ctx.measureText(`${l.label} (${count(l.id)})`).width + 40), ...warnings.slice(0, 6).map((t) => Math.min(260, ctx.measureText(t).width + 24)));
    const wl = warnings.slice(0, 6).flatMap((t) => wrapText(ctx, t, lw - 24));
    const lh = 26 + items.length * 18 + 22 + wl.length * 14 + 8;
    const lx = size.x - lw - 10, ly = size.y - lh - 22;
    ctx.fillStyle = "rgba(255,255,255,0.94)"; ctx.strokeStyle = "#D6DEE8"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.roundRect ? ctx.roundRect(lx, ly, lw, lh, 8) : ctx.rect(lx, ly, lw, lh); ctx.fill(); ctx.stroke();
    let y = ly + 18;
    ctx.fillStyle = "#16325C"; ctx.font = "bold 12px Arial"; ctx.fillText("Legend", lx + 10, y); y += 16;
    ctx.font = "11px Arial";
    items.forEach((l) => {
      ctx.fillStyle = l.color;
      if (l.id === "fire") { ctx.beginPath(); ctx.arc(lx + 16, y - 4, 5, 0, 2 * Math.PI); ctx.fill(); }
      else if (l.area) { ctx.globalAlpha = 0.45; ctx.fillRect(lx + 10, y - 9, 14, 10); ctx.globalAlpha = 1; }
      else if (l.square) ctx.fillRect(lx + 12, y - 8, 9, 9);
      else ctx.fillRect(lx + 10, y - 6, 14, 4);
      ctx.fillStyle = "#14243B"; ctx.fillText(count(l.id) === "" ? l.label : `${l.label} (${count(l.id)})`, lx + 32, y); y += 18;
    });
    y += 4; ctx.fillStyle = "#16325C"; ctx.font = "bold 12px Arial"; ctx.fillText("BoM warnings", lx + 10, y); y += 15;
    ctx.fillStyle = "#14243B"; ctx.font = "11px Arial";
    wl.forEach((t) => { ctx.fillText(t, lx + 12, y); y += 14; });
    ctx.restore();
    ctx.fillStyle = "#4F5E70"; ctx.font = "11px Arial";
    foot.forEach((t, i) => ctx.fillText(t, PAD, TOP + size.y + 18 + i * 14));
    try {
      c.toBlob((blob) => {
        const a = document.createElement("a");
        a.download = "nt-hazards-" + (H.generated || "").slice(0, 10) + ".png";
        a.href = URL.createObjectURL(blob); a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      }, "image/png");
    } catch (e) { if (note) note.textContent = "This browser blocked the picture because of the base map. Try another base map, or use Save as PDF."; }
  });

  // ---- PDF: the browser's print dialog, map only (see the print rules in styles.css) -----------
  document.getElementById("hazard-pdf").addEventListener("click", () => {
    document.body.dataset.print = "map";
    const det = legend.getContainer().querySelector("details"); if (det) det.open = true;   // the PDF always carries the legend
    map.invalidateSize(); map.fitBounds(NT);
    setTimeout(() => window.print(), 400);                      // let the resized map fetch its tiles
  });
  window.addEventListener("afterprint", () => { if (document.body.dataset.print === "map") { delete document.body.dataset.print; map.invalidateSize(); } });
})();
