"""Engine-side ablations on the REAL city OCPP simulation (engine_city.py).

Two ablations, both compromising the top-3 backends by MW (Endesa+Iberdrola+AMB = 31.7 MW,
the same set as the city attack-vector analysis), detect+isolate unless noted:

  (1) DETECTOR-SIGNAL ablation: rate-only vs consistency-only vs fused, per attack vector.
      Shows the two detection signals are COMPLEMENTARY -- neither alone covers all vectors
      (command-rate is blind to link-layer MitM tampering; consistency needs a power move).

  (2) DEFENSE-LAYER ablation: D0 none / D2 rate-limit / D5 detect-only / D3 isolate / D2+D3.
      Shows ISOLATION is the decisive containment layer; detection/rate-limit alone barely help.

Serial (one websocket port). Deterministic (fixed seed). Writes results_ablation.json.
"""
import asyncio, json, os
import engine_city as E

TOP3 = set(E.OPS[:3])
VECTORS = ["curtail", "remote_stop", "mitm_meter", "dos"]
SEED = 1

def _taud(m):
    ds = [v["tau_d"] for v in m["per_op"].values() if v["tau_d"] is not None]
    return round(sum(ds)/len(ds), 2) if ds else None

async def main():
    res = {"compromised": sorted(TOP3), "mw": round(sum(E.OP_MW[o] for o in TOP3), 2),
           "seed": SEED, "note": "top-3 backends; detect+isolate unless defense says otherwise"}

    # ---- (1) detector-signal ablation: rate / consist / fused, per vector (detect+isolate) ----
    det_abl = []
    for vec in VECTORS:
        row = {"vector": vec}
        for det in ["fused", "rate", "consist"]:
            m = await E.run_city(TOP3, vec, {"isolate": True}, seed=SEED, detector=det)
            row[det] = {"dE_kwh": m["dE_kwh"], "billing_eur": m["billing_eur"],
                        "n_affected": m["n_affected"], "denied": m["denied"],
                        "ctrl_mw": m["ctrl_mw"], "tau_d": _taud(m)}
        det_abl.append(row)
        f = row["fused"]; r = row["rate"]; c = row["consist"]
        print(f"[DET {vec:11s}] fused dE={f['dE_kwh']:7.1f} bill={f['billing_eur']:7.1f} tau={f['tau_d']} | "
              f"rate dE={r['dE_kwh']:7.1f} bill={r['billing_eur']:7.1f} tau={r['tau_d']} | "
              f"consist dE={c['dE_kwh']:7.1f} bill={c['billing_eur']:7.1f} tau={c['tau_d']}")
    res["detector_ablation"] = det_abl

    # ---- (2) defense-layer ablation on the curtail vector (fused detector) ----
    DEF = [("D0 无防御", {}), ("D2 仅限速", {"rate_limit": 3}), ("D5 仅检测", {}),
           ("D3 仅隔离", {"isolate": True}), ("D2+D3 限速+隔离", {"rate_limit": 3, "isolate": True})]
    def_abl = []
    for name, dfn in DEF:
        m = await E.run_city(TOP3, "curtail", dfn, seed=SEED, detector="fused")
        detected = any(v is not None for v in m["t_detect"].values())
        def_abl.append({"config": name, "dE_kwh": m["dE_kwh"], "n_affected": m["n_affected"],
                        "denied": m["denied"], "ctrl_mw": m["ctrl_mw"], "tau_d": _taud(m),
                        "detected": detected, "isolated": bool(dfn.get("isolate"))})
        print(f"[DEF {name:14s}] dE={m['dE_kwh']:8.1f} aff={m['n_affected']:3d} "
              f"ctrlMW={m['ctrl_mw']:5.2f} tau_d={_taud(m)} detected={detected} isolated={bool(dfn.get('isolate'))}")
    res["defense_ablation"] = def_abl

    json.dump(res, open(os.path.join(os.path.dirname(__file__), "results_ablation.json"), "w"),
              ensure_ascii=False, indent=1)
    print("[SAVED] results_ablation.json")
    make_fig(res)

