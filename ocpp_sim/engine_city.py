"""City-scale, multi-operator OCPP 1.6 attack/defense emulation (Barcelona AMB).

The metropolitan control plane is NOT one network but 37 independent operator
CSMS backends over 621 registered locations (DGT NAP). This engine instantiates
every location as a real `ocpp` charge point over a real websocket, groups them
by operator (= one logical CSMS control domain each), and lets an attacker
compromise one or several backends. A per-operator detector (command-rate +
scale*rhythm power consistency) and containment (isolate+recover) run per domain.

Demand model (clean macro/micro split, no mixing):
  * AMB operator  (src=AMB, 71 locations) -> REAL measured sessions. This is the
    single high-fidelity "calibration cell": identical physics to engine2.py.
  * 36 DGT operators (src=DGT, 550 locations) -> capacity-grounded scale*rhythm
    synthetic demand: scale = each location's DGT-registered kW; rhythm = the
    per-zone utilisation shape MEASURED from the AMB cell. Nothing is invented
    beyond the registered capacity (real) and the measured zone rhythm (real).

A discrete 1-min virtual clock (decoupled from wall time) drives real OCPP
messages. Metrics come from the real event timeline. Deterministic.
"""
import asyncio, logging, random, os, sqlite3
from datetime import datetime, timezone
import numpy as np, pandas as pd, shapely.wkb
from pyproj import Transformer
import websockets

_T2WGS=Transformer.from_crs("EPSG:25831","EPSG:4326",always_xy=True)
def to_wgs(x,y):
    lon,lat=_T2WGS.transform(x,y); return round(lon,5),round(lat,5)
from ocpp.v16 import ChargePoint as CP, call, call_result
from ocpp.routing import on
from ocpp.v16.enums import Action, RegistrationStatus

logging.getLogger("ocpp").setLevel(logging.CRITICAL); logging.getLogger("websockets").setLevel(logging.CRITICAL)
DATA=os.environ.get("AMB_DATA","/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/amb_data/supp")
PORT=int(os.environ.get("CITY_PORT","9773"))
DAY="2025-12-05"; W0=16*3600; W1=22*3600; T0=18*3600; STEP=60; MV_EVERY=10*60
TF=2.2; TARIFF=0.30
# rated-capacity weights (kW) by DC class for the capacity proxy
W_DC100=150.0; W_DC=50.0; W_AC=22.0
# sequential-controller constants (for the Shiryaev/CUSUM in-engine decision modes, calibrated as in optstop.py)
import math
DELTA_C=0.5; SIG_C=0.39; RHO_C=1/500.0
def _llr_c(r,delta=DELTA_C,sigma=SIG_C):
    """log-likelihood ratio of r under H1=N(1-delta,sigma) vs H0=N(1,sigma)."""
    return (-0.5*((r-(1.0-delta))/sigma)**2) - (-0.5*((r-1.0)/sigma)**2)

# ----------------------------------------------------------------------------- data
def _gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]; return shapely.wkb.loads(bytes(b[hdr:]))

def load_amb_real():
    """AMB calibration cell: real sessions + per-site rated capacity + geometry."""
    r=pd.read_csv(os.path.join(DATA,"charging_records_clean.csv"),
        usecols=["station","start_date","start_dt","duration_min","energy_kwh","charge_type"],low_memory=False)
    m=pd.read_csv(os.path.join(DATA,"station_mapping_v2.csv")); s2id=dict(zip(m.station,m.site_id))
    r["d"]=pd.to_datetime(r["start_date"],format="mixed",errors="coerce").dt.date.astype(str)
    r=r[r.d==DAY].copy(); r["site"]=r.station.map(s2id); r=r.dropna(subset=["site"])
    sd=pd.to_datetime(r.start_dt,format="mixed",errors="coerce")
    r["t0"]=sd.dt.hour*3600+sd.dt.minute*60+sd.dt.second
    r["dur"]=r.duration_min.clip(lower=1).fillna(1)*60; r["t1"]=r.t0+r["dur"]
    r["pkw"]=(r.energy_kwh/(r["dur"]/3600)).clip(upper=160)
    r=r[(r.t1>W0)&(r.t0<W1)]
    sess=r[["site","t0","t1","pkw","energy_kwh"]].reset_index(drop=True)
    con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
    cols=[c[1] for c in con.execute('PRAGMA table_info("amb_sites")')]
    a=pd.DataFrame(con.execute('SELECT * FROM "amb_sites"').fetchall(),columns=cols)
    a["g"]=a["geom"].apply(_gpkg_geom)
    a["lon"]=a.g.apply(lambda p:to_wgs(p.x,p.y)[0]); a["lat"]=a.g.apply(lambda p:to_wgs(p.x,p.y)[1])
    a["rated"]=(a.n_ac_pts.fillna(0)*W_AC+a.n_dc40_pts.fillna(0)*W_DC+a.n_dc100_pts.fillna(0)*W_DC100).clip(lower=W_AC)
    con.close()
    amb=a[["site_id","muni","zone_zh","lon","lat","rated"]].rename(columns={"site_id":"lid"}).copy()
    amb["operator"]="AMB公共网络"; amb["src"]="AMB"
    return sess, amb

