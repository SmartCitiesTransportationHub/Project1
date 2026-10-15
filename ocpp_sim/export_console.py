"""Export map geometry (EPSG:25831) + real OCPP-sim attack/defense timelines
into one compact artifact_data.json for the interactive GIS console."""
import os, json, sqlite3, asyncio
import numpy as np, pandas as pd
import shapely.wkb
from shapely.geometry import mapping
import engine2 as E

DATA=E.DATA; OUT=os.path.dirname(__file__)
def gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return shapely.wkb.loads(bytes(b[hdr:]))
def layer(con,name,simp=0):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    rows=con.execute(f'SELECT * FROM "{name}"').fetchall()
    df=pd.DataFrame(rows,columns=cols)
    df["g"]=df["geom"].apply(lambda b: (gpkg_geom(b).simplify(simp) if simp else gpkg_geom(b)) if b is not None else None)
    return df
def rnd(obj,n=1):
    if isinstance(obj,float): return round(obj,n)
    if isinstance(obj,(list,tuple)): return [rnd(x,n) for x in obj]
    return obj

con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
muni=layer(con,"municipalities",simp=40); bnd=layer(con,"amb_boundary",simp=40)
sites=layer(con,"amb_sites"); reg=layer(con,"registry_locations")

def feats(df,props):
    out=[]
    for _,r in df.iterrows():
        if r["g"] is None: continue
        geom=mapping(r["g"]); geom["coordinates"]=rnd(geom["coordinates"],1)
        out.append({"geometry":geom,"properties":{k:(None if pd.isna(r[k]) else (float(r[k]) if isinstance(r[k],(np.floating,)) else (int(r[k]) if isinstance(r[k],(np.integer,)) else r[k]))) for k in props}})
    return out

geo={
 "muni":feats(muni,["nommuni"]),
 "boundary":feats(bnd,["name"]),
 "sites":feats(sites,["site_id","name","muni","cfg","cfg_label","sess_day","kwh_day","in_dgt","zone_zh"]),
 "registry":feats(reg,["operator","has_dc","has_dc100","zone_zh"]),
}
print("[GEO] muni",len(geo["muni"]),"sites",len(geo["sites"]),"registry",len(geo["registry"]))

# ---- run 3 configs (fast attack, t0=18:00) capturing per-site timelines ----
CONFIGS=[("D0 无防御",{}),("D3+D5 检测+隔离",{"isolate":True}),("D2+D3+D5 限速+隔离",{"rate_limit":2,"isolate":True})]
async def runall():
    sim={}
    for name,dfn in CONFIGS:
        m=await E.run_scenario({"mode":"curtail","rate":30},dfn,seed=1,with_attack=True,t0_attack=18*3600)
        T0=m["T0"]; W1=m["W1"]
        R=2 if dfn.get("rate_limit") else 30   # attacker send rate (indices/min) in fan-out order
        curtailed=[s for s in E.FANOUT if s in m["curtail_start"]]
        cs={s:round(i/R,3) for i,s in enumerate(curtailed)}   # k-th curtailed site sent at k/R min
        td=(m["t_detect"]-T0)/60 if m["t_detect"] else None
        rec=(m["recovery"]-T0)/60 if m["recovery"] else None
        # per-minute series: ctrl_mw, ctrl_sites, denied
        ser=m["ctrl_mw_series"]; mins=[round((t-T0)/60,1) for t,_ in ser]; cmw=[round(v,3) for _,v in ser]
        # denied cumulative + ctrl_sites per tick
        csites=[]; dsessions=[]
        SESS=E.SESS
        for t,_ in ser:
            tm=t
            tmin=(tm-T0)/60
            active=sum(1 for s,ct in cs.items() if ct<=tmin and (rec is None or tmin<rec))
            csites.append(active)
        dmax=m["denied"]
        sim[name]={"curtail":cs,"t_detect":round(td,2) if td is not None else None,
                   "recovery":round(rec,2) if rec is not None else None,
                   "mins":mins,"ctrl_mw":cmw,"ctrl_sites":csites,
                   "metrics":{"dE_kwh":m["dE_kwh"],"denied":m["denied"],"ctrl_sites":m["ctrl_sites"],
                              "ctrl_mw":m["ctrl_mw"],"tau_d":m["tau_d_min"],"recovery":m["recovery_min"]}}
        print(f"[SIM] {name}: sites_curtailed={len(cs)} tau_d={td} rec={rec} dE={m['dE_kwh']}")
    return sim
sim=asyncio.run(runall())
meta={"day":E.DAY,"window":[16,22],"attack_min":0,"n_sites":len(E.SITES),
      "note":"真实 OCPP 1.6 仿真；坐标 EPSG:25831；时间轴单位=自攻击注入起的分钟"}
json.dump({"geo":geo,"sim":sim,"meta":meta,"configs":[c[0] for c in CONFIGS]},
          open(os.path.join(OUT,"artifact_data.json"),"w"),ensure_ascii=False,separators=(",",":"))
sz=os.path.getsize(os.path.join(OUT,"artifact_data.json"))/1024
print(f"[SAVED] artifact_data.json ({sz:.0f} KB)")
