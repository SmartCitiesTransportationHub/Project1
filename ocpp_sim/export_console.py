"""Export map geometry + real OCPP-sim timelines for 4 attack vectors x 3 defenses,
detector telemetry, OCPP message streams, and the OCPP-version feasibility gate,
into artifact_data.json for the 3D interactive command console (V4)."""
import os, json, sqlite3, asyncio
import numpy as np, pandas as pd, shapely.wkb
from shapely.geometry import mapping
import engine2 as E
DATA=E.DATA; OUT=os.path.dirname(__file__); W0,T0G,W1=E.W0,E.T0,E.W1
def gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]; return shapely.wkb.loads(bytes(b[hdr:]))
def layer(con,name,simp=0):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    df=pd.DataFrame(con.execute(f'SELECT * FROM "{name}"').fetchall(),columns=cols)
    df["g"]=df["geom"].apply(lambda b:(gpkg_geom(b).simplify(simp) if simp else gpkg_geom(b)) if b is not None else None); return df
def rnd(o,n=1):
    if isinstance(o,float): return round(o,n)
    if isinstance(o,(list,tuple)): return [rnd(x,n) for x in o]
    return o
con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
muni=layer(con,"municipalities",40); bnd=layer(con,"amb_boundary",40); sites=layer(con,"amb_sites"); reg=layer(con,"registry_locations")
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
geo={"muni":feats(muni,["nommuni"]),"boundary":feats(bnd,["name"]),
     "sites":feats(sites,["site_id","name","muni","cfg_label","sess_day","in_dgt","zone_zh"],extra=lambda r:{"pkw":site_pkw.get(r["site_id"],0.0)}),
     "registry":feats(reg,["has_dc"])}
print("[GEO] muni",len(geo["muni"]),"sites",len(geo["sites"]),"reg",len(geo["registry"]))
SESS=E.SESS.to_dict("records")
def expected_mw(ts): return sum(s["pkw"] for s in SESS if s["t0"]<=ts<s["t1"])/1000.0

VECTORS=[
 {"key":"curtail","label":"A3 后台沦陷·限功率","mode":"curtail","kind":"cut","hmult":0.12,"unit":"MWh","prim":"dE_kwh"},
 {"key":"stop","label":"A3 后台沦陷·批量停充","mode":"remote_stop","kind":"cut","hmult":0.0,"unit":"MWh","prim":"dE_kwh"},
 {"key":"mitm","label":"A1 中间人·篡改电表","mode":"mitm_meter","kind":"tamper","hmult":2.2,"unit":"€","prim":"billing_eur"},
 {"key":"dos","label":"A4 后台 DoS·洪泛","mode":"dos","kind":"offline","hmult":0.15,"unit":"会话","prim":"denied"},
]
DEFENSES=[{"key":"none","label":"D0 无防御","d":{}},
          {"key":"iso","label":"D3+D5 检测+隔离","d":{"isolate":True}},
          {"key":"rliso","label":"D2+D3+D5 限速+隔离","d":{"rate_limit":2,"isolate":True}}]
# OCPP version feasibility gate (consistent with reachability analysis, fig13)
VERSIONS=[{"key":"1.6","label":"OCPP 1.6 明文","feasible":{"curtail":1,"stop":1,"mitm":1,"dos":1}},
          {"key":"2.0.1","label":"OCPP 2.0.1 TLS","feasible":{"curtail":1,"stop":1,"mitm":0,"dos":1}},
          {"key":"2.1","label":"OCPP 2.1 P&C","feasible":{"curtail":1,"stop":1,"mitm":0,"dos":1}}]