def load_dgt_locations():
    """550 DGT locations across 36 operators: geometry, zone, DC class, operator."""
    con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
    cols=[c[1] for c in con.execute('PRAGMA table_info("registry_locations")')]
    rl=pd.DataFrame(con.execute('SELECT * FROM "registry_locations"').fetchall(),columns=cols)
    con.close()
    rl=rl[rl.src=="DGT"].copy()
    rl["g"]=rl["geom"].apply(lambda b:_gpkg_geom(b) if b is not None else None)
    rl=rl[rl.g.notna()].copy()
    # reproject? registry_locations geom already WGS84 in this gpkg (used by console); guard:
    rl["lon"]=rl.g.apply(lambda p:to_wgs(p.x,p.y)[0]); rl["lat"]=rl.g.apply(lambda p:to_wgs(p.x,p.y)[1])
    rl["w"]=np.where(rl.has_dc100==1,W_DC100,np.where(rl.has_dc==1,W_DC,W_AC))
    return rl[["loc_id","operator","zone_zh","lon","lat","has_dc","has_dc100","w"]].rename(columns={"loc_id":"lid"})

def operator_mw():
    """DGT registered MW per operator (name key) -> to size DGT locations exactly."""
    D=os.path.join(DATA,"dgt_nap")
    P=pd.read_csv(os.path.join(D,"dgt_refill_points_amb.csv"),dtype={"site_id":str})
    S=pd.read_csv(os.path.join(D,"dgt_sites_amb.csv"),dtype={"site_id":str},low_memory=False)
    P=P.merge(S[["site_id","operator"]],on="site_id",how="left")
    return P.groupby("operator")["max_kw"].sum().to_dict()   # kW

# ----------------------------------------------------------------------------- build city
def build_city():
    sess, amb = load_amb_real()
    dgt = load_dgt_locations()
    opkw = operator_mw()
    # size DGT locations so each operator's total == its DGT registered kW (real)
    caps=[]
    for op,grp in dgt.groupby("operator"):
        tot=opkw.get(op)
        w=grp.w.values
        if tot and w.sum()>0:
            cap=w/w.sum()*tot
        else:
            cap=w.copy()                      # fallback: weight as absolute kW
        caps.append(pd.Series(cap,index=grp.index))
    dgt["rated"]=pd.concat(caps).reindex(dgt.index).round(1)
    dgt["src"]="DGT"
    # unified location table
    cols=["lid","operator","zone_zh","lon","lat","rated","src"]
    LOC=pd.concat([amb[cols], dgt[cols]],ignore_index=True)
    LOC=LOC.drop_duplicates("lid").reset_index(drop=True)
    # zone utilisation rhythm rho_zone(T) measured from the AMB real cell
    sess_rec=sess.to_dict("records")
    amb_zone={r.lid:r.zone_zh for r in amb.itertuples()}
    amb_rated_by_zone=amb.groupby("zone_zh").rated.sum().to_dict()
    ticks=list(range(W0,W1,STEP))
    # delivered AMB power by zone & tick
    rho={}; city_shape={}
    for z in amb.zone_zh.unique():
        cap_z=amb_rated_by_zone.get(z,1.0)
        rho[z]={}
        for T in ticks:
            p=sum(s["pkw"] for s in sess_rec if s["site"] in amb_zone and amb_zone[s["site"]]==z and s["t0"]<=T<s["t1"])
            rho[z][T]=min(p/cap_z if cap_z>0 else 0.0, 1.0)
    # city-aggregate fallback shape (for zones absent from AMB)
    cap_all=amb.rated.sum()
    for T in ticks:
        p=sum(s["pkw"] for s in sess_rec if s["t0"]<=T<s["t1"])
        city_shape[T]=min(p/cap_all if cap_all>0 else 0.0,1.0)
    def rho_of(zone,T):
        if zone in rho and sum(rho[zone].values())>0: return rho[zone][T]
        return city_shape[T]
    return LOC, sess, rho_of, ticks

