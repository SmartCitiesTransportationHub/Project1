import asyncio, json, os, numpy as np
import engine2 as E
ATTACKS=[("快速篡改(30/min)",{"mode":"curtail","rate":30}),
         ("隐蔽慢速(3/min)",{"mode":"curtail","rate":3}),
         ("批量远程停充(30/min)",{"mode":"remote_stop","rate":30})]
DEFENSES=[("D0 无防御",{}),
          ("D5 仅检测",{"detect_only":True}),
          ("D3+D5 检测+隔离",{"isolate":True}),
          ("D2 限速",{"rate_limit":2}),
          ("D2+D3+D5 限速+隔离",{"rate_limit":2,"isolate":True})]
REPS=[17*3600+1800,18*3600,18*3600+1800]   # attack start times as reps
async def main():
    out=[]; series_keep={}
    for ai,(an,atk) in enumerate(ATTACKS):
        for di,(dn,dfn) in enumerate(DEFENSES):
            runs=[]
            for r,t0 in enumerate(REPS):
                m=await E.run_scenario(atk,dfn,seed=r,with_attack=True,t0_attack=t0)
                runs.append(m)
                if r==1 and an=="快速篡改(30/min)":   # keep series for timeline fig (t0=18:00)
                    series_keep[dn]={"ctrl":m["ctrl_mw_series"],"obs":m["obs_series"]}
            agg={k:[x[k] for x in runs if x[k] is not None] for k in ["dE_kwh","denied","ctrl_sites","ctrl_mw","tau_d_min","recovery_min","n_cmds"]}
            out.append({"attack":an,"defense":dn,"ai":ai,"di":di,
                        "dE_med":float(np.median(agg["dE_kwh"])),"dE_lo":float(np.min(agg["dE_kwh"])),"dE_hi":float(np.max(agg["dE_kwh"])),
                        "denied_med":float(np.median(agg["denied"])),"ctrl_sites_med":float(np.median(agg["ctrl_sites"])),
                        "ctrl_mw_med":float(np.median(agg["ctrl_mw"])),
                        "tau_med":(float(np.median(agg["tau_d_min"])) if agg["tau_d_min"] else None),
                        "n_detected":len(agg["tau_d_min"])})
            print(f"{an:18s} | {dn:16s} dE={out[-1]['dE_med']:7.1f} denied={out[-1]['denied_med']:5.0f} sites={out[-1]['ctrl_sites_med']:4.0f} tau={out[-1]['tau_med']}")
    # benign FPR
    fp=0; N=4
    for r in range(N):
        m=await E.run_scenario(ATTACKS[0][1],{"isolate":True},seed=r,with_attack=False,t0_attack=18*3600)
        if m["tau_d_min"] is not None: fp+=1
    json.dump({"cells":out,"series":series_keep,"fpr":{"false_alarms":fp,"runs":N}},
              open("results.json","w"),ensure_ascii=False,indent=1)
    print(f"[FPR] {fp}/{N} benign runs false-alarmed")
    print("[SAVED] results.json")
asyncio.run(main())
