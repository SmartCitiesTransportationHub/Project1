"""Engine experiments E2/E3/E5 (real multi-operator OCPP sim). Serial (one websocket port).

  E2  Fragmentation vs MONOLITHIC counterfactual: single-backend compromise under the real
      39-backend topology (max = Endesa) vs a single city-wide CSMS holding all 621 locations.
      Isolates the blast-radius-bounding effect of control-plane fragmentation as a clean A/B.

  E3  Stealth / adaptive attacker: partial-curtail fraction f x fan-out rate sweep, FUSED
      detector. Maps where BOTH detection signals go blind (rate<=1/min evades command-rate;
      shallow f keeps the consistency ratio in-band) -> the honest ">99% containment holds for
      LOUD attacks only" blind spot.

  E5  Optimal-stopping controller INSIDE the engine: on rate-evading stealth attacks, the
      isolation trigger on the consistency ratio = fixed rule vs Shiryaev posterior vs CUSUM.
      Shows the optimal-stopping advantage materialises as lower residual dE in the real sim
      (not just on the abstract Gaussian), and where even it cannot help.

Deterministic. Writes results_ablation2.json.
"""
import asyncio, json, os
import engine_city as E

TOP3 = set(E.OPS[:3])
ALLOPS = set(E.OPS)   # for the synchrony-gate blackout demo (all backends drop together)
ASTAR = 0.9           # headline Shiryaev posterior threshold A* (~0.9; per-operator 0.08-0.98 in optstop)
CUSUM_THR = 6.0
SEED = 1

def _taud(m):
    ds = [v["tau_d"] for v in m["per_op"].values() if v["tau_d"] is not None]
    return round(sum(ds)/len(ds), 2) if ds else None
def _det(m): return any(v is not None for v in m["t_detect"].values())

async def e2_monolithic():
    big = E.OPS[0]                                   # largest backend (Endesa)
    f0 = await E.run_city({big}, "curtail", {}, seed=SEED)
    f3 = await E.run_city({big}, "curtail", {"isolate": True}, seed=SEED)
    # monkeypatch the topology to a single city-wide CSMS (all 621 locations, one control domain)
    sOPS, sOL, sLO, sMW = E.OPS, E.OP_LOCS, E.LOC_OP, E.OP_MW
    E.OPS = ["__CITY__"]; E.OP_LOCS = {"__CITY__": E.ALL}
    E.LOC_OP = {l: "__CITY__" for l in E.ALL}; E.OP_MW = {"__CITY__": E.CITY_MW}
    try:
        m0 = await E.run_city({"__CITY__"}, "curtail", {}, seed=SEED)
        m3 = await E.run_city({"__CITY__"}, "curtail", {"isolate": True}, seed=SEED)
    finally:
        E.OPS, E.OP_LOCS, E.LOC_OP, E.OP_MW = sOPS, sOL, sLO, sMW
    res = {"fragmented_single_max": {"op": big, "mw": sMW[big], "d0_dE": f0["dE_kwh"], "d0_aff": f0["n_affected"],
                                     "d0_ctrlMW": f0["ctrl_mw"], "iso_dE": f3["dE_kwh"], "iso_aff": f3["n_affected"]},
           "monolithic": {"mw": E.CITY_MW, "d0_dE": m0["dE_kwh"], "d0_aff": m0["n_affected"],
                          "d0_ctrlMW": m0["ctrl_mw"], "iso_dE": m3["dE_kwh"], "iso_aff": m3["n_affected"]}}
    print(f"[E2] fragmented max ({big[:14]}): D0 ctrlMW={f0['ctrl_mw']:.2f} aff={f0['n_affected']} | "
          f"monolithic: D0 ctrlMW={m0['ctrl_mw']:.2f} aff={m0['n_affected']} dE={m0['dE_kwh']:.0f} | "
          f"iso collateral frag={f3['n_affected']} vs mono={m3['n_affected']}")
    return res

