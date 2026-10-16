"""Export geometry + real city-sim timelines for the multi-operator 3D console.
Headline scenarios (each with full per-tick timeline + message stream):
  single_endesa   : compromise the largest backend (curtail) D0 vs detect+isolate
  campaign_top5   : coordinated compromise of top-5 backends (curtail) D0 vs isolate
Produces artifact_data_city.json consumed by console_city.html.
"""
import os, json, asyncio
import engine_city as E

OUT=os.path.dirname(__file__)
SHORT={"ENDESA X WAY, S.L.":"Endesa","IBERDROLA CLIENTES S.A.U":"Iberdrola","AMB公共网络":"AMB",
       "BARCELONA DE SERVEIS MUNICIPALS, SA":"BSM-Endolla","REPSOL SOLUCIONES ENERGÉTICAS SA":"Repsol",
       "Etecnic Movilidad Electrica, SRL":"Etecnic"}
def short(op): return SHORT.get(op,op[:14])

def timeline(m):
    T0=m["T0"]
    mins=[round((t-T0)/60,1) for t,_ in m["ctrl_mw_series"]]
    cmw=[v for _,v in m["ctrl_mw_series"]]
    aff=[a for _,a in m["per_tick"]]
    det={short(o):(round((v-T0)/60,1) if v else None) for o,v in m["t_detect"].items()}
    rec={short(o):(round((v-T0)/60,1) if v else None) for o,v in m["recovery"].items()}
    return {"mins":mins,"ctrl_mw":[round(v,3) for v in cmw],"aff":aff,"detect":det,"recovery":rec,
            "dE":m["dE_kwh"],"n_aff":m["n_affected"],"ctrlMW":m["ctrl_mw"],"compromised":[short(o) for o in m["compromised"]]}

async def main():
    endesa={E.OPS[0]}; top5=set(E.OPS[:5])
    scen={}
    scen["single_d0"]=timeline(await E.run_city(endesa,"curtail",{},seed=1))
    scen["single_iso"]=timeline(await E.run_city(endesa,"curtail",{"isolate":True},seed=1))
    scen["campaign_d0"]=timeline(await E.run_city(top5,"curtail",{},seed=1))
    scen["campaign_iso"]=timeline(await E.run_city(top5,"curtail",{"isolate":True},seed=1))
    # geo: all 621 sites
    sites=[{"lid":r.lid,"op":short(r.operator),"lon":r.lon,"lat":r.lat,"cap":round(float(r.rated),1),
            "src":r.src,"top":(r.operator in E.OPS[:8])} for r in E.LOC.itertuples()]
    ops=[{"op":short(op),"full":op,"mw":E.OP_MW[op],"n":len(E.OP_LOCS[op]),
          "share":round(E.OP_MW[op]/E.CITY_MW,4)} for op in E.OPS[:12]]
    out={"sites":sites,"operators":ops,"scen":scen,
         "meta":{"n_loc":len(E.ALL),"n_op":len(E.OPS),"mw":E.CITY_MW,"amb":len(E.AMB_LOCS),"day":E.DAY}}
    json.dump(out,open(os.path.join(OUT,"artifact_data_city.json"),"w"),ensure_ascii=False,separators=(",",":"))
    print(f"[SAVED] artifact_data_city.json ({os.path.getsize(os.path.join(OUT,'artifact_data_city.json'))/1024:.0f} KB)")
    for k,v in scen.items(): print(f"  {k}: dE={v['dE']} n_aff={v['n_aff']} comp={v['compromised']}")

if __name__=="__main__":
    asyncio.run(main())
