"""Illustration: what a single people-per-dollar objective would choose.

We use this in the report's Discussion to explain why Underlink keeps its
readouts separate. A greedy optimiser spends a fixed budget on whichever option
covers the most uncovered people per dollar. Costs are grant values or stated
assumptions (config/params.yaml), not whole-of-life costs, so the result is an
illustration, not a recommendation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from underlink.config import P, PROCESSED, PUBLIC  # noqa: E402
from underlink.geo import haversine_km  # noqa: E402

C = P["single_score_probe"]


def candidates() -> pd.DataFrame:
    """Places outside Telstra's claimed coverage and not already near funded work."""
    pl = pd.read_csv(PROCESSED / "places.csv")
    fd = pd.read_csv(PROCESSED / "funded.csv")
    near_funded = [bool(len(fd)) and haversine_km(r.lat, r.lon, fd.lat.values, fd.lon.values).min() <= C["exclude_near_funded_km"] for r in pl.itertuples()]
    u = pl[(~pl.claimed_4g_2026) & (~np.array(near_funded))].copy()
    u["pop"] = u.population_2020.fillna(0)
    return u.reset_index(drop=True)


def greedy(u: pd.DataFrame, options: dict, budget: float) -> dict:
    lat, lon, pop = u.lat.values, u.lon.values, u["pop"].values
    D = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    covered = np.zeros(len(u), bool); spent = 0.0; mix = {}
    while True:
        best = None
        for name, (cost, radius) in options.items():
            if spent + cost > budget:
                continue
            gain = ((D <= radius) & ~covered[None, :]) @ pop     # people newly covered by a site at each place
            i = int(np.argmax(gain))
            if gain[i] > 0 and (best is None or gain[i] / cost > best[0]):
                best = (gain[i] / cost, name, i, cost, radius)
        if best is None:
            break
        _, name, i, cost, radius = best
        covered |= D[i] <= radius; spent += cost; mix[name] = mix.get(name, 0) + 1
    return {"spent_aud": round(spent), "people_covered": int(pop[covered].sum()), "mix": mix}


def run() -> dict:
    u = candidates()
    opts = {k: tuple(v) for k, v in C["options"].items()}
    out = {"candidate_places": int(len(u)), "candidate_people": int(u["pop"].sum()),
           "base": greedy(u, opts, C["budget_aud"]), "macro_cost_sweep": {}}
    for mc in C["macro_cost_sweep"]:
        o = dict(opts); o["macro_tower"] = (mc, opts["macro_tower"][1])
        out["macro_cost_sweep"][str(mc)] = greedy(u, o, C["budget_aud"])
    (PUBLIC / "single_score_probe.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
