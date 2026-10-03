// Hero: the NT coastline (NT_COAST, ABS) and highways (NT_BASE), the fibre backbone along the Stuart Highway, and
// six made-up radio chains. Signal pulses run from fibre to each community; every few seconds one
// chain's weak link fails and the community after it goes dark. No real relay or community
// locations are drawn: the chains are illustrative, and Darwin is the only place named.
(function () {
  "use strict";
  const host = document.getElementById("hero-map");
  if (!host || !window.NT_BASE) return;
  const NS = "http://www.w3.org/2000/svg";
  const W = 480, H = 600, LON0 = 128.55, LAT0 = -10.75, S = 36.5, KX = Math.cos((18.5 * Math.PI) / 180);
  const OX = (W - (138.45 - LON0) * KX * S) / 2;
  const P = ([lon, lat]) => [OX + (lon - LON0) * KX * S, (LAT0 - lat) * S + 6];
  const d = (pts) => pts.map((p, i) => (i ? "L" : "M") + P(p).map((v) => v.toFixed(1)).join(" ")).join("");
  const mk = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };

  const svg = mk("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "xMidYMid meet", "aria-hidden": "true", focusable: "false" });
  const defs = mk("defs", {}, svg);
  defs.innerHTML = `
    <linearGradient id="hm-land" x1="0" y1="0" x2="0.6" y2="1"><stop offset="0" stop-color="#2E5A97"/><stop offset="1" stop-color="#1F4377"/></linearGradient>
    <pattern id="hm-dots" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.8" fill="#9CC3F5" fill-opacity="0.16"/></pattern>
    <filter id="hm-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="hm-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
    <clipPath id="hm-clip"></clipPath>`;

  // graticule
  const grat = mk("g", { stroke: "#FFFFFF", "stroke-opacity": "0.05", "stroke-width": "1" }, svg);
  for (let lon = 129; lon <= 138; lon += 3) mk("path", { d: d([[lon, -10.5], [lon, -26.6]]) }, grat);
  for (let lat = -12; lat >= -26; lat -= 3) mk("path", { d: d([[128.4, lat], [138.6, lat]]) }, grat);

  // land: soft shadow, fill, dot texture, coastline
  const land = (window.NT_COAST || NT_BASE.outline).map((ring) => d(ring) + "Z").join("");
  defs.querySelector("#hm-clip").appendChild(mk("path", { d: land }));
  mk("path", { d: land, fill: "#000814", "fill-opacity": "0.45", filter: "url(#hm-soft)", transform: "translate(0 8)" }, svg);
  mk("path", { d: land, fill: "url(#hm-land)" }, svg);
  mk("rect", { width: W, height: H, fill: "url(#hm-dots)", "clip-path": "url(#hm-clip)" }, svg);
  mk("path", { d: NT_BASE.highways.map(d).join(""), fill: "none", stroke: "#BFD6F5", "stroke-opacity": "0.14", "stroke-width": "0.8", "clip-path": "url(#hm-clip)" }, svg);
  mk("path", { d: land, fill: "none", stroke: "#CFE1F8", "stroke-opacity": "0.55", "stroke-width": "1", "stroke-linejoin": "round" }, svg);

  // fibre backbone along the Stuart Highway (public route; fibre towns are not named except Darwin)
  const DARWIN = [130.84, -12.46], KATH = [132.27, -14.47], TENN = [134.19, -19.65], ALICE = [133.88, -23.7];
  const spine = [DARWIN, [131.35, -13.2], KATH, [133.05, -15.95], [133.4, -17.6], TENN, [134.05, -21.4], ALICE, [133.6, -24.9], [133.2, -26.0]];
  mk("path", { d: d(spine), fill: "none", stroke: "#6FAEF5", "stroke-opacity": "0.35", "stroke-width": "6", "stroke-linecap": "round", filter: "url(#hm-soft)" }, svg);
  mk("path", { d: d(spine), fill: "none", stroke: "#8EC0FA", "stroke-width": "2.2", "stroke-linecap": "round", "stroke-linejoin": "round" }, svg);
  mk("path", { class: "hm-flow", d: d(spine), fill: "none", stroke: "#FFFFFF", "stroke-width": "2.2", "stroke-linecap": "round", "stroke-dasharray": "3 26" }, svg);

  // illustrative radio chains: fibre town, relays, community. `weak` is the index of the relay that fails.
  const CHAINS = [
    { pts: [DARWIN, [131.9, -12.75], [132.95, -12.55], [134.05, -12.45], [135.35, -12.2]], weak: 2 },
    { pts: [KATH, [133.35, -14.2], [134.4, -14.25], [135.5, -14.6], [136.1, -15.35]], weak: null },
    { pts: [KATH, [131.35, -15.35], [130.45, -16.05], [129.65, -16.8]], weak: 1 },
    { pts: [TENN, [135.35, -19.25], [136.35, -18.85], [137.35, -18.55]], weak: 1 },
    { pts: [ALICE, [132.75, -23.25], [131.6, -22.95], [130.5, -22.6], [129.55, -22.25]], weak: 2 },
    { pts: [ALICE, [135.05, -23.15], [136.2, -22.75], [137.25, -22.45]], weak: null },
  ];
  const links = mk("g", { fill: "none", "stroke-linecap": "round" }, svg);
  const nodes = mk("g", {}, svg);
  const parts = mk("g", { filter: "url(#hm-glow)" }, svg);
  CHAINS.forEach((c) => {
    c.xy = c.pts.map(P);
    c.seg = [];
    c.len = [0];
    for (let i = 1; i < c.xy.length; i++) {
      const [x0, y0] = c.xy[i - 1], [x1, y1] = c.xy[i];
      const mx = (x0 + x1) / 2, my = (y0 + y1) / 2 - Math.hypot(x1 - x0, y1 - y0) * 0.18;   // a slight arc per hop
      c.seg.push(mk("path", { class: "hm-hop", d: `M${x0} ${y0}Q${mx} ${my} ${x1} ${y1}`, stroke: "#DCEBFF", "stroke-opacity": "0.5", "stroke-width": "1.3" }, links));
    }
    c.seg.forEach((s) => { c.len.push(c.len[c.len.length - 1] + s.getTotalLength()); });
    c.relays = c.xy.slice(1, -1).map(([x, y], i) => {
      const g = mk("g", { class: "hm-relay" + (i + 1 === c.weak ? " hm-weak" : ""), transform: `translate(${x} ${y})` }, nodes);
      if (i + 1 === c.weak) mk("circle", { class: "hm-ripple", r: "4", fill: "none", stroke: "#F28B5B", "stroke-width": "1.5" }, g);
      mk("circle", { class: "hm-dot", r: i + 1 === c.weak ? "3.6" : "2.6" }, g);
      return g;
    });
    const [cx, cy] = c.xy[c.xy.length - 1];
    c.comm = mk("g", { class: "hm-comm", transform: `translate(${cx} ${cy})` }, nodes);
    mk("circle", { class: "hm-halo", r: "9" }, c.comm);
    mk("circle", { class: "hm-core", r: "4.2" }, c.comm);
    c.dots = Array.from({ length: 3 }, () => mk("circle", { r: "1.9", fill: "#FFFFFF" }, parts));
  });
  // fibre towns on the chains: rings on the backbone
  [DARWIN, KATH, TENN, ALICE].forEach((t) => {
    const [x, y] = P(t);
    mk("circle", { cx: x, cy: y, r: "6", fill: "#0E1E38", stroke: "#8EC0FA", "stroke-width": "2" }, nodes);
    mk("circle", { cx: x, cy: y, r: "2.2", fill: "#FFFFFF" }, nodes);
  });
  const [dx, dy] = P(DARWIN);
  mk("text", { x: dx + 10, y: dy - 8, class: "hm-label" }, nodes).textContent = "Darwin";
  host.prepend(svg);

  // ---- animation ----------------------------------------------------------------------------
  const status = document.getElementById("hero-map-status");
  const failing = CHAINS.filter((c) => c.weak);
  const CYCLE = 9000, CUT_FROM = 4200, CUT_TO = 7600, SPEED = 0.055;   // ms; px per ms
  let cut = null, t0 = performance.now(), run = true, raf = 0;

  function setCut(c) {
    if (cut === c) return;
    if (cut) {
      cut.seg.forEach((s) => s.classList.remove("hm-off"));
      cut.relays[cut.weak - 1].classList.remove("hm-down");
      cut.comm.classList.remove("hm-dark");
    }
    cut = c;
    if (c) {
      c.seg.forEach((s, i) => { if (i >= c.weak) s.classList.add("hm-off"); });
      c.relays[c.weak - 1].classList.add("hm-down");
      c.comm.classList.add("hm-dark");
    }
    if (status) {
      status.classList.toggle("is-down", !!c);
      status.lastChild.textContent = c ? `Weak link down: ${CHAINS.length - 1} of ${CHAINS.length}`
        : `${CHAINS.length} of ${CHAINS.length} connected`;
    }
  }

  function at(c, u) {
    let i = 1;
    while (i < c.len.length - 1 && u > c.len[i]) i++;
    const s = c.seg[i - 1], p = s.getPointAtLength(u - c.len[i - 1]);
    return [p.x, p.y];
  }

  function frame(now) {
    const t = now - t0, k = Math.floor(t / CYCLE), ph = t % CYCLE;
    setCut(ph > CUT_FROM && ph < CUT_TO ? failing[k % failing.length] : null);
    CHAINS.forEach((c, ci) => {
      const L = c.len[c.len.length - 1], stop = c === cut ? c.len[c.weak] : L;
      c.dots.forEach((dot, j) => {
        const u = ((t * SPEED + ci * 37 + (j * L) / c.dots.length) % L);
        if (u > stop) { dot.setAttribute("opacity", "0"); return; }
        const [x, y] = at(c, u);
        dot.setAttribute("cx", x.toFixed(1)); dot.setAttribute("cy", y.toFixed(1));
        const edge = Math.min(u / 14, (stop - u) / 14, 1);   // fade in at the fibre end, out at the community
        dot.setAttribute("opacity", Math.max(0, edge).toFixed(2));
      });
    });
    if (run) raf = requestAnimationFrame(frame);
  }

  const still = window.matchMedia("(prefers-reduced-motion: reduce)");
  function start() { if (still.matches || raf) return; run = true; raf = requestAnimationFrame(frame); }
  function stop() { run = false; cancelAnimationFrame(raf); raf = 0; }
  setCut(null);
  CHAINS.forEach((c) => c.dots.forEach((dot) => dot.setAttribute("opacity", "0")));
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => (e.isIntersecting && !document.hidden ? start() : stop())).observe(host);
  } else start();
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
  still.addEventListener?.("change", () => (still.matches ? stop() : start()));
})();