def make_fig(res=None):
    import numpy as np, matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt, matplotlib.font_manager as fm
    for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
        if os.path.exists(p): fm.fontManager.addfont(p)
    plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":175})
    FIGS="/home/user/Project1/figs"; HERE=os.path.dirname(__file__)
    NAVY="#0F3D57"; TEAL="#1AA3C4"; RED="#E8384F"; GREEN="#1EA97C"; ORANGE="#F08A24"; PURPLE="#8B4DDB"; INK="#1A2633"; MUT="#5D6B7A"
    if res is None: res=json.load(open(os.path.join(HERE,"results_ablation.json")))
    city=json.load(open(os.path.join(HERE,"results_city.json")))
    base={v["label"].split()[0] if False else k: v for k,v in city["s3_vectors_top3"].items()}
    # D0 (no-containment) damage baselines per vector, from the city vector study (top-3)
    D0={vec: (city["s3_vectors_top3"][vec]["none"]["billing"] if vec=="mitm_meter"
              else city["s3_vectors_top3"][vec]["none"]["dE"]) for vec in ["curtail","remote_stop","mitm_meter","dos"]}
    VL={"curtail":"A3 限功率","remote_stop":"A3 批量停充","mitm_meter":"A1 篡改电表","dos":"A4 DoS"}
    fig,(a1,a2)=plt.subplots(1,2,figsize=(15.0,5.2),facecolor="white",gridspec_kw={"width_ratios":[1.25,1]})
    # (a) detector-signal ablation: residual damage as % of no-containment, per vector
    det=res["detector_ablation"]; vecs=[r["vector"] for r in det]; x=np.arange(len(vecs)); w=0.26
    def dmg(row,vec): return (row["billing_eur"] if vec=="mitm_meter" else row["dE_kwh"])
    for j,(sig,lab,col) in enumerate([("rate","仅指令速率",ORANGE),("consist","仅规模×节律一致性",TEAL),("fused","融合(本文)",GREEN)]):
        vals=[max(1e-3,100*dmg(r[sig],r["vector"])/max(D0[r["vector"]],1e-9)) for r in det]
        b=a1.bar(x+(j-1)*w,vals,w,color=col,label=lab,edgecolor=NAVY,lw=.5)
        for xi,vv in zip(x+(j-1)*w,vals):
            a1.text(xi,vv*1.15,("%.1f%%"%vv if vv>=0.1 else "<0.1%"),ha="center",fontsize=7.6,color=INK,rotation=0)
    a1.set_yscale("log"); a1.set_ylim(0.1,300); a1.axhline(100,color=RED,ls=":",lw=1,alpha=.7)
    a1.text(len(vecs)-1.4,118,"= 无遏制 (100%)",color=RED,fontsize=8.5)
    a1.set_xticks(x); a1.set_xticklabels([VL[v] for v in vecs],fontsize=9.5)
    a1.set_ylabel("被发现前残余损失 / 无遏制 (%，对数轴)",fontsize=10)
    a1.set_title("(a) 检测信号消融：两信号互补，缺一不可\n仅指令速率对 A1 篡改(无指令)完全失明(残留100%)；仅一致性对指令攻击较慢",fontsize=10.6,fontweight="bold",color=NAVY)
    a1.legend(fontsize=8.8,loc="upper left",ncol=1); a1.grid(axis="y",alpha=.25,which="both")
    # (b) defense-layer ablation: residual controlled energy (curtail, top-3)
    dfn=res["defense_ablation"]; names=[d["config"] for d in dfn]; de=[d["dE_kwh"] for d in dfn]; y=np.arange(len(dfn))
    cols=[RED,ORANGE,"#C9872F",TEAL,GREEN]
    a2.barh(y[::-1],de,color=cols,edgecolor=NAVY,lw=.6)
    for yi,d in zip(y[::-1],dfn):
        a2.text(max(d["dE_kwh"],12)*1.1,yi,f"{d['dE_kwh']:.0f} kWh · {d['n_affected']}站",va="center",fontsize=8.6,color=INK)
    a2.set_xscale("log"); a2.set_xlim(3,2e4); a2.set_yticks(y[::-1]); a2.set_yticklabels(names,fontsize=9.5)
    a2.set_xlabel("被发现前残余受控电量 ΔE (kWh，对数轴)",fontsize=10)
    a2.set_title("(b) 防御分层消融：隔离是决定性层\n仅检测/仅限速几乎不减损(8159→7548)；隔离→21、限速+隔离→8 kWh",fontsize=10.6,fontweight="bold",color=NAVY)
    a2.grid(axis="x",alpha=.25,which="both")
    for ax in (a1,a2):
        for sp in ax.spines.values(): sp.set_color("#C9D6E2")
        ax.tick_params(colors=MUT)
    fig.suptitle("图 12　防御消融（真实多运营商 OCPP 仿真，攻破前 3 家后台=31.7 MW）：检测信号互补 + 隔离是决定性遏制层",
                 color=NAVY,fontsize=12.5,fontweight="bold",y=1.0)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_ablation_engine.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("[fig] ablation-engine")

if __name__ == "__main__":
    asyncio.run(main())