LOC, SESS, RHO, TICKS = build_city()
OPS=sorted(LOC.operator.unique(), key=lambda o:-LOC[LOC.operator==o].rated.sum())
OP_LOCS={op:list(LOC[LOC.operator==op]["lid"]) for op in OPS}
OP_MW={op:round(LOC[LOC.operator==op].rated.sum()/1000,3) for op in OPS}
LOC_OP=dict(zip(LOC["lid"],LOC.operator)); LOC_CAP=dict(zip(LOC["lid"],LOC.rated)); LOC_ZONE=dict(zip(LOC["lid"],LOC.zone_zh))
ALL=list(LOC["lid"]); AMB_LOCS=set(LOC[LOC.src=="AMB"]["lid"])
SAFE={lid:f"L{i}" for i,lid in enumerate(ALL)}; SAFE2LID={v:k for k,v in SAFE.items()}  # URL-safe ws path per location
CITY_MW=round(LOC.rated.sum()/1000,2)
print(f"[CITY] {len(ALL)} locations, {len(OPS)} operators, {CITY_MW} MW registered | AMB cell={len(AMB_LOCS)} real-session sites")
print("[TOP] "+", ".join(f"{op}={OP_MW[op]}MW/{len(OP_LOCS[op])}" for op in OPS[:5]))

# ----------------------------------------------------------------------------- OCPP
class CSMS(CP):
    @on(Action.boot_notification)
    def b(self,charge_point_model,charge_point_vendor,**k):
        return call_result.BootNotification(current_time=datetime.now(timezone.utc).isoformat(),interval=300,status=RegistrationStatus.accepted)
    @on(Action.authorize)
    def a(self,id_tag,**k): return call_result.Authorize(id_tag_info={"status":"Accepted"})
    @on(Action.start_transaction)
    def s(self,connector_id,id_tag,meter_start,timestamp,**k): return call_result.StartTransaction(transaction_id=1,id_tag_info={"status":"Accepted"})
    @on(Action.meter_values)
    def mv(self,connector_id,meter_value,**k): return call_result.MeterValues()
    @on(Action.stop_transaction)
    def st(self,meter_stop,timestamp,transaction_id,**k): return call_result.StopTransaction(id_tag_info={"status":"Accepted"})
    @on(Action.heartbeat)
    def h(self,**k): return call_result.Heartbeat(current_time=datetime.now(timezone.utc).isoformat())
class Charger(CP):
    @on(Action.set_charging_profile)
    def scp(self,connector_id,cs_charging_profiles,**k): return call_result.SetChargingProfile(status="Accepted")
    @on(Action.remote_stop_transaction)
    def rst(self,transaction_id,**k): return call_result.RemoteStopTransaction(status="Accepted")

def now_iso(): return datetime.now(timezone.utc).isoformat()

