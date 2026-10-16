"""Run the city-scale attack/defense matrix and export:
  results_city.json        -> measured numbers for the paper (macro) tables
  artifact_data_city.json  -> geometry + timelines for the 3D multi-operator console

Macro scenarios (whole-city, multi-operator):
  S1 single-backend compromise per major operator (curtail): D0 vs detect+isolate
  S2 coordinated campaign: compromise top-k operators by MW (k=1..K), curtail, D0
  S3 city vector comparison: compromise the top-3 backends x {curtail,stop,mitm,dos} x {D0,iso,rl+iso}
The AMB subset of any run reproduces the micro (real-session) calibration cell.
"""
import os, json, asyncio, sqlite3
import numpy as np, pandas as pd, shapely.wkb
from shapely.geometry import mapping
from pyproj import Transformer
import engine_city as E

OUT=os.path.dirname(__file__); DATA=E.DATA
_T=Transformer.from_crs("EPSG:25831","EPSG:4326",always_xy=True)
def _geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]; return shapely.wkb.loads(bytes(b[hdr:]))
def _reproj(geom):
    from shapely.ops import transform
    return transform(lambda x,y,z=None:_T.transform(x,y),geom)
def rnd(o,n=4):
    if isinstance(o,float): return round(o,n)
    if isinstance(o,(list,tuple)): return [rnd(x,n) for x in o]
    return o
def layer(con,name,simp=0):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    df=pd.DataFrame(con.execute(f'SELECT * FROM "{name}"').fetchall(),columns=cols)
    df["g"]=df["geom"].apply(lambda b:(_reproj(_geom(b).simplify(simp)) if simp else _reproj(_geom(b))) if b is not None else None)
    return df

# ---- top operators for the paper (by registered MW), with short labels
SHORT={"ENDESA X WAY, S.L.":"Endesa X Way","IBERDROLA CLIENTES S.A.U":"Iberdrola","AMB公共网络":"AMB 公共网络",
       "BARCELONA DE SERVEIS MUNICIPALS, SA":"BSM-Endolla","REPSOL SOLUCIONES ENERGÉTICAS SA":"Repsol",
       "Etecnic Movilidad Electrica, SRL":"Etecnic","Wenea Services Spain, S.L.":"Wenea","Galp Energía España, S.A.U.":"Galp"}
def short(op): return SHORT.get(op,op[:16])
TOPN=8
TOP=E.OPS[:TOPN]

