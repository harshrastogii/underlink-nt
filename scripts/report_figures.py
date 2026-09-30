"""Draw every report and deck figure from the pipeline outputs.

Run after `python run_all.py`. Numbers come from outputs/public/numbers.json and
the CSVs beside it, so the figures and the text can never disagree.
Figures contain no place coordinates and no relay identifiers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from underlink.config import FIGURES, PUBLIC, RESTRICTED  # noqa: E402

# Validated default palette (dataviz reference instance), light mode.
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#ffffff"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"]    # ordinal ramp for repair bands
NEUTRAL = "#c9c8c3"

plt.rcParams.update({
    "font.family": "Arial", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.facecolor": SURFACE,
})
N = json.loads((PUBLIC / "numbers.json").read_text())


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 1: the hero chain, drawn abstractly (no coordinates, no IDs)
# ---------------------------------------------------------------------------
def fig_hero_chain():
    hero = N["named_places"]["Ampilatwatja"]
    hops, spof = int(hero["hops"]), int(hero["n_spof"])
    fig, ax = plt.subplots(figsize=(6.7, 2.1))
    ax.set_xlim(-0.6, hops + 3.5); ax.set_ylim(-1.35, 1.25); ax.axis("off")
    # positions: fibre town (0), fibre-connected site (1), relays (2..hops), end site (hops+1), community (hops+2)
    xs = list(range(hops + 3))
    ax.plot([0, 1], [0, 0], color=BLUE, lw=5, solid_capstyle="round", zorder=1)
    ax.plot([1, hops + 1], [0, 0], color=INK2, lw=1.6, zorder=1)
    ax.plot([hops + 1, hops + 2.6], [0, 0], color=INK2, lw=1.2, ls=(0, (2, 2)), zorder=1)
    ax.add_patch(FancyBboxPatch((-0.25, -0.3), 0.5, 0.6, boxstyle="round,pad=0.02,rounding_size=0.08", fc=BLUE, ec="none", zorder=2))
    ax.text(0, -0.62, "Fibre\ntown", ha="center", va="top", color=INK, fontsize=8.5)
    ax.scatter([1], [0], s=150, color=SURFACE, edgecolor=BLUE, linewidth=2, zorder=3)
    ax.text(1, -0.62, "Fibre-\nconnected\nsite", ha="center", va="top", color=INK2, fontsize=7.5)
    relay_x = xs[2:hops + 1]
    ax.scatter(relay_x, [0] * len(relay_x), s=170, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.text(sum(relay_x) / len(relay_x), 0.42, f"{spof} single-path relays in a row", ha="center", va="bottom", color=INK, fontsize=8.5)
    ax.plot([relay_x[0], relay_x[-1]], [0.32, 0.32], color=ORANGE, lw=1)
    ax.scatter([hops + 1], [0], s=150, marker="s", color=SURFACE, edgecolor=INK, linewidth=1.6, zorder=3)
    ax.text(hops + 1, -0.62, "Community\nmobile site", ha="center", va="top", color=INK2, fontsize=7.5)
    ax.add_patch(plt.Circle((hops + 2.6, 0), 0.62, fc="#eaf2fc", ec=BLUE, ls=(0, (3, 2)), lw=1, zorder=0))
    ax.scatter([hops + 2.6], [0], s=60, color=INK, zorder=3)
    ax.text(hops + 2.6, -0.72, "Community", ha="center", va="top", color=INK, fontsize=8.5)
    ax.text(hops + 2.6, 0.72, "Inside Telstra's\npredicted 4G area", ha="center", va="bottom", color=BLUE, fontsize=7.5)
    save(fig, "fig1_hero_chain")


# ---------------------------------------------------------------------------
# Figure 2: method in one picture
# ---------------------------------------------------------------------------
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(6.7, 2.7)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 4.2)

    def box(x, y, w, h, title, body, fc="#f6f6f4", ec=GRID, tc=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1))
        ax.text(x + 0.1, y + h - 0.12, title, ha="left", va="top", fontsize=8, fontweight="bold", color=tc)
        ax.text(x + 0.1, y + h - 0.42, body, ha="left", va="top", fontsize=6.8, color=INK2, linespacing=1.35)

    box(0.05, 0.2, 2.2, 3.8, "Inputs (18 sources)", "8 organiser datasets\n+ 10 more\n\nACMA licence register:\npoint-to-point links\n\nBoM cyclone tracks\nNTG registers 2019, 2021\nHardening Program sites\nSky Muster, payphones,\nWi-Fi phones\nRoads, land councils\nOutage registers")
    box(2.55, 0.2, 1.75, 3.8, "Prepare", "Hash relay IDs\nRound coordinates\nto ~1 km\n\nManifest: URL,\nlicence, md5,\nrow counts\n\nShipped: 0.7 MB")
    readouts = [("A  Coverage claim", "Telstra map, audit tiles"), ("B  Relay chain", "dominators to fibre"), ("C  Hazard replay", "5 cyclones, 3 radii"), ("D  Repair window", "base + travel + access"), ("E  What still works", "fallbacks within 3 km")]
    for i, (t, b) in enumerate(readouts):
        y = 3.3 - i * 0.74
        box(4.6, y, 2.35, 0.64, t, b, fc="#eaf2fc" if t.startswith("B") else "#f6f6f4", ec=BLUE if t.startswith("B") else GRID)
    box(7.25, 2.7, 2.7, 1.3, "Community", "\"When the phone goes down\"\ncard, draft for co-design")
    box(7.25, 1.45, 2.7, 1.1, "Government (DCDD)", "Regional counts, KPIs,\nstar schema, data request")
    box(7.25, 0.2, 2.7, 1.1, "Providers (restricted)", "Relay register,\ncorrection file")
    for x0, x1 in ((2.27, 2.53), (4.32, 4.58), (6.97, 7.23)):
        ax.annotate("", xy=(x1, 2.1), xytext=(x0, 2.1), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))
    ax.text(5.77, 0.0, "Kept separate. Never merged into one score.", ha="center", va="bottom", fontsize=6.8, color=INK2, style="italic")
    save(fig, "fig2_pipeline")


# ---------------------------------------------------------------------------
# Figure 3: relays without an alternative path, per radio-chain place
# ---------------------------------------------------------------------------
def fig_spof_distribution():
    pc = pd.read_csv(RESTRICTED / "place_chains.csv")
    rc = pc[(pc.larger) & (pc.chain_class == "radio-chain")]
    counts = rc.groupby(["n_spof", "claimed_4g_2026"]).size().unstack(fill_value=0).reindex(range(0, int(rc.n_spof.max()) + 1), fill_value=0)
    cov = counts.get(True, pd.Series(0, index=counts.index))
    unc = counts.get(False, pd.Series(0, index=counts.index))
    fig, ax = plt.subplots(figsize=(4.6, 2.5))
    x = counts.index.values
    ax.bar(x, cov, width=0.62, color=BLUE, label="Inside Telstra's predicted 4G area", zorder=2)
    ax.bar(x, unc, width=0.62, bottom=cov + 0.06, color=ORANGE, label="Outside it", zorder=2)
    for xi, a, b in zip(x, cov, unc):
        if a + b:
            ax.text(xi, a + b + 0.25, str(a + b), ha="center", va="bottom", color=INK, fontsize=8)
    ax.set_xticks(x); ax.set_xlabel("Single-path relays on the place's chain")
    ax.set_ylabel("Radio-chain places"); ax.set_ylim(0, max(cov + unc) + 1.6)
    ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    save(fig, "fig3_spof_distribution")


# ---------------------------------------------------------------------------
# Figure 4: hazard replay, places exposed per event
# ---------------------------------------------------------------------------
def fig_replay():
    rep = pd.read_csv(PUBLIC / "replay_summary.csv")
    main = rep[(rep.radius_km == 100) & (~rep.cyclone_only)].set_index("event")
    rng = rep.groupby("event").exposed_larger.agg(["min", "max"])
    order = list(main.index)[::-1]
    fig, ax = plt.subplots(figsize=(4.6, 2.3))
    y = range(len(order))
    direct = main.loc[order, "exposed_larger"] - main.loc[order, "upstream_only_larger"]
    up = main.loc[order, "upstream_only_larger"]
    ax.barh(y, direct, height=0.5, color=BLUE, label="Own site or place in footprint", zorder=2)
    ax.barh(y, up, left=direct + 0.05, height=0.5, color=ORANGE, label="Cut off by an upstream relay only", zorder=2)
    for yi, ev in zip(y, order):
        lo, hi = rng.loc[ev, "min"], rng.loc[ev, "max"]
        ax.plot([lo, hi], [yi - 0.36, yi - 0.36], color=INK2, lw=1)
        ax.plot([lo, lo], [yi - 0.42, yi - 0.30], color=INK2, lw=1); ax.plot([hi, hi], [yi - 0.42, yi - 0.30], color=INK2, lw=1)
    ax.set_yticks(list(y)); ax.set_yticklabels(order)
    ax.set_xlabel("Larger radio-chain places that lose their path (100 km, whole track)")
    ax.xaxis.grid(True, color=GRID, lw=0.6, zorder=0); ax.set_axisbelow(True)
    ax.plot([], [], color=INK2, lw=1, label="Range across 6 variants (50-150 km; whole track or gale-strength part)")
    ax.legend(frameon=False, fontsize=7, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=1)
    save(fig, "fig4_replay")


# ---------------------------------------------------------------------------
# Figure 5: repair window by season, and what is known about power at relays
# ---------------------------------------------------------------------------
def fig_repair_power():
    R = N["repair"]; bands = ["<1 d", "1-3 d", "3-14 d", ">14 d"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.2, 2.6), gridspec_kw={"height_ratios": [2, 1], "hspace": 0.9})
    for yi, (lab, key) in enumerate((("July (dry)", "jul_bands"), ("January (wet)", "jan_bands"))):
        left = 0
        for b, col in zip(bands, SEQ):
            v = R[key].get(b, 0)
            if v:
                a1.barh(yi, v, left=left, height=0.55, color=col, edgecolor=SURFACE, linewidth=1.5)
                a1.text(left + v / 2, yi, f"{b}: {v}", ha="center", va="center", fontsize=7.5, color=INK if col in SEQ[:2] else SURFACE)
                left += v
    a1.set_yticks([0, 1]); a1.set_yticklabels(["July (dry)", "January (wet)"]); a1.set_xlim(0, R["radio_chain_places"])
    a1.set_title("Indicative repair window for the 23 radio-chain places (wet-access days are an assumption)", fontsize=8, color=INK, loc="left")
    a1.spines["left"].set_visible(False); a1.tick_params(axis="y", length=0)
    pcs = N["relays"]["power_classes"]; tot = N["relays"]["spof_relays"]
    parts = [("In Hardening Program", N["relays"]["published_autonomy"], BLUE),
             ("Depot within 150 km", pcs.get("P4_depot_within_150km", 0), SEQ[1]),
             ("No public backup information", pcs.get("P0_unknown", 0), NEUTRAL)]
    left = 0
    for lab, v, col in parts:
        if v:
            a2.barh(0, v, left=left, height=0.55, color=col, edgecolor=SURFACE, linewidth=1.5)
            a2.text(left + v / 2, 0, f"{lab}: {v}", ha="center", va="center", fontsize=7.5, color=INK)
            left += v
    a2.set_xlim(0, tot); a2.set_yticks([])
    a2.set_title(f"Backup power at the {tot} single-path relays (in the Hardening Program: {N['relays']['published_autonomy']})", fontsize=8, color=INK, loc="left")
    a2.spines["left"].set_visible(False)
    save(fig, "fig5_repair_power")


if __name__ == "__main__":
    fig_hero_chain(); fig_pipeline(); fig_spof_distribution(); fig_replay(); fig_repair_power()
    print("figures written to", FIGURES)