async def e3_stealth():
    rows = []
    for f in [1.0, 0.5, 0.3, 0.15]:
        for rate in [30, 5, 2, 1]:
            m = await E.run_city(TOP3, "curtail", {"isolate": True}, seed=SEED, curtail_frac=f, rate=rate, detector="fused")
            rows.append({"f": f, "rate": rate, "dE_kwh": m["dE_kwh"], "n_affected": m["n_affected"],
                         "detected": _det(m), "tau_d": _taud(m)})
            print(f"[E3] f={f:4.2f} rate={rate:2d}/min fused: dE={m['dE_kwh']:8.1f} aff={m['n_affected']:3d} det={_det(m)} tau={_taud(m)}")
    return rows

async def e5_controller():
    rows = []
    for f in [1.0, 0.5, 0.3, 0.15]:
        mf = await E.run_city(TOP3, "curtail", {"isolate": True}, seed=SEED, curtail_frac=f, rate=1, detector="consist", decision="fixed")
        ms = await E.run_city(TOP3, "curtail", {"isolate": True}, seed=SEED, curtail_frac=f, rate=1, decision="shiryaev", astar=ASTAR)
        mc = await E.run_city(TOP3, "curtail", {"isolate": True}, seed=SEED, curtail_frac=f, rate=1, decision="cusum", astar=CUSUM_THR)
        red = 100*(1 - ms["dE_kwh"]/mf["dE_kwh"]) if mf["dE_kwh"] > 0 else 0
        rows.append({"f": f, "fixed_dE": mf["dE_kwh"], "shiryaev_dE": ms["dE_kwh"], "cusum_dE": mc["dE_kwh"],
                     "fixed_det": _det(mf), "shiryaev_det": _det(ms), "cusum_det": _det(mc), "shi_reduction_pct": round(red, 1)})
        print(f"[E5] f={f:4.2f} rate=1: fixed-consist dE={mf['dE_kwh']:8.1f} | shiryaev dE={ms['dE_kwh']:8.1f} (-{red:.0f}%) | cusum dE={mc['dE_kwh']:8.1f}")
    return rows

async def e1_synchrony():
    """E1 synchrony gate: a network-wide synchronous drop (blackout proxy, all backends via the consistency
    signal) vs a localized attack (top-3). The gate suppresses isolation when >=K backends drop together."""
    out = {}
    for gate in [0, 10]:
        bo = await E.run_city(ALLOPS, "curtail", {"isolate": True}, seed=SEED, detector="consist", sync_gate=gate)
        at = await E.run_city(TOP3, "curtail", {"isolate": True}, seed=SEED, detector="consist", sync_gate=gate)
        bo_iso = sum(1 for v in bo["t_detect"].values() if v is not None)
        at_iso = sum(1 for v in at["t_detect"].values() if v is not None)
        out[f"gate{gate}"] = {"blackout_false_isolations": bo_iso, "n_ops": len(E.OPS),
                              "attack_isolations": at_iso, "attack_dE": at["dE_kwh"]}
        print(f"[E1] sync_gate={gate:2d}: blackout(all {len(E.OPS)} drop) false-iso={bo_iso}/{len(E.OPS)} | "
              f"localized attack iso={at_iso}/3 dE={at['dE_kwh']:.1f}")
    return out

async def main():
    res = {"compromised_top3": sorted(TOP3), "seed": SEED, "astar": ASTAR, "cusum_thr": CUSUM_THR}
    res["e2_monolithic"] = await e2_monolithic()
    res["e3_stealth"] = await e3_stealth()
    res["e5_controller"] = await e5_controller()
    res["e1_synchrony_gate"] = await e1_synchrony()
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "results_ablation2.json"), "w"),
              ensure_ascii=False, indent=1)
    print("[SAVED] results_ablation2.json")

if __name__ == "__main__":
    asyncio.run(main())
