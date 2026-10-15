"""Export map geometry (EPSG:25831) + real OCPP-sim attack/defense timelines +
detector telemetry + an OCPP message stream, into one artifact_data.json for the
interactive GIS command console (V3)."""
import os, json, sqlite3, asyncio
import numpy as np, pandas as pd
import shapely.wkb
from shapely.geometry import mapping
import engine2 as E

DATA=E.DATA; OUT=os.path.dirname(__file__)
W0,T0G,W1=E.W0,E.T0,E.W1
def gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return shapely.wkb.loads(bytes(b[hdr:]))
def layer(con,name,simp=0):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    df=pd.DataFrame(con.execute(f'SELECT * FROM "{name}"').fetchall(),columns=cols)
    df["g"]=df["geom"].apply(lambda b:(gpkg_geom(b).simplify(simp) if simp else gpkg_geom(b)) if b is not None else None)
    return df
def rnd(o,n=1):
    if isinstance(o,float): return round(o,n)
    if isinstance(o,(list,tuple)): return [rnd(x,n) for x in o]
    return o

con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
muni=layer(con,"municipalities",simp=40); bnd=layer(con,"amb_boundary",simp=40)
sites=layer(con,"amb_sites"); reg=layer(con,"registry_locations")

# representative per-site power (mean session kW) for the live choropleth
site_pkw=E.SESS.groupby("site").pkw.mean().round(1).to_dict()

def feats(df,props,extra=None):
    out=[]
    for _,r in df.iterrows():
        if r["g"] is None: continue
        geom=mapping(r["g"]); geom["coordinates"]=rnd(geom["coordinates"],1)
        p={k:(None if pd.isna(r[k]) else (float(r[k]) if isinstance(r[k],np.floating) else (int(r[k]) if isinstance(r[k],np.integer) else r[k]))) for k in props}
        if extra: p.update(extra(r))
        out.append({"geometry":geom,"properties":p})
    return out

geo={
 "muni":feats(muni,["nommuni"]),
 "boundary":feats(bnd,["name"]),
 "sites":feats(sites,["site_id","name","muni","cfg","cfg_label","sess_day","kwh_day","in_dgt","zone_zh"],
               extra=lambda r:{"pkw":site_pkw.get(r["site_id"],0.0)}),
 "registry":feats(reg,["operator","has_dc","has_dc100"]),
}
print("[GEO] muni",len(geo["muni"]),"sites",len(geo["sites"]),"registry",len(geo["registry"]))

SESS=E.SESS.to_dict("records")
def expected_mw(tsec):  # benign scheduled power at absolute sec
    return sum(s["pkw"] for s in SESS if s["t0"]<=tsec<s["t1"])/1000.0

CONFIGS=[("D0 无防御",{}),("D3+D5 检测+隔离",{"isolate":True}),("D2+D3+D5 限速+隔离",{"rate_limit":2,"isolate":True})]
async def runall():
    sim={}
    for name,dfn in CONFIGS:
        m=await E.run_scenario({"mode":"curtail","rate":30},dfn,seed=1,with_attack=True,t0_attack=18*3600)
        T0=m["T0"]
        R=2 if dfn.get("rate_limit") else 30
        curtailed=[s for s in E.FANOUT if s in m["curtail_start"]]
        cs={s:round(i/R,3) for i,s in enumerate(curtailed)}          # fine curtail min from attack
        td=round((m["t_detect"]-T0)/60,2) if m["t_detect"] else None
        rec=round((m["recovery"]-T0)/60,2) if m["recovery"] else None
        ser=m["ctrl_mw_series"]; mins=[round((t-T0)/60,1) for t,_ in ser]; cmw=[round(v,3) for _,v in ser]
        csites=[]; expS=[]; ratioS=[]; cmdrateS=[]
        finevals=sorted(cs.values())
        for (t,_),cm in zip(ser,cmw):
            tmin=(t-T0)/60
            csites.append(sum(1 for ct in cs.values() if ct<=tmin and (rec is None or tmin<rec)))
            exp=expected_mw(t); expS.append(round(exp,3))
            obs=max(0.0,exp-cm); ratioS.append(round(obs/exp,3) if exp>0.05 else 1.0)
            cmdrateS.append(sum(1 for v in finevals if tmin-2<v<=tmin))   # commands in last 2 min
        # ---- OCPP message stream (real events) ----
        stream=[]
        def ev(t,kind,txt): stream.append({"t":round(t,2),"k":kind,"x":txt})
        # a few ambient normal messages before/around attack
        amb=[s for s in SESS if s["t0"]>=T0-600 and s["t0"]<T0+1800]
        for s in sorted(amb,key=lambda s:s["t0"])[:14]:
            ev((s["t0"]-T0)/60,"ok",f"{s['site']} → StartTransaction  {s['pkw']:.0f} kW")
        ev(0,"atk","⚠ CSMS compromised — begin SetChargingProfile fan-out")
        for s,ct in sorted(cs.items(),key=lambda kv:kv[1]):
            ev(ct,"atk",f"CSMS → {s}  SetChargingProfile(limit=0 W)")
        if td is not None:
            which="command-rate ≥5/2min" if cmdrateS[min(range(len(mins)),key=lambda i:abs(mins[i]-td))]>=5 else "scale×rhythm ratio<0.5"
            ev(td,"alarm",f"⚑ DETECTOR ALARM — {which}")
        if rec is not None:
            ev(rec,"contain",f"⛉ ISOLATE operator backend → clear profiles, {len(cs)} sites recovering")
        else:
            ev(min(mins[-1],60),"atk",f"no containment — {len(cs)} sites held controlled")
        stream.sort(key=lambda e:e["t"])
        if len(stream)>240: stream=stream[:240]
        sim[name]={"curtail":cs,"t_detect":td,"recovery":rec,"mins":mins,"ctrl_mw":cmw,"ctrl_sites":csites,
                   "expected":expS,"ratio":ratioS,"cmdrate":cmdrateS,"stream":stream,
                   "metrics":{"dE_kwh":m["dE_kwh"],"denied":m["denied"],"ctrl_sites":m["ctrl_sites"],
                              "ctrl_mw":m["ctrl_mw"],"tau_d":m["tau_d_min"],"recovery":m["recovery_min"]}}
        print(f"[SIM] {name}: curtailed={len(cs)} tau_d={td} rec={rec} dE={m['dE_kwh']} stream={len(stream)}")
    return sim
sim=asyncio.run(runall())
# site -> muni index for live choropleth
meta={"day":E.DAY,"window":[16,22],"n_sites":len(E.SITES),"peak_mw":0.9,
      "note":"真实 OCPP 1.6 仿真；坐标 EPSG:25831；时间=自攻击注入起的分钟"}
json.dump({"geo":geo,"sim":sim,"meta":meta,"configs":[c[0] for c in CONFIGS]},
          open(os.path.join(OUT,"artifact_data.json"),"w"),ensure_ascii=False,separators=(",",":"))
print(f"[SAVED] artifact_data.json ({os.path.getsize(os.path.join(OUT,'artifact_data.json'))/1024:.0f} KB)")