async def run_city(compromised, vector="curtail", defense=None, seed=0, t0_attack=T0, rate=30, detector="fused",
                   curtail_frac=1.0, decision="fixed", astar=None, sync_gate=0):
    """compromised: set/list of operator names whose CSMS backend is owned by the attacker.
       vector in {curtail, remote_stop, mitm_meter, dos}. defense dict: {rate_limit, isolate}.
       detector in {fused, rate, consist}: which detection signal(s) are active (for ablation).
       curtail_frac in (0,1]: fraction of each controlled load removed (1.0=full blackout, <1=stealthy partial).
       decision in {fixed, shiryaev, cusum}: isolation trigger rule (fixed heuristic vs sequential controller);
         astar = per-operator posterior threshold dict (shiryaev) or a scalar statistic threshold (cusum).
       sync_gate>0: suppress isolation when >=sync_gate backends drop out-of-band in the SAME tick
         (a network-wide-synchronous drop = benign grid event, e.g. a blackout, not a localised attack)."""
    defense=defense or {}; rng=random.Random(seed); cmap={}
    comp=set(compromised)
    async def handler(ws,*a):
        cid=(getattr(ws,"path",None) or ws.request.path).strip("/"); lid=SAFE2LID.get(cid,cid)
        cp=CSMS(lid,ws); cmap[lid]=cp                 # cmap keyed by canonical location id
        try: await cp.start()
        except Exception: pass
    srv=await websockets.serve(handler,"127.0.0.1",PORT,subprotocols=["ocpp1.6"]); await asyncio.sleep(0.15)
    chargers={}; start_tasks=[]
    for loc in ALL:
        ws=await websockets.connect(f"ws://127.0.0.1:{PORT}/{SAFE[loc]}",subprotocols=["ocpp1.6"])
        cp=Charger(loc,ws); chargers[loc]=cp; start_tasks.append(asyncio.create_task(cp.start()))
    await asyncio.sleep(0.25)
    await asyncio.gather(*[chargers[l].call(call.BootNotification(charge_point_model="AMB",charge_point_vendor="sim")) for l in ALL],return_exceptions=True)

    sess=SESS.to_dict("records")
    active={}; started=set()
    # per-operator attack bookkeeping
    curtail_start={}; tamper_start={}; aborted=set()
    fan_idx={op:0 for op in comp}; cmd_log={op:[] for op in OPS}; kcons={op:0 for op in OPS}
    t_detect={op:None for op in OPS}; recovery={op:None for op in OPS}; stopped={op:False for op in OPS}
    post={op:0.0 for op in OPS}; scum={op:0.0 for op in OPS}   # sequential-controller state (shiryaev/cusum)
    nlow_prev=0                                                 # #backends out-of-band last tick (synchrony gate)
    ctrl_mw_series=[]; obs_series=[]; per_tick=[]
    rl=defense.get("rate_limit")

    async def send(loc,payload):
        try: return await chargers[loc].call(payload)
        except Exception: return None
    PROF={"charging_profile_id":1,"stack_level":0,"charging_profile_purpose":"TxDefaultProfile","charging_profile_kind":"Absolute",
          "charging_schedule":{"charging_rate_unit":"W","charging_schedule_period":[{"start_period":0,"limit":0.0}]}}

    def loc_power(loc,T):
        """scheduled (benign) active power at loc,T."""
        if loc in AMB_LOCS:
            return sum(a[1] for a in active.get(loc,[]) if a[0]>T)
        return LOC_CAP[loc]*RHO(LOC_ZONE[loc],T)      # DGT synthetic = scale*rhythm

    for T in TICKS:
        calls=[]
        # AMB real sessions start this tick
        for i,s in enumerate(sess):
            if i not in started and T<=s["t0"]<T+STEP:
                started.add(i); active.setdefault(s["site"],[]).append([s["t1"],s["pkw"]])
                calls.append(send(s["site"],call.StartTransaction(connector_id=1,id_tag="R",meter_start=0,timestamp=now_iso())))
        for loc in AMB_LOCS:
            active[loc]=[a for a in active.get(loc,[]) if a[0]>T]
        # attacker fan-out per compromised backend (only once the campaign begins)
        for op in (comp if T>=t0_attack else set()):
            if stopped[op]: continue
            budget=rl if rl is not None else rate; n=0
            locs=OP_LOCS[op]
            while fan_idx[op]<len(locs) and n<budget:
                loc=locs[fan_idx[op]]; fan_idx[op]+=1
                if loc not in cmap: continue
                if vector=="mitm_meter":
                    tamper_start.setdefault(loc,T); n+=1          # link MitM: no CSMS command
                elif vector=="remote_stop":
                    calls.append(cmap[loc].call(call.RemoteStopTransaction(transaction_id=1))); aborted.add(loc)
                    curtail_start.setdefault(loc,T); cmd_log[op].append(T); n+=1
                elif vector=="dos":
                    curtail_start.setdefault(loc,T); cmd_log[op].append(T); n+=1
                else:  # curtail
                    calls.append(cmap[loc].call(call.SetChargingProfile(connector_id=0,cs_charging_profiles=PROF)))
                    curtail_start.setdefault(loc,T); cmd_log[op].append(T); n+=1
        # periodic MeterValues (light real messages, a sample of active locations)
        if (T-W0)%MV_EVERY==0:
            samp=[l for l in ALL if loc_power(l,T)>0][:120]
            for loc in samp:
                op=LOC_OP[loc]; rec=recovery[op]
                cut=loc in curtail_start and (rec is None or T<rec)
                tmp=loc in tamper_start and (rec is None or T<rec)
                p=loc_power(loc,T)*(1.0-curtail_frac) if cut else loc_power(loc,T)*(TF if tmp else 1.0)
                calls.append(send(loc,call.MeterValues(connector_id=1,meter_value=[{"timestamp":now_iso(),"sampled_value":[{"value":str(round(p,1)),"measurand":"Power.Active.Import"}]}])))
        if calls: await asyncio.gather(*calls,return_exceptions=True)

        # observed power + controlled power + per-operator detector
        ctrl=0.0; obs=0.0; aff_now=0; nlow=0
        sync=(sync_gate>0 and nlow_prev>=sync_gate)            # last tick was a network-wide synchronous drop -> grid event
        for op in OPS:
            rec=recovery[op]; active_atk=(rec is None or T<rec)
            exp_op=0.0; obs_op=0.0; ctrl_op=0.0
            for loc in OP_LOCS[op]:
                base=loc_power(loc,T); exp_op+=base
                cut=loc in curtail_start and active_atk
                tmp=loc in tamper_start and active_atk
                reported=base*(1.0-curtail_frac) if cut else (base*TF if tmp else base)
                obs_op+=reported
                if (cut or (loc in curtail_start)) and active_atk: ctrl_op+=base*curtail_frac
            obs+=obs_op; ctrl+=ctrl_op
            if exp_op>5 and obs_op<0.5*exp_op: nlow+=1          # out-of-band (low) this tick, for the synchrony gate
            if active_atk: aff_now+=sum(1 for loc in OP_LOCS[op] if (loc in curtail_start or loc in tamper_start))
            # detector (per operator backend)
            rate_cnt=sum(1 for c in cmd_log[op] if T-120<=c<=T)
            alarm=False
            if decision=="fixed":
                if detector in ("rate","fused") and rate_cnt>=5: alarm=True
                if exp_op>5 and (obs_op<0.5*exp_op or obs_op>1.5*exp_op): kcons[op]+=1
                else: kcons[op]=0
                if detector in ("consist","fused") and kcons[op]>=2: alarm=True
            else:
                # sequential controller on the consistency ratio r=obs/exp (optstop.py brought inside the engine)
                r_t=(obs_op/exp_op) if exp_op>5 else 1.0
                llr=_llr_c(r_t)
                if decision=="shiryaev":
                    pre=post[op]+RHO_C*(1-post[op]); L=math.exp(min(llr,50.0)); num=pre*L
                    den=num+(1-RHO_C)*(1-post[op]); post[op]=num/max(den,1e-300)
                    A=(astar.get(op,0.9) if isinstance(astar,dict) else (astar if astar is not None else 0.9))
                    if post[op]>=A: alarm=True
                elif decision=="cusum":
                    scum[op]=max(0.0,scum[op]+llr)
                    if scum[op]>=(astar if astar is not None else 6.0): alarm=True
            if alarm and (not sync) and t_detect[op] is None and op in comp and T>=t0_attack:
                t_detect[op]=T
                if defense.get("isolate"): recovery[op]=T+60; stopped[op]=True
        nlow_prev=nlow
        ctrl_mw_series.append((T,round(ctrl/1000,3))); obs_series.append((T,round(obs/1000,3)))
        per_tick.append((T,aff_now))

    # ---- energy / billing accounting from the event timeline
    rec_of=lambda op:(recovery[op] if recovery[op] else W1)
    dE=0.0; denied=0; billing=0.0
    # AMB (discrete sessions)
    for s in sess:
        op=LOC_OP[s["site"]]
        cs=curtail_start.get(s["site"])
        if cs is not None:
            ov=max(0,min(s["t1"],W1,rec_of(op))-max(s["t0"],W0,cs))
            if ov>0: dE+=s["pkw"]*curtail_frac*ov/3600.0; denied+=(1 if curtail_frac>=0.99 else 0)
        ts=tamper_start.get(s["site"])
        if ts is not None:
            ov=max(0,min(s["t1"],W1,rec_of(op))-max(s["t0"],W0,ts))
            if ov>0: billing+=s["pkw"]*ov/3600.0*(TF-1)*TARIFF
    # DGT (continuous scheduled power integrated over curtailed interval)
    for loc in ALL:
        if loc in AMB_LOCS: continue
        op=LOC_OP[loc]; rec=rec_of(op)
        cs=curtail_start.get(loc); ts=tamper_start.get(loc)
        if cs is not None:
            e=sum(loc_power(loc,T)*STEP/3600.0 for T in TICKS if cs<=T<rec)*curtail_frac
            if e>0: dE+=e; denied+=(1 if curtail_frac>=0.99 else 0)
        if ts is not None:
            e=sum(loc_power(loc,T)*STEP/3600.0 for T in TICKS if ts<=T<rec)
            billing+=e*(TF-1)*TARIFF
    affected=sorted(set(curtail_start)|set(tamper_start))
    peak_mw=max((m for _,m in ctrl_mw_series),default=0.0)
    # per-operator summary
    per_op={}
    for op in comp:
        locs_hit=[l for l in OP_LOCS[op] if l in curtail_start or l in tamper_start]
        per_op[op]={"n_loc":len(locs_hit),"mw":OP_MW[op],
                    "tau_d":round((t_detect[op]-t0_attack)/60,1) if t_detect[op] else None,
                    "recovery":round((recovery[op]-t0_attack)/60,1) if recovery[op] else None}
    # teardown (quiet)
    for t in start_tasks: t.cancel()
    for l in ALL:
        try: await chargers[l]._connection.close()
        except Exception: pass
    srv.close(); await srv.wait_closed()
    await asyncio.gather(*start_tasks,return_exceptions=True)
    return dict(vector=vector, compromised=sorted(comp), defense=defense,
                affected=affected, n_affected=len(affected), dE_kwh=round(dE,1),
                denied=denied, billing_eur=round(billing,1), ctrl_mw=round(peak_mw,3),
                t_detect={o:t_detect[o] for o in comp}, recovery={o:recovery[o] for o in comp},
                W0=W0,T0=t0_attack,W1=W1, ctrl_mw_series=ctrl_mw_series, obs_series=obs_series,
                per_tick=per_tick, per_op=per_op)

if __name__=="__main__":
    async def main():
        print("\n=== single-backend compromise (curtail), no defense vs detect+isolate ===")
        for op in OPS[:5]:
            m0=await run_city({op},"curtail",{},seed=1)
            m1=await run_city({op},"curtail",{"isolate":True},seed=1)
            taud=m1["per_op"][op]["tau_d"]
            print(f"{op[:22]:22s} MW={OP_MW[op]:5.2f} loc={len(OP_LOCS[op]):3d} | "
                  f"D0 dE={m0['dE_kwh']:7.1f} aff={m0['n_affected']:3d} ctrlMW={m0['ctrl_mw']:5.2f} | "
                  f"ISO dE={m1['dE_kwh']:6.1f} tau_d={taud}min")
        print("\n=== coordinated campaign: compromise top-k by MW (curtail, no defense) ===")
        for k in [1,2,3,5,8]:
            ops=set(OPS[:k]); m=await run_city(ops,"curtail",{},seed=1)
            print(f"k={k:2d} ops ({sum(OP_MW[o] for o in ops):5.1f} MW) -> dE={m['dE_kwh']:8.1f} kWh aff={m['n_affected']:3d} ctrlMW={m['ctrl_mw']:6.2f}")
    asyncio.run(main())
