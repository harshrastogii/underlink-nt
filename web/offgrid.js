// "When the chain breaks": an animated walk through three layers that keep a community in touch
// after a weak link fails. Layer 1 keeps the tower on air (a satellite second path), layer 2 brings a
// network to the evacuation centre, layer 3 is the community's own radios. Messages are drawn as
// dots moving along real paths (SVG animateMotion).
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
  const CLINIC = [520, 206], STORE = [640, 258], SCHOOL = [702, 190], HILL = [690, 104], SAT = [560, 30], LSAT = [345, 24];
  const DISH = [452, 172], TRUCK = [728, 300];
  const PHONES = [[470, 220], [500, 260], [560, 238], [585, 292], [618, 214], [668, 226], [690, 286], [736, 246]];
  const NODES = { clinic: [CLINIC[0], CLINIC[1] - 26], store: [STORE[0], STORE[1] - 24], school: [SCHOOL[0], SCHOOL[1] - 24], hill: HILL };
  const ROAD_Y = 322, NTES = [505, 316];

  const C = { ink: "#16325C", fibre: "#1E6FD9", weak: "#F6A15E", off: "#C4CDD5", msg: "#E4602E", bt: "#2A78D6", lora: "#7B61D9", sat: "#0EA5C6", lband: "#0F8A6B", nbn: "#E4602E" };
  const path = (pts) => "M" + pts.map((p) => p.join(",")).join("L");
  const arc = (a, b, lift = 30) => `M${a[0]},${a[1]} Q${(a[0] + b[0]) / 2},${Math.min(a[1], b[1]) - lift} ${b[0]},${b[1]}`;

  const STEPS = [
    { t: "A normal day", d: "Phone traffic runs from the fibre town over a chain of radio relays to the community's tower, and from the tower to every phone in range.", uses: ["Licensed radio chain", "Mobile tower"] },
    { t: "A weak link fails", d: "One relay on the chain has no way around it. When its battery runs flat or a storm takes it down, the tower loses its path. Every phone loses service, although the tower itself works and the coverage map still says covered.", uses: ["What Underlink finds: 18 of 23 radio-chain places"] },
    { t: "Layer 1: a second path for the tower", d: "A satellite dish at the tower carries its traffic when the radio chain breaks, so phones keep working. Telstra already links some remote towers by satellite and planned to move more than 300 of them to OneWeb LEO, but paused in 2026 after voice problems. A second path adds resilience; a straight swap has not been reliable yet. The Hardening Program can fund a satellite second path.", uses: ["Layer 1", "LEO satellite link", "Mobile Network Hardening Program", "Rec 2: satellite failover"] },
    { t: "Heavy rain: the slow lane stays open", d: "LEO broadband uses Ku and Ka bands, which tropical downpours can fade for minutes. The government's LEO working group notes that bands above 5 GHz fade most. L-band satellites such as Iridium Certus (up to 704 kbps) barely fade, so police, clinic and NTES staff can keep a slower link for messages and calls.", uses: ["Layer 1", "Iridium Certus (L-band)", "Rain fade"] },
    { t: "Layer 2: bring a network to the evacuation centre", d: "If a cyclone takes the tower itself down, emergency teams bring the network. Under the STAND program, NBN satellite services at emergency service sites and evacuation centres, and Community Wi-Fi, are funded to the end of 2027. Telstra can also bring a satellite cell on wheels.", uses: ["Layer 2", "NBN satellite services (STAND)", "Satellite cell on wheels"] },
    { t: "Layer 3: the community's own radios", d: "Phones pass text to each other over Bluetooth (Bitchat); Reticulum apps such as Columba also carry small photos and voice notes, slowly. Solar LoRa radios on the clinic, store, school and a hill link the whole community; one private rural Australian network reports 5 to 10 km a hop through bushland, though its author says the hardware is not ready for serious emergency use. No individual licence is needed at 915 to 928 MHz under ACMA's LIPD Class Licence 2025. Meshtastic carries short text and positions.", uses: ["Layer 3", "Bitchat", "Meshtastic", "Reticulum"] },
    { t: "Out, or wait", d: "One radio at the clinic also uses the clinic's satellite service, so mesh messages reach the outside world. When no link is up, a radio that stays on holds them, and a radio on the bush bus or clinic car carries them to town.", uses: ["Layer 3", "Satellite bridge", "Store and forward"] },
  ];
  const phoneView = window.matchMedia("(max-width: 720px)");
  let step = 0, playing = !reduce.matches && !phoneView.matches, timer = null;

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
    svg.append(el("text", { x: SAT[0], y: SAT[1] + 24, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: C.sat, class: "og-lbl og-dim", id: "og-sat-lbl" }, "LEO satellite"));
    const lsat = el("g", { id: "og-lsat", class: "og-dim" });
    lsat.append(el("rect", { x: LSAT[0] - 8, y: LSAT[1] - 8, width: 16, height: 16, rx: 3, fill: C.lband }));
    lsat.append(el("rect", { x: LSAT[0] - 30, y: LSAT[1] - 4, width: 18, height: 8, fill: "#9FD9C6" }));
    lsat.append(el("rect", { x: LSAT[0] + 12, y: LSAT[1] - 4, width: 18, height: 8, fill: "#9FD9C6" }));
    lsat.append(el("text", { x: LSAT[0], y: LSAT[1] + 24, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: C.lband, class: "og-lbl" }, "L-band satellite"));
    svg.append(lsat);
    // rain: short slanted strokes over the sky, falling while step 4 shows
    const rain = el("g", { id: "og-rain", visibility: "hidden", stroke: "#7FA6CF", "stroke-width": 1.4, "stroke-linecap": "round" });
    for (let k = 0; k < 46; k++) { const x = (k * 53) % 760, y = 8 + ((k * 37) % 150); rain.append(el("line", { x1: x, y1: y, x2: x - 6, y2: y + 14 })); }
    svg.append(rain);
    // chain
    svg.append(el("path", { id: "og-chain", d: path([TOWN, ...RELAYS, TOWER]), fill: "none", stroke: C.fibre, "stroke-width": 3 }));
    RELAYS.forEach((r, i) => svg.append(el("circle", { id: "og-relay" + i, cx: r[0], cy: r[1], r: 12, fill: C.weak, stroke: "#fff", "stroke-width": 2 })));
    // tower
    svg.append(el("path", { d: `M${TOWER[0] - 12},${TOWER[1] + 34} L${TOWER[0]},${TOWER[1] - 8} L${TOWER[0] + 12},${TOWER[1] + 34}`, fill: "none", stroke: C.ink, "stroke-width": 3 }));
    svg.append(el("circle", { id: "og-tower", cx: TOWER[0], cy: TOWER[1] - 10, r: 6, fill: C.fibre }));
    const dish = el("g", { id: "og-dish", class: "og-dim" });   // the tower's satellite terminal (layer 1)
    dish.append(el("path", { d: `M${DISH[0] - 9},${DISH[1]} q9,-14 18,0 z`, fill: C.sat }));
    dish.append(el("line", { x1: DISH[0], y1: DISH[1], x2: DISH[0], y2: DISH[1] + 12, stroke: C.ink, "stroke-width": 2 }));
    svg.append(dish);
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
    ntes.append(el("text", { x: NTES[0], y: NTES[1] - 14, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: "#A83A12", class: "og-lbl" }, "NTES"));
    svg.append(ntes);
    const truck = el("g", { id: "og-truck", class: "og-dim" });   // NBN Road Muster style truck (layer 2)
    truck.append(el("rect", { x: TRUCK[0] - 22, y: TRUCK[1] - 14, width: 44, height: 18, rx: 4, fill: C.nbn }));
    truck.append(el("circle", { cx: TRUCK[0] - 12, cy: TRUCK[1] + 6, r: 4, fill: C.ink })); truck.append(el("circle", { cx: TRUCK[0] + 12, cy: TRUCK[1] + 6, r: 4, fill: C.ink }));
    truck.append(el("path", { d: `M${TRUCK[0] - 6},${TRUCK[1] - 14} q6,-10 12,0 z`, fill: C.sat }));
    truck.append(el("text", { x: TRUCK[0] - 6, y: TRUCK[1] - 30, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700, fill: "#A83A12", class: "og-lbl" }, "Satellite truck"));
    svg.append(truck);
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
    const chainOn = i === 0, towerDown = i >= 4;
    const towerColor = i === 0 ? C.fibre : i === 2 || i === 3 ? C.sat : C.off;
    $("og-chain").setAttribute("stroke", chainOn ? C.fibre : C.off);
    $("og-relay1").setAttribute("fill", chainOn ? C.weak : "#fff");
    $("og-relay1").setAttribute("stroke", chainOn ? "#fff" : C.msg);
    $("og-relay1").setAttribute("stroke-dasharray", chainOn ? "" : "4 3");
    $("og-tower").setAttribute("fill", towerColor);
    const near = new Set([5, 6, 7]);                       // phones within the truck's Wi-Fi
    svg.querySelectorAll(".og-phone").forEach((p, k) => p.setAttribute("fill",
      i === 0 || i === 2 ? C.fibre : i === 3 ? (k % 2 ? C.fibre : C.off) : i === 4 ? (near.has(k) ? C.nbn : C.off) : i >= 5 ? C.bt : C.off));
    svg.querySelectorAll(".og-node, #og-hill-lbl").forEach((n) => n.classList.toggle("og-dim", i < 5));
    $("og-sat").classList.toggle("og-dim", i < 2 || i === 5);
    $("og-sat-lbl").classList.toggle("og-dim", i < 2 || i === 5);
    $("og-lsat").classList.toggle("og-dim", i !== 3);
    $("og-rain").setAttribute("visibility", i === 3 ? "visible" : "hidden");
    $("og-dish").classList.toggle("og-dim", i < 2 || towerDown);
    $("og-truck").classList.toggle("og-dim", i !== 4);
    $("og-ntes").classList.toggle("og-dim", i !== 3 && i !== 5);
    $("og-bus").classList.toggle("og-dim", i !== 6);
    const rain = $("og-rain");
    rain.querySelectorAll("animateTransform").forEach((a) => a.remove());
    if (i === 3 && !reduce.matches) rain.append(el("animateTransform", { attributeName: "transform", type: "translate", values: "0 -20;6 20", dur: "0.9s", repeatCount: "indefinite" }));
    if (i === 0) {
      flow(path([TOWN, ...RELAYS, TOWER]), C.fibre, { dur: 3, n: 3, dash: "0" });
      rings([TOWER[0], TOWER[1] - 10], C.fibre);
    }
    if (i === 1) {
      flow(path([TOWN, RELAYS[0], RELAYS[1]]), C.fibre, { dur: 2, n: 2, dash: "0" });
      if (!reduce.matches) dyn.append(el("text", { x: RELAYS[1][0], y: RELAYS[1][1] + 5, "text-anchor": "middle", "font-size": 16, "font-weight": 700, fill: C.msg }, "×"));
      dyn.append(el("text", { x: 600, y: 180, "text-anchor": "middle", "font-size": 15, "font-weight": 700, fill: C.msg }, "No service"));
    }
    if (i === 2) {                                         // layer 1: the tower's own satellite path
      flow(arc(DISH, SAT, 30), C.sat, { dur: 2, n: 2 });
      flow(arc(SAT, TOWN, 40), C.sat, { dur: 3, begin: 0.8, n: 2 });
      rings([TOWER[0], TOWER[1] - 10], C.sat);
    }
    if (i === 3) {                                         // rain fade on Ku/Ka; L-band keeps a slow link
      const fade = el("path", { d: arc(DISH, SAT, 30), fill: "none", stroke: C.sat, "stroke-width": 2, "stroke-dasharray": "2 9", opacity: 0.5 });
      if (!reduce.matches) fade.append(el("animate", { attributeName: "opacity", values: "0.6;0.1;0.6", dur: "2.4s", repeatCount: "indefinite" }));
      dyn.append(fade);
      flow(arc(NTES, LSAT, 60), C.lband, { dur: 2.6, n: 1 });
      flow(arc(LSAT, TOWN, 30), C.lband, { dur: 2.2, begin: 1.2, n: 1 });
      flow(arc(CLINIC, LSAT, 50), C.lband, { dur: 2.8, begin: 0.6, n: 1 });
      dyn.append(el("text", { x: 600, y: 160, "text-anchor": "middle", "font-size": 13, "font-weight": 700, fill: "#0B6E85" }, "LEO fading in rain"));
    }
    if (i === 4) {                                         // layer 2: the truck's Wi-Fi at the evacuation centre
      if (!reduce.matches) dyn.append(el("text", { x: TOWER[0], y: TOWER[1] - 22, "text-anchor": "middle", "font-size": 16, "font-weight": 700, fill: C.msg }, "×"));
      rings(TRUCK, C.nbn);
      flow(arc(TRUCK, SAT, 40), C.sat, { dur: 2.2, n: 2 });
      flow(arc(SAT, TOWN, 40), C.sat, { dur: 3, begin: 0.8, n: 2 });
      [5, 6, 7].forEach((k, j) => flow(path([PHONES[k], TRUCK]), C.nbn, { dur: 1.3, begin: j * 0.3, n: 1, width: 1.4 }));
      dyn.append(el("text", { x: SCHOOL[0] - 6, y: SCHOOL[1] - 26, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: "#A83A12" }, "Evacuation centre"));
    }
    if (i === 5) {                                         // layer 3: Bluetooth between phones, LoRa between nodes
      const N = NODES;
      [[0, 1], [1, 2], [2, 4], [4, 5], [5, 7], [3, 6]].forEach(([a, b], k) => flow(arc(PHONES[a], PHONES[b], 16), C.bt, { dur: 1.6, begin: k * 0.25, n: 1, width: 1.6 }));
      [[N.clinic, N.store], [N.store, N.school], [N.school, N.hill], [N.clinic, N.hill]].forEach(([a, b], k) => flow(arc(a, b, 26), C.lora, { dur: 2.2, begin: k * 0.3, n: 1 }));
      flow(path([NTES, N.store]), C.bt, { dur: 1.4, n: 1, width: 1.4 });
    }
    if (i === 6) {                                         // out through the clinic's satellite, or carried by the bus
      flow(arc(NODES.clinic, SAT, 10), C.sat, { dur: 2.2, n: 2 });
      flow(arc(SAT, TOWN, 40), C.sat, { dur: 3.2, begin: 1, n: 2 });
      flow(arc(NODES.store, NODES.clinic, 20), C.lora, { dur: 1.8, n: 1 });
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
  // each step stays long enough to read its caption (about 260 ms a word, at least 8 s);
  // the caption is announced only when the reader steps by hand, not every few seconds while playing
  const caption = document.querySelector(".og-caption");
  const dwell = () => Math.max(8000, STEPS[step].d.split(/\s+/).length * 260);
  function schedule() { clearTimeout(timer); timer = setTimeout(() => { show((step + 1) % STEPS.length); if (playing) schedule(); }, dwell()); }
  function play() { playing = true; playBtn.textContent = "Pause"; if (caption) caption.setAttribute("aria-live", "off"); schedule(); }
  function pause() { playing = false; playBtn.textContent = "Play"; if (caption) caption.setAttribute("aria-live", "polite"); clearTimeout(timer); }
  playBtn.addEventListener("click", () => (playing ? pause() : play()));
  document.getElementById("og-prev").addEventListener("click", () => { pause(); show((step + STEPS.length - 1) % STEPS.length); });
  document.getElementById("og-next").addEventListener("click", () => { pause(); show((step + 1) % STEPS.length); });
  // only run while the scene is on screen
  new IntersectionObserver(([e]) => { if (!e.isIntersecting) clearTimeout(timer); else if (playing) play(); }, { threshold: 0.3 }).observe(host);
  show(0);
  if (!playing) playBtn.textContent = "Play";
  // phones: the scene scrolls sideways; start in the middle so the chain and the community both show
  const wrap = host.parentElement;
  if (wrap && wrap.scrollWidth > wrap.clientWidth) wrap.scrollLeft = (wrap.scrollWidth - wrap.clientWidth) * 0.5;
})();
