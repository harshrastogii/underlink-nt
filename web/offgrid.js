// "When the tower is down": an animated walk through the fallbacks that keep a community talking
// after a weak link fails. Messages are drawn as dots moving along real paths (SVG animateMotion).
// With prefers-reduced-motion the same paths are shown still, as dashed lines.
(function () {
  "use strict";
  const host = document.getElementById("offgrid-scene");
  if (!host) return;
  const NS = "http://www.w3.org/2000/svg";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const el = (t, a = {}, txt) => { const e = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) if (v != null) e.setAttribute(k, v); if (txt != null) e.textContent = txt; return e; };

  // Scene geometry (viewBox 0 0 760 340)
  const TOWN = [52, 176], RELAYS = [[150, 112], [240, 78], [330, 100]], TOWER = [430, 150];
  const CLINIC = [520, 206], STORE = [640, 258], SCHOOL = [702, 190], HILL = [690, 104], SAT = [600, 30];
  const PHONES = [[470, 220], [500, 260], [560, 238], [585, 292], [618, 214], [668, 226], [690, 286], [736, 246]];
  const NODES = { clinic: [CLINIC[0], CLINIC[1] - 26], store: [STORE[0], STORE[1] - 24], school: [SCHOOL[0], SCHOOL[1] - 24], hill: HILL };
  const ROAD_Y = 322, NTES = [505, 316];

  const C = { ink: "#16325C", fibre: "#1E6FD9", weak: "#F6A15E", off: "#C4CDD5", msg: "#E4602E", bt: "#2A78D6", lora: "#7B61D9", sat: "#0EA5C6" };
  const path = (pts) => "M" + pts.map((p) => p.join(",")).join("L");
  const arc = (a, b, lift = 30) => `M${a[0]},${a[1]} Q${(a[0] + b[0]) / 2},${Math.min(a[1], b[1]) - lift} ${b[0]},${b[1]}`;

  const STEPS = [
    { t: "A normal day", d: "Phone traffic runs from the fibre town over a chain of radio relays to the community's tower, and from the tower to every phone in range.", uses: ["Licensed radio chain", "Mobile tower"] },
    { t: "A weak link fails", d: "One relay on the chain has no way around it. When its battery runs flat or a storm takes it down, the tower loses its path. Every phone loses service, although the tower itself works and the coverage map still says covered.", uses: ["What Underlink finds: 18 of 23 radio-chain places"] },
    { t: "Phone to phone, over Bluetooth", d: "Apps such as Bitchat and Columba pass encrypted messages, photos and voice notes from phone to phone, with no tower and no account. Each hop reaches tens of metres, so it works across a camp or a street, not across a town.", uses: ["Bitchat", "Columba", "Bluetooth"] },
    { t: "A community mesh on solar LoRa nodes", d: "Small solar radios on the clinic, store, school and a hill link the whole community, about 3 to 15 km a hop. Meshtastic carries short text and positions. Reticulum apps (Sideband, Columba, MeshChatX) also carry small photos, files and voice messages, slowly. In Australia these radios need no licence at 915 to 928 MHz under the ACMA LIPD class licence. Emergency teams can share positions on the same radios with ATAK and the LANCE plugin.", uses: ["Meshtastic", "Reticulum", "ACMA LIPD class licence", "ATAK + LANCE"] },
    { t: "A bridge out, through satellite", d: "One node at the clinic also has an internet link, such as the clinic's Sky Muster service or a community satellite Wi-Fi hub. Reticulum joins LoRa, Wi-Fi and satellite into one network, so messages from the mesh reach the outside world. A propagation node (LXMF) holds them whenever that link drops.", uses: ["Reticulum bridge", "LXMF store-and-forward", "Sky Muster / satellite Wi-Fi"] },
    { t: "A vehicle carries the rest", d: "When there is no live link at all, a node on a bush bus, mail run or clinic vehicle collects waiting messages as it passes and hands them over in town. Messages wait until a link appears, then move on.", uses: ["LXMF propagation node", "Store and forward"] },
  ];
  let step = 0, playing = !reduce.matches, timer = null;

  function scene() {
    const svg = el("svg", { viewBox: "0 0 760 340", role: "img", "aria-labelledby": "offgrid-title", "font-family": "Arial, Helvetica, sans-serif" });
    svg.append(el("rect", { x: 0, y: 0, width: 760, height: 340, rx: 16, fill: "#F3F7FD" }));
    svg.append(el("path", { d: "M0,150 Q120,40 250,64 T420,130 L420,340 L0,340 Z", fill: "#E3ECF7" }));   // hills
    svg.append(el("ellipse", { cx: 600, cy: 262, rx: 190, ry: 84, fill: "#FFF5EA", stroke: "#F6D3B0", "stroke-dasharray": "5 5" }));   // community
    svg.append(el("line", { x1: 0, y1: ROAD_Y, x2: 760, y2: ROAD_Y, stroke: "#D6DEE8", "stroke-width": 8 }));
    svg.append(el("g", { id: "og-dyn" }));
    // town
    svg.append(el("rect", { x: TOWN[0] - 22, y: TOWN[1] - 30, width: 44, height: 46, rx: 4, fill: C.ink }));
    svg.append(el("rect", { x: TOWN[0] - 4, y: TOWN[1] + 16, width: 8, height: 0, fill: C.ink }));
    svg.append(el("text", { x: TOWN[0], y: TOWN[1] + 36, "text-anchor": "middle", "font-size": 13, "font-weight": 700, fill: C.ink, class: "og-lbl" }, "Fibre town"));
    // satellite
    const sat = el("g", { id: "og-sat", class: "og-dim" });
    sat.append(el("rect", { x: SAT[0] - 9, y: SAT[1] - 9, width: 18, height: 18, rx: 3, fill: C.sat }));
    sat.append(el("rect", { x: SAT[0] - 36, y: SAT[1] - 5, width: 22, height: 10, fill: "#9BD9E8" }));
    sat.append(el("rect", { x: SAT[0] + 14, y: SAT[1] - 5, width: 22, height: 10, fill: "#9BD9E8" }));
    svg.append(sat);
    // chain
    svg.append(el("path", { id: "og-chain", d: path([TOWN, ...RELAYS, TOWER]), fill: "none", stroke: C.fibre, "stroke-width": 3 }));
    RELAYS.forEach((r, i) => svg.append(el("circle", { id: "og-relay" + i, cx: r[0], cy: r[1], r: 12, fill: C.weak, stroke: "#fff", "stroke-width": 2 })));
    // tower
    svg.append(el("path", { d: `M${TOWER[0] - 12},${TOWER[1] + 34} L${TOWER[0]},${TOWER[1] - 8} L${TOWER[0] + 12},${TOWER[1] + 34}`, fill: "none", stroke: C.ink, "stroke-width": 3 }));
    svg.append(el("circle", { id: "og-tower", cx: TOWER[0], cy: TOWER[1] - 10, r: 6, fill: C.fibre }));
    svg.append(el("text", { x: TOWER[0], y: TOWER[1] + 52, "text-anchor": "middle", "font-size": 13, fill: C.ink, class: "og-lbl" }, "Community tower"));
    // buildings
    const bldg = (p, name, dish) => {
      svg.append(el("rect", { x: p[0] - 20, y: p[1] - 16, width: 40, height: 26, rx: 3, fill: "#fff", stroke: C.ink, "stroke-width": 1.5 }));
      svg.append(el("text", { x: p[0], y: p[1] + 26, "text-anchor": "middle", "font-size": 12, fill: C.ink, class: "og-lbl" }, name));
      if (dish) svg.append(el("path", { d: `M${p[0] + 8},${p[1] - 16} q8,-12 16,0`, fill: "none", stroke: C.sat, "stroke-width": 2.5 }));
    };
    bldg(CLINIC, "Clinic", true); bldg(STORE, "Store"); bldg(SCHOOL, "School");
    // LoRa nodes
    Object.entries(NODES).forEach(([k, p]) => {
      const g = el("g", { class: "og-node og-dim", "data-node": k });
      g.append(el("line", { x1: p[0], y1: p[1], x2: p[0], y2: p[1] - 14, stroke: C.lora, "stroke-width": 2 }));
      g.append(el("circle", { cx: p[0], cy: p[1] - 16, r: 4.5, fill: C.lora }));
      g.append(el("rect", { x: p[0] - 7, y: p[1] - 2, width: 14, height: 5, fill: "#F2C14E" }));   // solar panel
      svg.append(g);
    });
    svg.append(el("text", { x: HILL[0], y: HILL[1] + 18, "text-anchor": "middle", "font-size": 12, fill: C.lora, class: "og-lbl og-dim", id: "og-hill-lbl" }, "Hill node"));
    // phones
    PHONES.forEach((p, i) => svg.append(el("rect", { class: "og-phone", id: "og-phone" + i, x: p[0] - 4.5, y: p[1] - 8, width: 9, height: 16, rx: 2, fill: C.fibre })));
    // vehicles
    const bus = el("g", { id: "og-bus", class: "og-dim" });
    bus.append(el("rect", { x: -18, y: -12, width: 36, height: 16, rx: 4, fill: "#F29A3F" }));
    bus.append(el("circle", { cx: -10, cy: 6, r: 4, fill: C.ink })); bus.append(el("circle", { cx: 10, cy: 6, r: 4, fill: C.ink }));
    bus.append(el("line", { x1: 12, y1: -12, x2: 12, y2: -24, stroke: C.lora, "stroke-width": 2 }));
    bus.setAttribute("transform", `translate(665 ${ROAD_Y - 4})`);
    svg.append(bus);
    const ntes = el("g", { id: "og-ntes", class: "og-dim" });
    ntes.append(el("rect", { x: NTES[0] - 15, y: NTES[1] - 10, width: 30, height: 13, rx: 3, fill: "#E4602E" }));
    ntes.append(el("text", { x: NTES[0], y: NTES[1] - 14, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: "#A83A12", class: "og-lbl" }, "NTES on ATAK"));
    svg.append(ntes);
    return svg;
  }

  const svg = scene();
  host.replaceChildren(svg);
  const dyn = svg.querySelector("#og-dyn");
  const $ = (id) => svg.querySelector("#" + id);

  // A message dot moving along a path, repeating; still dashed line when motion is reduced.
  function flow(d, color, { dur = 2.4, begin = 0, n = 2, width = 2, dash = "4 6" } = {}) {
    dyn.append(el("path", { d, fill: "none", stroke: color, "stroke-width": width, "stroke-dasharray": dash, opacity: 0.7 }));
    if (reduce.matches) return;
    for (let i = 0; i < n; i++) {
      const dot = el("circle", { r: 4, fill: color });
      dot.append(el("animateMotion", { dur: dur + "s", begin: (begin + (i * dur) / n).toFixed(2) + "s", repeatCount: "indefinite", path: d, calcMode: "spline", keyTimes: "0;1", keySplines: "0.45 0 0.55 1" }));
      dyn.append(dot);
    }
  }
  function rings(p, color) {
    if (reduce.matches) return;
    for (let i = 0; i < 2; i++) {
      const c = el("circle", { cx: p[0], cy: p[1], r: 6, fill: "none", stroke: color, "stroke-width": 2 });
      c.append(el("animate", { attributeName: "r", from: 6, to: 60, dur: "2.2s", begin: i * 1.1 + "s", repeatCount: "indefinite" }));
      c.append(el("animate", { attributeName: "opacity", from: 0.7, to: 0, dur: "2.2s", begin: i * 1.1 + "s", repeatCount: "indefinite" }));
      dyn.append(c);
    }
  }

  function show(i) {
    step = i;
    dyn.replaceChildren();
    const failed = i >= 1;
    $("og-chain").setAttribute("stroke", failed ? C.off : C.fibre);
    $("og-relay1").setAttribute("fill", failed ? "#fff" : C.weak);
    $("og-relay1").setAttribute("stroke", failed ? C.msg : "#fff");
    $("og-relay1").setAttribute("stroke-dasharray", failed ? "4 3" : "");
    $("og-tower").setAttribute("fill", failed ? C.off : C.fibre);
    svg.querySelectorAll(".og-phone").forEach((p) => p.setAttribute("fill", i === 1 ? C.off : i >= 2 ? C.bt : C.fibre));
    svg.querySelectorAll(".og-node, #og-hill-lbl").forEach((n) => n.classList.toggle("og-dim", i < 3));
    $("og-sat").classList.toggle("og-dim", i < 4);
    $("og-ntes").classList.toggle("og-dim", i < 3);
    $("og-bus").classList.toggle("og-dim", i < 5);
    if (i === 0) {
      flow(path([TOWN, ...RELAYS, TOWER]), C.fibre, { dur: 3, n: 3, dash: "0" });
      rings([TOWER[0], TOWER[1] - 10], C.fibre);
    }
    if (i === 1) {
      flow(path([TOWN, RELAYS[0], RELAYS[1]]), C.fibre, { dur: 2, n: 2, dash: "0" });
      if (!reduce.matches) {
        const x = el("text", { x: RELAYS[1][0], y: RELAYS[1][1] + 5, "text-anchor": "middle", "font-size": 16, "font-weight": 700, fill: C.msg }, "×");
        dyn.append(x);
      }
      dyn.append(el("text", { x: 600, y: 180, "text-anchor": "middle", "font-size": 15, "font-weight": 700, fill: C.msg }, "No service"));
    }
    if (i === 2) {
      [[0, 1], [1, 2], [2, 4], [4, 5], [5, 7], [3, 6]].forEach(([a, b], k) => flow(arc(PHONES[a], PHONES[b], 16), C.bt, { dur: 1.6, begin: k * 0.25, n: 1, width: 1.6 }));
    }
    if (i === 3) {
      const N = NODES;
      [[N.clinic, N.store], [N.store, N.school], [N.school, N.hill], [N.clinic, N.hill]].forEach(([a, b], k) => flow(arc(a, b, 26), C.lora, { dur: 2.2, begin: k * 0.3, n: 1 }));
      [[PHONES[0], N.clinic], [PHONES[6], N.store], [PHONES[7], N.school], [NTES, N.store]].forEach(([a, b], k) => flow(path([a, b]), C.bt, { dur: 1.4, begin: k * 0.2, n: 1, width: 1.4 }));
    }
    if (i === 4) {
      flow(arc(NODES.clinic, SAT, 10), C.sat, { dur: 2.2, n: 2 });
      flow(arc(SAT, TOWN, 40), C.sat, { dur: 3.2, begin: 1, n: 2 });
      flow(arc(NODES.store, NODES.clinic, 20), C.lora, { dur: 1.8, n: 1 });
    }
    if (i === 5) {
      flow(path([NODES.clinic, [CLINIC[0], ROAD_Y - 14]]), C.lora, { dur: 1.4, n: 1 });
      flow(path([[TOWN[0] + 30, ROAD_Y - 14], [TOWN[0], TOWN[1] + 20]]), C.lora, { dur: 1.4, begin: 1, n: 1 });
      const bus = $("og-bus");
      if (!reduce.matches) bus.append(el("animateTransform", { attributeName: "transform", type: "translate", values: `665 ${ROAD_Y - 4};110 ${ROAD_Y - 4};665 ${ROAD_Y - 4}`, dur: "8s", repeatCount: "indefinite", calcMode: "spline", keyTimes: "0;0.5;1", keySplines: "0.45 0 0.55 1;0.45 0 0.55 1" }));
    } else {
      const bus = $("og-bus"); bus.querySelectorAll("animateTransform").forEach((a) => a.remove()); bus.setAttribute("transform", `translate(665 ${ROAD_Y - 4})`);
    }
    // caption and controls
    const s = STEPS[i];
    document.getElementById("og-step-n").textContent = `Step ${i + 1} of ${STEPS.length}`;
    document.getElementById("og-step-t").textContent = s.t;
    document.getElementById("og-step-d").textContent = s.d;
    document.getElementById("og-step-uses").replaceChildren(...s.uses.map((u) => { const c = document.createElement("span"); c.className = "og-use"; c.textContent = u; return c; }));
    document.querySelectorAll("#og-dots button").forEach((b, k) => b.setAttribute("aria-current", String(k === i)));
  }

  // controls: play/pause, previous/next, a dot per step
  const dots = document.getElementById("og-dots");
  STEPS.forEach((s, k) => { const b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-label", `Step ${k + 1}: ${s.t}`); b.addEventListener("click", () => { pause(); show(k); }); dots.append(b); });
  const playBtn = document.getElementById("og-play");
  function tick() { show((step + 1) % STEPS.length); }
  function play() { playing = true; playBtn.textContent = "Pause"; clearInterval(timer); timer = setInterval(tick, 7000); }
  function pause() { playing = false; playBtn.textContent = "Play"; clearInterval(timer); }
  playBtn.addEventListener("click", () => (playing ? pause() : play()));
  document.getElementById("og-prev").addEventListener("click", () => { pause(); show((step + STEPS.length - 1) % STEPS.length); });
  document.getElementById("og-next").addEventListener("click", () => { pause(); show((step + 1) % STEPS.length); });
  // only run while the scene is on screen
  new IntersectionObserver(([e]) => { if (!e.isIntersecting) clearInterval(timer); else if (playing) play(); }, { threshold: 0.3 }).observe(host);
  show(0);
  if (!playing) playBtn.textContent = "Play";
  // phones: the scene scrolls sideways; start in the middle so the chain and the community both show
  const wrap = host.parentElement;
  if (wrap && wrap.scrollWidth > wrap.clientWidth) wrap.scrollLeft = (wrap.scrollWidth - wrap.clientWidth) * 0.5;
})();
