// Hazard map: fires, road problems and BoM warnings on one NT map, with layers you choose,
// a legend drawn into the map itself, and PNG / PDF export. Data: data/hazards.js (snapshot of
// public feeds, refreshed by scripts/hazards_snapshot.py) and data/nt_base.js (outline, highways).
// The map is plain SVG with no tiles, so it works offline and exports cleanly.
(function () {
  "use strict";
  const H = window.HAZARDS, B = window.NT_BASE;
  const host = document.getElementById("hazard-map");
  if (!H || !B || !host) return;
  const NS = "http://www.w3.org/2000/svg";
  const el = (t, a = {}, txt) => { const e = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (txt != null) e.textContent = txt; return e; };

  // Equirectangular projection, x scaled by cos(18 S) so the NT keeps its shape.
  const LON0 = 128.9, LAT0 = -10.8, S = 58, KX = Math.cos((18 * Math.PI) / 180);
  const X = (lon) => (lon - LON0) * S * KX, Y = (lat) => (LAT0 - lat) * S;
  const MAP_W = Math.ceil(X(138.1)), MAP_H = Math.ceil(Y(-26.1));
  const PANEL = 210, W = MAP_W + PANEL, TOP = 54, Hh = MAP_H + TOP + 34;

  const LAYERS = [
    { id: "fire", label: "Fire hotspots, last 3 days", color: "#E4602E", on: true },
    { id: "flood", label: "Flooding on a road", color: "#1E6FD9", on: true },
    { id: "closed", label: "Road closed", color: "#A83A12", on: true },
    { id: "damage", label: "Road damage", color: "#F29A3F", on: true },
    { id: "works", label: "Roadworks", color: "#7B61D9", on: false },
    { id: "smoke", label: "Smoke on a road", color: "#5B6878", on: false },
    { id: "other", label: "Other road restrictions", color: "#8A96A3", on: false },
  ];
  const state = Object.fromEntries(LAYERS.map((l) => [l.id, l.on]));
  const fmtTime = (iso) => { try { return new Date(iso).toLocaleString("en-AU", { timeZone: "Australia/Darwin", day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }) + " (Darwin time)"; } catch (e) { return iso; } };
  const roadCount = (k) => H.roads.filter((r) => r.kind === k).length;
  const count = (id) => (id === "fire" ? H.hotspots.length : roadCount(id));

  function draw() {
    const svg = el("svg", { viewBox: `0 0 ${W} ${Hh}`, role: "img", "aria-label": "Map of current fire hotspots and road problems in the Northern Territory", "font-family": "Arial, Helvetica, sans-serif" });
    svg.append(el("rect", { x: 0, y: 0, width: W, height: Hh, fill: "#FFFFFF" }));
    svg.append(el("text", { x: 14, y: 24, "font-size": 17, "font-weight": 700, fill: "#16325C" }, "Northern Territory hazards now"));
    svg.append(el("text", { x: 14, y: 42, "font-size": 11, fill: "#4F5E70" }, "Snapshot: " + fmtTime(H.generated)));
    const g = el("g", { transform: `translate(10 ${TOP})` });
    B.outline.forEach((ring) => g.append(el("path", { d: "M" + ring.map(([lo, la]) => `${X(lo).toFixed(1)},${Y(la).toFixed(1)}`).join("L") + "Z", fill: "#EEF3F9", stroke: "#16325C", "stroke-width": 1.2 })));
    B.highways.forEach((line) => g.append(el("path", { d: "M" + line.map(([lo, la]) => `${X(lo).toFixed(1)},${Y(la).toFixed(1)}`).join("L"), fill: "none", stroke: "#B9C6D6", "stroke-width": 1.4 })));
    // Darwin for orientation only (a capital city, not a remote community)
    g.append(el("circle", { cx: X(130.84), cy: Y(-12.46), r: 3.2, fill: "#16325C" }));
    g.append(el("text", { x: X(130.84) + 6, y: Y(-12.46) - 5, "font-size": 11, fill: "#16325C", "font-weight": 700 }, "Darwin"));
    if (state.fire) H.hotspots.forEach((h) => g.append(el("circle", { cx: X(h.lon).toFixed(1), cy: Y(h.lat).toFixed(1), r: Math.min(5, 2 + Math.log2(h.n + 1) / 2).toFixed(1), fill: "#E4602E", "fill-opacity": 0.55 })));
    LAYERS.filter((l) => l.id !== "fire" && state[l.id]).forEach((l) => {
      H.roads.filter((r) => r.kind === l.id).forEach((r) => {
        const [x1, y1, x2, y2] = [X(r.from[0]), Y(r.from[1]), X(r.to[0]), Y(r.to[1])];
        g.append(el("line", { x1, y1, x2, y2, stroke: l.color, "stroke-width": 3.2, "stroke-linecap": "round" }));
        g.append(el("circle", { cx: x1, cy: y1, r: 3.6, fill: l.color, stroke: "#fff", "stroke-width": 1 }));
      });
    });
    svg.append(g);
    // Legend, inside the map so a PNG or PDF carries it
    const lx = MAP_W + 22; let ly = TOP + 6;
    svg.append(el("text", { x: lx, y: ly, "font-size": 12, "font-weight": 700, fill: "#16325C" }, "Legend"));
    ly += 18;
    LAYERS.filter((l) => state[l.id]).forEach((l) => {
      if (l.id === "fire") svg.append(el("circle", { cx: lx + 6, cy: ly - 4, r: 5, fill: l.color, "fill-opacity": 0.6 }));
      else svg.append(el("line", { x1: lx, y1: ly - 4, x2: lx + 14, y2: ly - 4, stroke: l.color, "stroke-width": 3.2, "stroke-linecap": "round" }));
      svg.append(el("text", { x: lx + 22, y: ly, "font-size": 11, fill: "#14243B" }, `${l.label} (${count(l.id)})`));
      ly += 19;
    });
    svg.append(el("line", { x1: lx, y1: ly - 4, x2: lx + 14, y2: ly - 4, stroke: "#B9C6D6", "stroke-width": 1.4 }));
    svg.append(el("text", { x: lx + 22, y: ly, "font-size": 11, fill: "#14243B" }, "Highway"));
    ly += 30;
    svg.append(el("text", { x: lx, y: ly, "font-size": 12, "font-weight": 700, fill: "#16325C" }, "BoM warnings"));
    ly += 16;
    const warn = H.warnings.length ? H.warnings.map((w) => w.title) : ["None current for the NT"];
    warn.slice(0, 8).forEach((t) => { wrap(t, 30).forEach((line, i) => { svg.append(el("text", { x: lx, y: ly, "font-size": 10.5, fill: "#14243B" }, (i ? "  " : "• ") + line)); ly += 13; }); ly += 3; });
    const src = "Sources: Geoscience Australia DEA Hotspots; NT Government Road Report; Bureau of Meteorology. Fire points are grouped into cells of about 5 km. Check the source before travelling.";
    wrap(src, 120).forEach((line, i) => svg.append(el("text", { x: 14, y: Hh - 20 + i * 12, "font-size": 9.5, fill: "#4F5E70" }, line)));
    host.replaceChildren(svg);
  }
  function wrap(text, n) { const out = []; let cur = ""; for (const w of text.split(" ")) { if ((cur + " " + w).trim().length > n) { out.push(cur.trim()); cur = w; } else cur += " " + w; } if (cur.trim()) out.push(cur.trim()); return out; }

  // Layer switches
  const ctl = document.getElementById("hazard-layers");
  LAYERS.forEach((l) => {
    const lab = document.createElement("label");
    lab.className = "layer-chip";
    lab.innerHTML = `<input type="checkbox" ${l.on ? "checked" : ""}><i style="background:${l.color}"></i><span>${l.label}</span><b>${count(l.id)}</b>`;
    lab.querySelector("input").addEventListener("change", (e) => { state[l.id] = e.target.checked; draw(); });
    ctl.append(lab);
  });
  const note = document.getElementById("hazard-note");
  if (note) note.textContent = Object.keys(H.errors || {}).length ? "Some feeds could not be read at the last snapshot: " + Object.keys(H.errors).join(", ") + "." : "";

  // Export: PNG through a canvas; PDF through the browser's print dialog (Save as PDF), map only.
  document.getElementById("hazard-png").addEventListener("click", () => {
    const svg = host.querySelector("svg");
    let xml = new XMLSerializer().serializeToString(svg);
    if (!/^<svg[^>]*xmlns=/.test(xml)) xml = xml.replace("<svg", `<svg xmlns="${NS}"`);   // the serializer usually adds it
    xml = xml.replace("<svg", `<svg width="${W * 2}" height="${Hh * 2}"`);
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas"); c.width = W * 2; c.height = Hh * 2;
      c.getContext("2d").drawImage(img, 0, 0);
      const a = document.createElement("a"); a.download = "nt-hazards-" + (H.generated || "").slice(0, 10) + ".png"; a.href = c.toDataURL("image/png"); a.click();
    };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
  });
  document.getElementById("hazard-pdf").addEventListener("click", () => { document.body.dataset.print = "map"; window.print(); });
  window.addEventListener("afterprint", () => { delete document.body.dataset.print; });
  draw();
})();
