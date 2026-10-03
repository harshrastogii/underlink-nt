// Underlink web app. No build step and no dependencies: open index.html from disk or any static host.
// Every number comes from window.UNDERLINK (data/public.js), which scripts/export_web_data.py
// writes from outputs/public/. The sandbox network is made up and holds no real site.
(function () {
  "use strict";
  const D = window.UNDERLINK;
  const $ = (id) => document.getElementById(id);
  const SVGNS = "http://www.w3.org/2000/svg";
  const fmt = (n) => Number(n).toLocaleString("en-AU");
  const about = (n, to = 100) => fmt(Math.round(n / to) * to);

  function el(tag, attrs = {}, ...kids) {
    const svg = ["svg", "g", "circle", "rect", "line", "text", "path", "title", "animateMotion", "animate", "animateTransform"].includes(tag);
    const e = svg ? document.createElementNS(SVGNS, tag) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.setAttribute("class", v);
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k !== null && k !== undefined) e.append(k.nodeType ? k : document.createTextNode(k));
    return e;
  }

  // Segmented control: calls onChange(value) and marks the chosen button.
  function seg(host, label, options, value, onChange) {
    host.replaceChildren(el("span", { class: "seg-label" }, label));
    const buttons = options.map(([v, text]) => {
      const b = el("button", { type: "button", role: "radio", "aria-checked": String(v === value) }, text);
      b.addEventListener("click", () => {
        buttons.forEach((x) => x.setAttribute("aria-checked", "false"));
        b.setAttribute("aria-checked", "true");
        onChange(v);
      });
      return b;
    });
    host.append(...buttons);
    onChange(value);
  }

  const fact = (n, text, cls = "") => el("div", { class: "fact" }, el("span", { class: "n " + cls }, n), el("p", {}, text));
  const stat = (n, text, cls = "") => el("div", { class: "stat" }, el("div", { class: "num " + cls }, n), el("p", { class: "what" }, text));

  const c = D.chains, r = D.relays, rep = D.repair, fb = D.fallbacks, a = D.accc_check;
  const inMnhp = r.spof_relays - Object.values(r.power_classes).reduce((s, v) => s + v, 0);

  // ---- Hero chain ---------------------------------------------------------------
  (function chain() {
    const svg = $("chain");
    const y = 78, xs = [205, 275, 345, 415, 485];
    const off = new Set();
    const status = $("chain-status");
    // Phones draw the chain top to bottom so all of it fits the screen; wider screens draw it left to right.
    const phone = window.matchMedia("(max-width: 720px)");
    const K = 0.78;                                          // vertical spacing factor on phones
    const P = (x, yy) => (phone.matches ? [70 + (yy - y), 24 + (x - 40) * K] : [x, yy]);
    const line = (x1, y1, x2, y2, attrs) => { const [a1, b1] = P(x1, y1), [a2, b2] = P(x2, y2);
      return el("line", { x1: a1, y1: b1, x2: a2, y2: b2, ...attrs }); };
    const circle = (x, r, attrs) => { const [cx, cy] = P(x, y); return el("circle", { cx, cy, r, ...attrs }); };
    const box = (x, w, h, attrs) => { const [cx, cy] = P(x, y); const [bw, bh] = phone.matches ? [h, w] : [w, h];
      return el("rect", { x: cx - bw / 2, y: cy - bh / 2, width: bw, height: bh, ...attrs }); };
    function draw() {
      svg.replaceChildren();
      svg.setAttribute("viewBox", phone.matches ? `0 0 330 ${Math.round(48 + 684 * K)}` : "0 0 760 170");
      // Links past the first switched-off relay no longer carry service, so they fade.
      const cutX = off.size ? xs[Math.min(...off)] : Infinity;
      const seg_ = (x1, x2) => svg.append(line(x1, y, x2, y, { stroke: "#fff", "stroke-width": 3, opacity: x2 <= cutX ? 1 : 0.35 }));
      // fibre town and fibre-connected site
      svg.append(box(47, 14, 52, { fill: "#fff" }));
      seg_(54, 112); svg.append(circle(125, 13, { fill: "none", stroke: "#fff", "stroke-width": 3 }));
      seg_(138, xs[0] - 15);
      xs.forEach((x, i) => {
        if (i > 0) seg_(xs[i - 1] + 15, x - 15);
        const isOff = off.has(i);
        const [cx, cy] = P(x, y);
        const g = el("g", { class: "relay", tabindex: 0, role: "button", "aria-pressed": String(isOff), "data-i": i,
          "aria-label": `Relay ${i + 1}, ${isOff ? "switched off" : "working"}` });
        g.append(el("circle", { cx, cy, r: 15, fill: isOff ? "none" : "#F6A15E", stroke: isOff ? "#fff" : "none",
          "stroke-width": 2.5, "stroke-dasharray": isOff ? "4 3" : null }));
        if (isOff) g.append(el("path", { d: `M${cx - 6} ${cy - 6} L${cx + 6} ${cy + 6} M${cx + 6} ${cy - 6} L${cx - 6} ${cy + 6}`, stroke: "#fff", "stroke-width": 2.5 }));
        const toggle = () => { off.has(i) ? off.delete(i) : off.add(i); draw(); const f = $("chain").querySelector(`[data-i="${i}"]`); if (f) f.focus(); };
        g.addEventListener("click", toggle);
        g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
        svg.append(g);
      });
      seg_(xs[4] + 15, 568);
      const down = off.size > 0;
      svg.append(box(581, 26, 26, { fill: "none", stroke: "#fff", "stroke-width": 3, opacity: down ? 0.35 : 1 }));
      svg.append(line(594, y, 640, y, { stroke: "#fff", "stroke-width": 3, "stroke-dasharray": "3 4", opacity: down ? 0.35 : 1 }));
      svg.append(circle(690, 34, { fill: down ? "rgba(0,0,0,0.12)" : "none", stroke: "#fff", "stroke-width": 2.5, "stroke-dasharray": "6 5" }));
      svg.append(circle(690, 7, { fill: down ? "none" : "#fff", stroke: down ? "#fff" : "none", "stroke-width": 2 }));
      const txt = { fill: "#fff", "font-family": "Arial, sans-serif" };
      const label = (x, lines, bold) => {
        const [cx, cy] = P(x, y);
        lines.forEach((t, k) => svg.append(phone.matches
          ? el("text", { x: 118, y: cy + 5 - (lines.length - 1) * 8 + k * 16, "text-anchor": "start", "font-size": 14, "font-weight": bold ? 700 : 400, ...txt }, t)
          : el("text", { x: cx, y: y + 44 + k * 15, "text-anchor": "middle", "font-size": 12.5, "font-weight": bold ? 700 : 400, ...txt }, t)));
      };
      label(47, ["Fibre", "town"]); label(125, ["Fibre-connected", "site"]); label(581, ["Community", "mobile site"]);
      label(690, [down ? "No service" : "Community"], true);   // sits under (or beside) the dashed circle
      const tag = { fill: "#FFD9B0", "font-weight": 700, "font-family": "Arial, sans-serif" };
      if (phone.matches) {
        const [, t0] = P(xs[0] - 10, y), [, t1] = P(xs[4] + 10, y);
        svg.append(el("line", { x1: 38, y1: t0, x2: 38, y2: t1, stroke: "#F6A15E", "stroke-width": 2 }));
        ["5 single-path", "relays in a row"].forEach((t, k) => svg.append(el("text", { x: 118, y: (t0 + t1) / 2 - 4 + k * 17, "font-size": 14, ...tag }, t)));
      } else {
        svg.append(el("line", { x1: xs[0] - 10, y1: 30, x2: xs[4] + 10, y2: 30, stroke: "#F6A15E", "stroke-width": 2 }));
        svg.append(el("text", { x: (xs[0] + xs[4]) / 2, y: 22, "text-anchor": "middle", "font-size": 13, ...tag }, "5 single-path relays in a row"));
      }
      // Signal pulses run from the fibre town along the chain and stop at the first switched-off relay.
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const stops = [47, 125, ...xs, 581, 690];
        const first = off.size ? Math.min(...off) : -1;
        const live = first < 0 ? stops : stops.slice(0, stops.indexOf(xs[first]) + 1);
        const d = "M" + live.map((x) => P(x, y).join(",")).join("L");
        const dur = (live.length * 0.42).toFixed(2);
        for (let k = 0; k < 3; k++) {
          const dot = el("circle", { r: 4.5, fill: first < 0 ? "#FFFFFF" : "#FFD9B0", "pointer-events": "none" });
          dot.append(el("animateMotion", { dur: dur + "s", begin: (k * dur / 3).toFixed(2) + "s", repeatCount: "indefinite", path: d }));
          svg.append(dot);
        }
      }
      status.textContent = down
        ? `Relay ${[...off].map((i) => i + 1).join(", ")} ${off.size > 1 ? "are" : "is"} off. The community loses mobile service, even though its own site still works and the coverage map still shows it as covered.`
        : "Every relay on this chain is working. The community has service.";
    }
    $("chain-reset").addEventListener("click", () => { off.clear(); draw(); });
    phone.addEventListener("change", draw);
    draw();
  })();

  $("hero-stats").append(
    stat(`${c.with_ge1_spof} of ${c.radio_chain_places}`, `larger places on a radio chain depend on at least one single-path relay (about ${about(c.people_ge1_spof)} people)`, "orange"),
    stat(`${c.ge1_spof_inside_predicted_4g} of ${c.with_ge1_spof}`, "of those sit inside Telstra's predicted 4G coverage", "blue"),
    stat(`${inMnhp} of ${r.spof_relays}`, "single-path relays are in the Mobile Network Hardening Program, so their battery hours are not public"),
    stat(`${rep.jan_bands[">14 d"]} of ${rep.radio_chain_places}`, "could wait more than 14 days for a repair in January, against under 3 days in July", "orange"),
    stat(`${fb.radio_chain_with_other_carrier} of ${rep.radio_chain_places}`, "has a second carrier's site within 10 km that could carry a 000 call"),
  );

  // ---- Sandbox: a made-up network -------------------------------------------
  (function sandbox() {
    const N = {
      F1: { x: 50, y: 205, t: "fibre", name: "Fibre town A" },
      F2: { x: 668, y: 345, t: "fibre", name: "Fibre town B" },
      R1: { x: 150, y: 115, t: "relay" }, R2: { x: 260, y: 75, t: "relay" }, R3: { x: 370, y: 75, t: "relay" },
      R4: { x: 360, y: 160, t: "relay" }, R5: { x: 150, y: 300, t: "relay" }, R6: { x: 440, y: 345, t: "relay" },
      R7: { x: 560, y: 240, t: "relay" }, R8: { x: 590, y: 70, t: "relay" },
      C1: { x: 480, y: 75, t: "comm", name: "Community 1" }, C2: { x: 470, y: 160, t: "comm", name: "Community 2" },
      C3: { x: 295, y: 345, t: "comm", name: "Community 3" }, C4: { x: 665, y: 205, t: "comm", name: "Community 4" },
      C5: { x: 670, y: 110, t: "comm", name: "Community 5" },
    };
    const E = [["F1", "R1"], ["R1", "R2"], ["R2", "R3"], ["R3", "C1"], ["R2", "R4"], ["R4", "C2"],
      ["F1", "R5"], ["R5", "C3"], ["C3", "R6"], ["R6", "F2"], ["R6", "R7"], ["R7", "C4"], ["R8", "C5"]];
    const EXTRA = ["C1", "R7"];
    const off = new Set();
    let extra = false, showSpof = true;
    const svg = $("sandbox"), list = $("sb-list");

    const edges = () => (extra ? E.concat([EXTRA]) : E);
    function reach(removed) {
      const adj = {};
      for (const [u, v] of edges()) { (adj[u] ||= []).push(v); (adj[v] ||= []).push(u); }
      const seen = new Set(), q = Object.keys(N).filter((k) => N[k].t === "fibre" && !removed.has(k));
      q.forEach((k) => seen.add(k));
      while (q.length) {
        const u = q.shift();
        for (const v of adj[u] || []) if (!seen.has(v) && !removed.has(v)) { seen.add(v); q.push(v); }
      }
      return seen;
    }
    // A relay is single-path for a community if switching it off (as well as whatever is already off)
    // cuts the community from every fibre town. Same answer as the dominator tree the Python code uses.
    function analyse() {
      const now = reach(off), base = reach(new Set());
      const relays = Object.keys(N).filter((k) => N[k].t === "relay" && !off.has(k));
      const out = {};
      for (const k of Object.keys(N).filter((k) => N[k].t === "comm")) {
        const island = !base.has(k);
        const connected = now.has(k);
        const spofs = connected ? relays.filter((rl) => !reach(new Set([...off, rl])).has(k)) : [];
        const causes = !connected && !island ? [...off].filter((rl) => reach(new Set([...off].filter((x) => x !== rl))).has(k)) : [];
        out[k] = { island, connected, spofs, causes };
      }
      return out;
    }
    function draw() {
      const res = analyse();
      const spofSet = new Set(Object.values(res).flatMap((x) => x.spofs));
      const live = reach(off);
      svg.replaceChildren();
      for (const [u, v] of edges()) {
        const on = live.has(u) && live.has(v);
        const isExtra = extra && u === EXTRA[0] && v === EXTRA[1];
        svg.append(el("line", { x1: N[u].x, y1: N[u].y, x2: N[v].x, y2: N[v].y, stroke: on ? "var(--ink)" : "var(--line)",
          "stroke-width": 2.5, "stroke-dasharray": isExtra ? "7 5" : null }));
      }
      for (const [k, n] of Object.entries(N)) {
        if (n.t === "fibre") {
          svg.append(el("rect", { x: n.x - 9, y: n.y - 22, width: 18, height: 44, fill: "var(--blue)" }));
          svg.append(el("text", { x: n.x, y: n.y + 38, "text-anchor": "middle", "font-weight": 700 }, n.name));
        } else if (n.t === "relay") {
          const isOff = off.has(k), isSpof = showSpof && spofSet.has(k);
          const g = el("g", { "data-k": k, class: "node", tabindex: 0, role: "button", "aria-pressed": String(isOff),
            "aria-label": `Relay ${k.slice(1)}, ${isOff ? "switched off" : isSpof ? "single-path relay" : "working"}` });
          g.append(el("title", {}, `Relay ${k.slice(1)}: click to switch ${isOff ? "on" : "off"}`));
          g.append(el("circle", { cx: n.x, cy: n.y, r: 13, fill: isOff ? "var(--line)" : isSpof ? "var(--orange)" : "var(--panel)",
            stroke: isOff ? "var(--faint)" : isSpof ? "var(--orange)" : "var(--ink)", "stroke-width": 2.5, "stroke-dasharray": isOff ? "4 3" : null }));
          g.append(el("text", { x: n.x, y: n.y + 4, "text-anchor": "middle", "font-size": 11, "font-weight": 700,
            fill: isSpof && !isOff ? "#1a1a1a" : "var(--ink)" }, k));
          const toggle = () => { off.has(k) ? off.delete(k) : off.add(k); draw(); const f = $("sandbox").querySelector(`[data-k="${k}"]`); if (f) f.focus(); };
          g.addEventListener("click", toggle);
          g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
          svg.append(g);
        } else {
          const s = res[k], cut = !s.connected;
          svg.append(el("circle", { cx: n.x, cy: n.y, r: 16, fill: cut ? "var(--orange-soft)" : "var(--blue-soft)",
            stroke: cut ? "var(--orange)" : "var(--blue)", "stroke-width": 2, "stroke-dasharray": "5 4" }));
          svg.append(el("circle", { cx: n.x, cy: n.y, r: 4.5, fill: cut ? "var(--orange)" : "var(--ink)" }));
          svg.append(el("text", { x: n.x, y: n.y + 32, "text-anchor": "middle" }, n.name));
        }
      }
      // Pulses travel each connected community's shortest live path from a fibre town.
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const adj = {};
        for (const [u, v] of edges()) { if (off.has(u) || off.has(v)) continue; (adj[u] ||= []).push(v); (adj[v] ||= []).push(u); }
        const parent = {}, q = Object.keys(N).filter((k) => N[k].t === "fibre");
        q.forEach((k) => (parent[k] = null));
        while (q.length) { const u = q.shift(); for (const v of adj[u] || []) if (!(v in parent)) { parent[v] = u; q.push(v); } }
        Object.keys(N).filter((k) => N[k].t === "comm" && k in parent).forEach((k, idx) => {
          const pts = []; for (let x = k; x != null; x = parent[x]) pts.unshift([N[x].x, N[x].y]);
          if (pts.length < 2) return;
          const d = "M" + pts.map((pt) => pt.join(",")).join("L");
          const dot = el("circle", { r: 4, fill: "var(--blue)", "pointer-events": "none" });
          dot.append(el("animateMotion", { dur: (0.55 * pts.length).toFixed(2) + "s", begin: (idx * 0.3).toFixed(2) + "s", repeatCount: "indefinite", path: d }));
          svg.append(dot);
        });
      }
      list.replaceChildren(...Object.entries(res).map(([k, s]) => {
        let msg;
        if (s.island) msg = [el("span", { class: "st" }, "Radio island. "), "Licensed links, but none reach fibre. Probably satellite or a link the register cannot show."];
        else if (!s.connected) msg = [el("span", { class: "st cut" }, "Cut off. "), s.causes.length ? `Relay ${s.causes.map((x) => x.slice(1)).join(" or ")} is off.` : "More than one relay on its paths is off."];
        else if (!s.spofs.length) msg = [el("span", { class: "st ok" }, "Connected. "), "No weak links: every relay has a way around it."];
        else msg = [el("span", { class: "st ok" }, "Connected. "), `Depends on ${s.spofs.length} weak link${s.spofs.length > 1 ? "s" : ""}: relay ${s.spofs.map((x) => x.slice(1)).join(", ")}.`];
        return el("li", {}, el("strong", {}, N[k].name + ": "), ...msg);
      }));
    }
    $("sb-spof").addEventListener("change", (e) => { showSpof = e.target.checked; draw(); });
    $("sb-link").addEventListener("change", (e) => { extra = e.target.checked; draw(); });
    $("sb-reset").addEventListener("click", () => { off.clear(); extra = false; $("sb-link").checked = false; draw(); });
    draw();
  })();

  // ---- Findings -----------------------------------------------------------------
  (function classes() {
    const k = D.larger_classes;
    const rows = [["At a fibre town", k["at-anchor"]], ["On a radio chain", k["radio-chain"], true],
      ["Radio island", k["radio-island"]], ["No licensed radio site within 10 km", k["no-radio-site"]]];
    const max = Math.max(...rows.map((x) => x[1]));
    $("classes-chart").append(...rows.map(([t, v, hl]) => el("div", { class: "row" }, el("span", {}, t),
      el("div", { class: "bar" + (hl ? " hl" : ""), style: `width:${(100 * v) / max}%` }), el("span", { class: "val" }, v))));
    // the same 116 places, one square each, weak-link places first
    const spof = c.with_ge1_spof, chain = k["radio-chain"];
    const cells = [["w-spof", spof], ["w-chain", chain - spof], ["w-fibre", k["at-anchor"]],
      ["w-island", k["radio-island"]], ["w-none", k["no-radio-site"]]];
    const w = $("classes-waffle");
    w.setAttribute("aria-label", `${spof} of the ${rows.reduce((a, r) => a + r[1], 0)} larger places are on a radio chain with a weak link; ` +
      `${chain - spof} more are on a radio chain without one.`);
    w.append(...cells.flatMap(([cls, n]) => Array.from({ length: n }, () => el("i", { class: cls }))));
  })();

  $("chain-facts").append(
    fact(`${c.with_ge1_spof}`, `depend on at least one single-path relay, about ${about(c.people_ge1_spof)} of the ${about(c.people_on_radio_chains, 1000)} people on radio chains`, "orange"),
    fact(`${c.with_ge3_spof}`, "depend on three or more"),
    fact(`${c.hops_median}`, `radio links on the median chain; the longest has ${c.hops_max}`),
    fact(`${c.ge1_spof_inside_predicted_4g} of ${c.with_ge1_spof}`, "of the places with a single-path relay sit inside Telstra's predicted 4G coverage", "blue"),
    fact(`${D.fibre_what_if.radio_chain_single_fibre_town}`, "reach only one fibre town over licensed radio, so a fibre break there cuts them too"),
  );

  (function sensitivity() {
    let ak = 10, ek = 10;
    const out = $("sens-out");
    const show = () => {
      const t = D.sensitivity.table.find((x) => x.anchor_km === ak && x.end_km === ek);
      const main = ak === 10 && ek === 10;
      out.replaceChildren(
        stat(t.radio_chain, "larger places on a radio chain"),
        stat(t.ge1_spof, "with a single-path relay", "orange"),
        stat(`${Math.round((100 * t.ge1_spof) / t.radio_chain)}%`, "share with a single-path relay"),
        stat(t.ge3_spof, "with three or more"),
        el("p", { class: "note", style: "grid-column:1/-1;margin:0" }, (main ? "Main run. " : "") +
          `Across all nine runs the share stays between ${Math.round(100 * D.sensitivity.ge1_spof_share_range[0])}% and ${Math.round(100 * D.sensitivity.ge1_spof_share_range[1])}%.`),
      );
    };
    const opts = [[5, "5 km"], [10, "10 km"], [15, "15 km"]];
    seg($("sens-anchor"), "Fibre-town radius", opts, 10, (v) => { ak = v; show(); });
    seg($("sens-end"), "Serving-site radius", opts, 10, (v) => { ek = v; show(); });
  })();

  $("accc-out").append(
    fact(`${a.ge1_spof_end_is_mobile_site} of ${a.ge1_spof_places}`, `places with a single-path relay have a chain that ends at a site the ACCC lists as a Telstra mobile site (within ${a.match_km} km). The other ${a.ge1_spof_places - a.ge1_spof_end_is_mobile_site} end at least ${Math.floor(a.unmatched_min_km)} km from one, so their result is less certain.`, "blue"),
    fact(`${a.telstra_sites_on_radio_graph} of ${a.telstra_mobile_sites_2026}`, `Telstra mobile sites in the NT (${Math.round(100 * a.share_on_radio_graph)}%) sit on the licensed radio network. The rest run on fibre, satellite or links the register does not show. Underlink covers the licensed radio part only.`),
  );

  (function replay() {
    let radius = 100, gale = false;
    const host = $("replay-chart");
    const events = [...new Set(D.replay.variants.map((v) => v.event))];
    const maxAll = Math.max(...D.replay.variants.map((v) => v.exposed));
    const show = () => {
      const rows = events.map((e) => D.replay.variants.find((v) => v.event === e && v.radius_km === radius && v.gale_only === gale));
      const small = window.matchMedia("(max-width: 720px)").matches;   // phones: narrower drawing, so text stays readable
      const W = small ? 330 : 520, left = small ? 92 : 100, bh = 22, gap = 12, H = rows.length * (bh + gap) + 34;
      const x = (v) => left + ((W - left - 20) * v) / maxAll;
      const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Cyclone replay results" });
      for (let t = 0; t <= maxAll; t++) {
        svg.append(el("line", { x1: x(t), y1: 0, x2: x(t), y2: H - 26, stroke: "var(--line)" }));
        svg.append(el("text", { x: x(t), y: H - 10, "text-anchor": "middle", fill: "var(--muted)" }, t));
      }
      rows.forEach((v, i) => {
        const y = i * (bh + gap) + 4, local = v.exposed - v.upstream_only;
        svg.append(el("text", { x: left - 8, y: y + 15, "text-anchor": "end" }, v.event));
        svg.append(el("rect", { x: x(0), y, width: x(local) - x(0), height: bh, fill: "var(--dark)" }));
        svg.append(el("rect", { x: x(local), y, width: x(v.exposed) - x(local), height: bh, fill: "var(--orange)" }));
      });
      const tot = rows.reduce((s, v) => s + v.exposed, 0), up = rows.reduce((s, v) => s + v.upstream_only, 0);
      host.replaceChildren(svg, el("p", { class: "note" }, `${tot} cases of a larger radio-chain place losing its path; ${up} of them upstream-only (the storm missed the place and its own site).`));
    };
    window.matchMedia("(max-width: 720px)").addEventListener("change", () => show());
    seg($("rp-radius"), "Distance", [[50, "50 km"], [100, "100 km"], [150, "150 km"]], 100, (v) => { radius = v; show(); });
    seg($("rp-part"), "Track", [[false, "Whole track"], [true, "Gale-strength part"]], false, (v) => { gale = v; show(); });
  })();

  $("relay-facts").append(
    fact(`${inMnhp}`, "are in the Mobile Network Hardening Program", "orange"),
    fact(`${r.power_classes.P4_depot_within_150km}`, "are within 150 km of a portable-generator depot listed in that program"),
    fact(`${r.power_classes.P0_unknown}`, "have no public source naming any backup power"),
    fact(`${r.far_from_sealed_road}`, "are more than 10 km from a sealed road"),
    fact(`${r.ge5_cyclones_100km}`, "had five or more cyclone tracks pass within 100 km, 1980 to 2026"),
    fact(`${r.on_aboriginal_land_trust}`, "sit on Aboriginal Land Trust land, where new works need a section 19 lease"),
  );

  (function regions() {
    const cols = [["at-anchor", "At a fibre town"], ["radio-chain", "Radio chain"], ["radio-island", "Radio island"], ["no-radio-site", "No licensed radio site"]];
    const t = $("regions");
    t.append(el("thead", {}, el("tr", {}, el("th", {}, "Land council region"), ...cols.map(([, h]) => el("th", { class: "num" }, h)))));
    t.append(el("tbody", {}, ...Object.entries(D.regions).map(([lc, row]) =>
      el("tr", {}, el("td", {}, lc), ...cols.map(([k]) => el("td", { class: "num" }, String(row[k])))))));
  })();

  // ---- Repair -------------------------------------------------------------------
  (function repair() {
    const n = rep.radio_chain_places;
    const bar = (month, parts) => el("div", { class: "band-row" }, el("div", { class: "mo" }, month),
      el("div", { class: "stack", role: "img", "aria-label": `${month}: ` + parts.map(([t, v]) => `${t} ${v}`).join(", ") },
        ...parts.filter(([, v]) => v).map(([t, v, cls]) => el("span", { class: cls, style: `width:${(100 * v) / n}%`, title: `${t}: ${v}` }, `${t}: ${v}`))));
    $("repair-bands").append(
      bar("July (dry)", [["Under 1 day", rep.jul_bands["<1 d"] || 0, "b-fast"], ["1 to 3 days", rep.jul_bands["1-3 d"] || 0, "b-mid"]]),
      bar("January (wet)", [["Under 1 day", rep.jan_bands["<1 d"] || 0, "b-fast"], ["Over 14 days", rep.jan_bands[">14 d"] || 0, "b-slow"]]),
    );
    $("repair-note").textContent = `The median drive from a crew base is about ${Math.round(rep.median_travel_hours)} hours. ` +
      `${rep.jul_fast_and_jan_slow} places that take under a day in July take over 14 days in January. ` +
      `For ${rep.jan_slow_set_by_spof_relay} of the slow ones, the site that sets the delay is a single-path relay, not the place's own site.`;
    let w = 30, km = 10;
    const out = $("rep-out");
    const show = () => {
      const s = rep.sweep.find((x) => x.w_wet === w && x.sealed_km === km);
      out.replaceChildren(el("strong", {}, String(s.gt14d)), ` of ${n} places could wait more than 14 days in January; the median January wait is `,
        el("strong", {}, `${Math.round(s.jan_median_days)} days`), ".",
        (w === 30 && km === 10) ? el("span", { class: "note" }, " (main run)") : null,
        el("span", { class: "note", style: "display:block" }, "The delay changes how long the wait is. Which places wait depends on road distance."));
    };
    seg($("rep-wet"), "Delay", [[14, "14 days"], [30, "30 days"], [60, "60 days"]], 30, (v) => { w = v; show(); });
    seg($("rep-km"), "Distance", [[5, "5 km"], [10, "10 km"], [20, "20 km"]], 10, (v) => { km = v; show(); });
  })();

  // ---- What still works ------------------------------------------------------------
  $("works-stats").append(
    stat(`${fb.radio_chain_with_other_carrier} of ${rep.radio_chain_places}`, "radio-chain places have another carrier's site within 10 km. In the other 22 a mobile 000 call has no second network to use.", "orange"),
    stat(`${fb.radio_chain_with_independent_fallback} of ${rep.radio_chain_places}`, "have a satellite Wi-Fi phone or a Sky Muster site within 3 km", "blue"),
    stat(`${fb.radio_chain_with_payphone_3km} of ${rep.radio_chain_places}`, "have a payphone within 3 km, but no public source says which payphones use satellite and which share the tower's path"),
  );
  $("t0-text").textContent = D.card.triple_zero;

  // ---- Community card -----------------------------------------------------------------
  (function card() {
    const cls = { works: "works", degraded: "degraded", "not available": "na", "ask locally": "ask" };
    const sym = { works: "✓", degraded: "◐", "not available": "✕", "ask locally": "?" };
    const t = $("card-grid");
    t.append(el("thead", {}, el("tr", {}, el("th", {}, ""), ...D.card.scenarios.map((s) => el("th", {}, s.label)))));
    t.append(el("tbody", {}, ...D.card.services.map((s) => el("tr", {}, el("td", { class: "svc" }, s.label),
      ...s.cells.map((x) => el("td", { class: "cell " + cls[x.status] },
        el("span", { class: "sym", "aria-hidden": "true" }, sym[x.status]), x.word.toUpperCase()))))));
    $("card-t0").textContent = D.card.triple_zero;
    $("card-print").addEventListener("click", () => window.print());
  })();

  // ---- Government measures ------------------------------------------------------------
  (function kpi() {
    // the same six measures as Appendix F, written by scripts/export_web_data.py from app_data.kpis()
    const rows = D.kpis.map((k) => [k.rec, k.title, k.start, k.target, k.owner]);
    const t = $("kpi");
    t.append(el("thead", {}, el("tr", {}, ...["Recommendation", "Measure", "Starting value", "Target", "Owner"].map((h) => el("th", {}, h)))));
    t.append(el("tbody", {}, ...rows.map((row) => el("tr", {}, ...row.map((x, i) => el("td", i === 2 ? { style: "font-weight:700" } : {}, x))))));
  })();

  // ---- Sources ---------------------------------------------------------------------------
  $("sources").append(...D.datasets.map((s) => el("li", {}, s.organiser ? "★ " : "",
    el("a", { href: s.url, rel: "noopener" }, s.name), el("br"), el("span", { class: "pub" }, `${s.publisher} · ${s.licence}`))));
  // ---- Logo: back to the top without leaving "#top" in the address bar ----------------------
  document.querySelector(".brand").addEventListener("click", (e) => {
    e.preventDefault();
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" });
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  });
  // ---- Top navigation: highlight the section in view ------------------------------------
  (function navSpy() {
    const links = [...document.querySelectorAll(".nav a")];
    const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    if (!("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        links.forEach((a) => a.classList.remove("active"));
        const a = byId.get(e.target.id);
        if (a) {
          a.classList.add("active");
          // on phones the menu scrolls sideways: bring the active link into view
          const nav = a.parentElement;
          if (nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: a.offsetLeft - 8, behavior: "smooth" });
        }
      }
    }, { rootMargin: "-45% 0px -50% 0px" });
    byId.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
  })();
  // ---- "Show technical detail" switch (as in Pyrantis): plain view first, detail on demand.
  // Hiding or showing panels changes the page height, so keep whatever is at the top of the
  // screen in the same place instead of letting the page jump.
  (function detailSwitch() {
    const box = $("detail-toggle");
    const header = document.querySelector(".topbar");
    function anchor() {
      const top = header.getBoundingClientRect().bottom + 8;
      const blocks = document.querySelectorAll("main h2, main h3, main p, main .panel, main .stats, main figure, main table");
      for (const el of blocks) {
        if (el.closest(".detail")) continue;
        const r = el.getBoundingClientRect();
        if (r.bottom > top) return { el, y: r.top };
      }
      return null;
    }
    const apply = (keepPlace) => {
      const a = keepPlace ? anchor() : null;
      document.body.classList.toggle("show-numbers", box.checked);
      if (a) window.scrollBy({ top: a.el.getBoundingClientRect().top - a.y, behavior: "instant" });
      try { localStorage.setItem("underlink-detail", box.checked ? "1" : "0"); } catch (e) {}
    };
    try { box.checked = localStorage.getItem("underlink-detail") === "1"; } catch (e) {}
    box.addEventListener("change", () => apply(true));
    apply(false);
  })();
  // ---- Tables: give each cell its column name, so phones can show rows as stacked cards ----
  document.querySelectorAll("table.data").forEach((t) => {
    const heads = [...t.querySelectorAll("thead th")].map((h) => h.textContent.trim());
    t.querySelectorAll("tbody tr").forEach((tr) => [...tr.children].forEach((td, k) => { if (heads[k]) td.dataset.label = heads[k]; }));
  });
  // ---- Off-grid: where a pilot could start (numbers from numbers.json) --------------------
  (function ogFacts() {
    const box = $("og-facts");
    if (!box) return;
    box.append(
      fact(`${c.with_ge1_spof} of ${c.radio_chain_places}`, "radio-chain places would lose service if one of their weak links failed. A satellite second path at their tower (layer 1) could keep them on air, if the tower has power", "orange"),
      fact(`${D.layers.flagged_and_wet_slow} of ${D.layers.flagged_places}`, "of those also wait more than two weeks for a wet-season repair. There, layer 1 could save weeks without service", "orange"),
      fact(`${D.layers.flagged_with_stand_3km} of ${D.layers.flagged_places}`, "have a STAND satellite site (evacuation centre or fire depot) within 3 km: layer 2 is already there", "blue"),
      fact(`${fb.radio_chain_with_independent_fallback} of ${rep.radio_chain_places}`, "already have a satellite Wi-Fi phone or a Sky Muster service within 3 km, where a layer 3 pilot could start", "blue"),
      fact(`${fb.radio_chain_with_other_carrier} of ${rep.radio_chain_places}`, "has another company's mobile site within 10 km, so 000 by mobile mostly depends on the one chain"),
    );
  })();
})();