async def run_matrix():
    res={"city":{"n_loc":len(E.ALL),"n_operators":len(E.OPS),"mw":E.CITY_MW,"amb_cell":len(E.AMB_LOCS),"day":E.DAY}}
    # operator inventory
    res["operators"]=[{"op":op,"short":short(op),"mw":E.OP_MW[op],"n_loc":len(E.OP_LOCS[op]),
                       "share":round(E.OP_MW[op]/E.CITY_MW,4)} for op in E.OPS]
    # S1 single-backend compromise
    s1=[]
    for op in TOP:
        m0=await E.run_city({op},"curtail",{},seed=1)
        m1=await E.run_city({op},"curtail",{"isolate":True},seed=1)
        po=m1["per_op"][op]
        s1.append({"op":op,"short":short(op),"mw":E.OP_MW[op],"n_loc":len(E.OP_LOCS[op]),
                   "share":round(E.OP_MW[op]/E.CITY_MW,4),
                   "d0_dE":m0["dE_kwh"],"d0_aff":m0["n_affected"],"d0_ctrlMW":m0["ctrl_mw"],
                   "iso_dE":m1["dE_kwh"],"iso_aff":m1["n_affected"],"tau_d":po["tau_d"],"recovery":po["recovery"]})
        print(f"[S1] {short(op):14s} share={E.OP_MW[op]/E.CITY_MW:5.1%} D0 dE={m0['dE_kwh']:7.1f} ctrlMW={m0['ctrl_mw']:5.2f} | ISO dE={m1['dE_kwh']:6.1f} tau={po['tau_d']}")
    res["s1_single_backend"]=s1
    # S2 coordinated campaign (cumulative over top-k)
    s2=[]
    for k in range(1,TOPN+1):
        ops=set(E.OPS[:k])
        m0=await E.run_city(ops,"curtail",{},seed=1)
        m1=await E.run_city(ops,"curtail",{"isolate":True},seed=1)
        s2.append({"k":k,"ops":[short(o) for o in E.OPS[:k]],"mw":round(sum(E.OP_MW[o] for o in ops),3),
                   "d0_dE":m0["dE_kwh"],"d0_aff":m0["n_affected"],"d0_ctrlMW":m0["ctrl_mw"],
                   "iso_dE":m1["dE_kwh"],"iso_aff":m1["n_affected"]})
        print(f"[S2] k={k} ({sum(E.OP_MW[o] for o in ops):5.1f}MW) D0 dE={m0['dE_kwh']:8.1f} aff={m0['n_affected']:3d} | ISO dE={m1['dE_kwh']:7.1f}")
    res["s2_campaign"]=s2
    # S3 city vector comparison (compromise top-3 backends)
    vset=set(E.OPS[:3])
    VEC=[("curtail","A3 限功率"),("remote_stop","A3 批量停充"),("mitm_meter","A1 篡改电表"),("dos","A4 DoS 洪泛")]
    DEF=[("none",{}),("iso",{"isolate":True}),("rliso",{"rate_limit":2,"isolate":True})]
    s3={}
    for vk,vlab in VEC:
        s3[vk]={"label":vlab}
        for dk,dd in DEF:
            m=await E.run_city(vset,vk,dd,seed=1)
            s3[vk][dk]={"dE":m["dE_kwh"],"billing":m["billing_eur"],"denied":m["denied"],
                        "aff":m["n_affected"],"ctrlMW":m["ctrl_mw"]}
            print(f"[S3] {vk:12s}|{dk:6s} dE={m['dE_kwh']:7.1f} €={m['billing_eur']:7.1f} denied={m['denied']:4d} aff={m['n_affected']:3d}")
    res["s3_vectors_top3"]=s3
    return res

def export_geo():
    con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
    muni=layer(con,"municipalities",30); bnd=layer(con,"amb_boundary",30); con.close()
    def feats(df,props):
        out=[]
        for _,r in df.iterrows():
            if r["g"] is None: continue
            gj=mapping(r["g"]); gj["coordinates"]=rnd(gj["coordinates"],4)
            p={k:(None if pd.isna(r[k]) else r[k]) for k in props}
            out.append({"geometry":gj,"properties":p})
        return out
    # locations as points with operator/cap/src/zone
    sites=[{"lid":r.lid,"op":short(r.operator),"opfull":r.operator,"lon":r.lon,"lat":r.lat,
            "cap":round(float(r.rated),1),"zone":r.zone_zh,"src":r.src} for r in E.LOC.itertuples()]
    return {"muni":feats(muni,["nommuni"]),"boundary":feats(bnd,["name"]),"sites":sites}

async def main():
    res=await run_matrix()
    geo=export_geo()
    json.dump(res,open(os.path.join(OUT,"results_city.json"),"w"),ensure_ascii=False,indent=1)
    print(f"[SAVED] results_city.json ({os.path.getsize(os.path.join(OUT,'results_city.json'))/1024:.0f} KB)")
    # console artifact (geo + headline scenario timelines added by export_city_console.py later)
    json.dump({"geo":geo,"operators":res["operators"],"meta":res["city"]},
              open(os.path.join(OUT,"city_geo.json"),"w"),ensure_ascii=False,separators=(",",":"))
    print(f"[SAVED] city_geo.json ({os.path.getsize(os.path.join(OUT,'city_geo.json'))/1024:.0f} KB)")

if __name__=="__main__":
    asyncio.run(main())
