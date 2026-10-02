// How Underlink works, as an animation: data moves from the public sources through each step to
// the three outputs. Left to right on wide screens, top to bottom on phones. The numbered list
// under it says the same in words (and is what screen readers use).
(function () {
  "use strict";
  const host = document.getElementById("pipeline-anim");
  if (!host) return;
  const D = window.UNDERLINK || {};
  const n = D.network || {};
  const NS = "http://www.w3.org/2000/svg";
  const el = (t, a = {}, txt) => { const e = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (txt != null) e.textContent = txt; return e; };
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const phone = window.matchMedia("(max-width: 720px)");
  const STAGES = [
    ["18 public sources", "ACMA, ACCC, NTG, BoM, Geoscape"],
    ["Prepare", "hash site ids, round places"],
    ["Build the network", `${n.V || 358} sites, ${n.E || 313} links`],
    ["Find weak links", "dominator tree to fibre"],
    ["Four checks", "cyclones, power, repair, fallbacks"],
    ["Three outputs", "card, government, carriers"],
  ];
  const COLORS = ["#16325C", "#2B4F80", "#1E6FD9", "#E4602E", "#7B61D9", "#0EA5C6"];

  function draw() {
    const v = phone.matches;
    const W = v ? 340 : 1080, H = v ? 640 : 170, step = v ? 104 : 178;
    const pos = (i) => (v ? [70, 46 + i * step] : [110 + i * step, 70]);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "How Underlink works, step by step", "font-family": "Arial, Helvetica, sans-serif" });
    const d = "M" + STAGES.map((_, i) => pos(i).join(",")).join("L");
    svg.append(el("path", { d, fill: "none", stroke: "#D6DEE8", "stroke-width": 4, "stroke-linecap": "round" }));
    STAGES.forEach(([t, s], i) => {
      const [x, y] = pos(i);
      const g = el("g", { class: "pl-stage", style: `--i:${i}` });
      g.append(el("circle", { cx: x, cy: y, r: 22, fill: "#fff", stroke: COLORS[i], "stroke-width": 3 }));
      g.append(el("text", { x, y: y + 5, "text-anchor": "middle", "font-size": 14, "font-weight": 700, fill: COLORS[i] }, String(i + 1)));
      const tx = v ? x + 38 : x, ty = v ? y - 4 : y + 44, anchor = v ? "start" : "middle";
      g.append(el("text", { x: tx, y: ty, "text-anchor": anchor, "font-size": 14, "font-weight": 700, fill: "#16325C" }, t));
      g.append(el("text", { x: tx, y: ty + 17, "text-anchor": anchor, "font-size": 12, fill: "#4F5E70" }, s));
      svg.append(g);
    });
    if (!reduce.matches) {
      const dur = 6;
      for (let k = 0; k < 4; k++) {
        const dot = el("circle", { r: 5, fill: "#E4602E" });
        dot.append(el("animateMotion", { dur: dur + "s", begin: (k * dur / 4) + "s", repeatCount: "indefinite", path: d }));
        svg.append(dot);
      }
    }
    host.replaceChildren(svg);
  }
  phone.addEventListener("change", draw);
  draw();
})();