async def one(vec,dfn):
    m=await E.run_scenario({"mode":vec["mode"],"rate":30},dfn,seed=1,with_attack=True,t0_attack=18*3600)
    T0=m["T0"]; R=2 if dfn.get("rate_limit") else 30
    aff=[s for s in E.FANOUT if s in m["affected"]]
    attack={s:round(i/R,3) for i,s in enumerate(aff)}       # fine min from attack, fanout order
    td=round((m["t_detect"]-T0)/60,2) if m["t_detect"] else None
    rec=round((m["recovery"]-T0)/60,2) if m["recovery"] else None
    ser=m["ctrl_mw_series"]; mins=[round((t-T0)/60,1) for t,_ in ser]; cmw=[round(v,3) for _,v in ser]
    csites=[]; ratioS=[]; cmdrateS=[]; billS=[]; finev=sorted(attack.values()); TARIFF=0.30
    for (t,_),cm in zip(ser,cmw):
        tmin=(t-T0)/60; exp=expected_mw(t)
        nact=sum(1 for ct in attack.values() if ct<=tmin and (rec is None or tmin<rec)); csites.append(nact)
        if vec["kind"]=="tamper":
            obs=exp + sum(s["pkw"] for s in SESS if s["t0"]<=t<s["t1"] and s["site"] in {k for k,ct in attack.items() if ct<=tmin and (rec is None or tmin<rec)})*(2.2-1)/1000.0
        else:
            obs=max(0.0,exp-cm)
        ratioS.append(round(obs/exp,3) if exp>0.05 else 1.0)
        cmdrateS.append(0 if vec["kind"]=="tamper" else sum(1 for v in finev if tmin-2<v<=tmin))
        # cumulative billing deviation (€) for tamper
        if vec["kind"]=="tamper":
            dev=sum(s["pkw"] for s in SESS if s["t0"]<=t<s["t1"] and s["site"] in attack and attack[s["site"]]<=tmin and (rec is None or tmin<rec))*(2.2-1)*TARIFF/60.0
            billS.append(round((billS[-1] if billS else 0)+dev,2))
        else: billS.append(0)
    # message stream
    stream=[]; add=lambda t,k,x: stream.append({"t":round(t,2),"k":k,"x":x})
    for s in sorted([x for x in SESS if T0-600<=x["t0"]<T0+1500],key=lambda s:s["t0"])[:10]:
        add((s["t0"]-T0)/60,"ok",f"{s['site']} → StartTransaction {s['pkw']:.0f} kW")
    HEAD={"curtail":"⚠ CSMS compromised — SetChargingProfile fan-out","stop":"⚠ CSMS compromised — RemoteStop fan-out",
          "mitm":"⚠ link MitM — falsifying MeterValues","dos":"⚠ CSMS flood — connection/heartbeat storm"}
    add(0,"atk",HEAD[vec["key"]])
    for s,ct in sorted(attack.items(),key=lambda kv:kv[1]):
        msg={"curtail":f"CSMS → {s} SetChargingProfile(limit=0W)","stop":f"CSMS → {s} RemoteStopTransaction",
             "mitm":f"MitM ✎ {s} MeterValues ×2.2 (falsified)","dos":f"flood ✕ {s} offline (unreachable)"}[vec["key"]]
        add(ct,"atk",msg)
    if td is not None:
        which="command/connection-rate ≥5" if vec["kind"]!="tamper" else "scale×rhythm ratio out-of-band"
        add(td,"alarm",f"⚑ DETECTOR ALARM — {which}")
    if rec is not None: add(rec,"contain",f"⛉ isolate backend → {len(attack)} sites recover")
    else: add(min(mins[-1],60),"atk",f"no containment — {len(attack)} sites held")
    stream.sort(key=lambda e:e["t"]); stream=stream[:200]
    return {"attack":attack,"kind":vec["kind"],"hmult":vec["hmult"],"t_detect":td,"recovery":rec,
            "mins":mins,"ctrl_mw":cmw,"ctrl_sites":csites,"ratio":ratioS,"cmdrate":cmdrateS,"bill":billS,"stream":stream,
            "metrics":{"dE_kwh":m["dE_kwh"],"denied":m["denied"],"billing_eur":m["billing_eur"],
                       "n_affected":m["n_affected"],"ctrl_mw":m["ctrl_mw"],"tau_d":m["tau_d_min"],"recovery":m["recovery_min"]}}
async def main():
    sim={}
    for v in VECTORS:
        sim[v["key"]]={}
        for d in DEFENSES:
            sim[v["key"]][d["key"]]=await one(v,d["d"])
            mm=sim[v["key"]][d["key"]]["metrics"]
            print(f"[{v['key']:8s}|{d['key']:6s}] aff={mm['n_affected']:3d} dE={mm['dE_kwh']:6.1f} €={mm['billing_eur']:5.1f} denied={mm['denied']:4d} tau={mm['tau_d']} rec={mm['recovery']}")
    return sim
sim=asyncio.run(main())
meta={"day":E.DAY,"n_sites":len(E.SITES),"peak_mw":0.9}
json.dump({"geo":geo,"sim":sim,"vectors":VECTORS,"defenses":DEFENSES,"versions":VERSIONS,"meta":meta},
          open(os.path.join(OUT,"artifact_data.json"),"w"),ensure_ascii=False,separators=(",",":"))
print(f"[SAVED] artifact_data.json ({os.path.getsize(os.path.join(OUT,'artifact_data.json'))/1024:.0f} KB)")
