"""Real OCPP 1.6 attack/defense emulation (AMB network) with a DISCRETE virtual clock.
Real ocpp messages over real websockets; sim-time advances in 1-min ticks (decoupled from
wall time). A3 backend-compromise (SetChargingProfile=0 / RemoteStop); CSMS-side detector
(command-rate + scale*rhythm power consistency); containment = rate-limit / isolate+recover.
Metrics from the real event timeline. Fast + deterministic.
"""
import asyncio, logging, random, os
from datetime import datetime, timezone
import numpy as np, pandas as pd
import websockets
from ocpp.v16 import ChargePoint as CP, call, call_result
from ocpp.routing import on
from ocpp.v16.enums import Action, RegistrationStatus

logging.getLogger("ocpp").setLevel(logging.CRITICAL); logging.getLogger("websockets").setLevel(logging.CRITICAL)
DATA=os.environ.get("AMB_DATA","/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/amb_data/supp")
PORT=9770
DAY="2025-12-05"; W0=16*3600; W1=22*3600; T0=18*3600; STEP=60; MV_EVERY=10*60

def load_sessions():
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
    return r[["site","t0","t1","pkw","energy_kwh"]].reset_index(drop=True)

SESS=load_sessions(); SITES=sorted(SESS.site.unique())
FANOUT=list(SESS.groupby("site").pkw.sum().sort_values(ascending=False).index)  # busiest first
print(f"[LOAD] {len(SESS)} sessions, {len(SITES)} sites, day {DAY} 16-22h")

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

async def run_scenario(attack,defense,seed=0,with_attack=True,t0_attack=T0):
    rng=random.Random(seed); cmap={}
    async def handler(ws,*a):
        cid=(getattr(ws,"path",None) or ws.request.path).strip("/"); cp=CSMS(cid,ws); cmap[cid]=cp
        try: await cp.start()
        except Exception: pass
    srv=await websockets.serve(handler,"127.0.0.1",PORT,subprotocols=["ocpp1.6"]); await asyncio.sleep(0.15)
    chargers={}
    for site in SITES:
        ws=await websockets.connect(f"ws://127.0.0.1:{PORT}/{site}",subprotocols=["ocpp1.6"])
        cp=Charger(site,ws); chargers[site]=cp; asyncio.create_task(cp.start())
    await asyncio.sleep(0.2)
    await asyncio.gather(*[chargers[s].call(call.BootNotification(charge_point_model="AMB",charge_point_vendor="sim")) for s in SITES],return_exceptions=True)

    active={}                      # site -> (t1, pkw) for current session
    started=set()                  # session indices started
    curtail_start={}; aborted=set()
    power_now={s:0.0 for s in SITES}
    cmd_log=[]; obs_series=[]; ctrl_mw_series=[]
    t_detect=None; recovery=None; attack_stopped=[False]
    sess=SESS.to_dict("records")
    # expected (scale*rhythm) power profile = benign scheduled power at each tick
    EXP={T: sum(s["pkw"] for s in sess if s["t0"]<=T<s["t1"]) for T in range(W0,W1,STEP)}
    fan_idx=0; kcons=0
    rl=defense.get("rate_limit"); mode=attack["mode"]; rate=attack["rate"]

    async def send(site,payload):
        try: return await chargers[site].call(payload)
        except Exception: return None

    for T in range(W0,W1,STEP):
        calls=[]
        # start/stop sessions this tick
        for i,s in enumerate(sess):
            if i not in started and T<=s["t0"]<T+STEP:
                started.add(i); active.setdefault(s["site"],[]).append([s["t1"],s["pkw"]])
                calls.append(send(s["site"],call.Authorize(id_tag=f"R{rng.randint(1000,9999)}")))
                calls.append(send(s["site"],call.StartTransaction(connector_id=1,id_tag="R",meter_start=0,timestamp=now_iso())))
        # update power_now (0 if curtailed)
        for site in SITES:
            act=[a for a in active.get(site,[]) if a[0]>T]
            active[site]=act
            cur = site in curtail_start and (recovery is None or curtail_start[site]<=T<recovery or (recovery and T<recovery))
            cur = site in curtail_start and (recovery is None or T<recovery)
            power_now[site]=0.0 if cur else sum(a[1] for a in act)
        # periodic MeterValues (light, real messages)
        if (T-W0)%MV_EVERY==0:
            for site in SITES:
                if active.get(site):
                    calls.append(send(site,call.MeterValues(connector_id=1,meter_value=[{"timestamp":now_iso(),"sampled_value":[{"value":str(round(power_now[site],2)),"measurand":"Power.Active.Import"}]}])))
        # attacker
        if with_attack and T>=t0_attack and not attack_stopped[0]:
            budget = rl if rl is not None else rate
            n=0
            while fan_idx<len(FANOUT) and n<budget:
                site=FANOUT[fan_idx]; fan_idx+=1
                if site in cmap:
                    prof={"charging_profile_id":1,"stack_level":0,"charging_profile_purpose":"TxDefaultProfile","charging_profile_kind":"Absolute","charging_schedule":{"charging_rate_unit":"W","charging_schedule_period":[{"start_period":0,"limit":0.0}]}}
                    if mode=="remote_stop": calls.append(cmap[site].call(call.RemoteStopTransaction(transaction_id=1))); aborted.add(site)
                    else: calls.append(cmap[site].call(call.SetChargingProfile(connector_id=0,cs_charging_profiles=prof)))
                    curtail_start.setdefault(site,T); cmd_log.append(T); n+=1
        if calls: await asyncio.gather(*calls,return_exceptions=True)
        # observed & detector
        obs=sum(power_now.values()); obs_series.append((T,obs))
        ctrl=sum(sum(a[1] for a in active.get(st,[])) for st in curtail_start if (recovery is None or T<recovery))
        ctrl_mw_series.append((T,ctrl/1000.0))
        exp=EXP.get(T,0.0)
        rate_cnt=sum(1 for c in cmd_log if T-120<=c<=T)
        alarm=False
        if rate_cnt>=5: alarm=True                       # command-rate burst
        if exp>5 and obs<0.5*exp: kcons+=1               # scale*rhythm consistency
        else: kcons=0
        if kcons>=2: alarm=True
        if alarm and t_detect is None and T>=t0_attack:
            t_detect=T
            if defense.get("isolate"):
                recovery=T+60; attack_stopped[0]=True
    rec=recovery if recovery else W1
    dE=0.0; denied=0
    for s in sess:
        cs=curtail_start.get(s["site"])
        if cs is None: continue
        ov=max(0,min(s["t1"],W1,rec)-max(s["t0"],W0,cs))
        if ov>0: dE+=s["pkw"]*ov/3600.0; denied+=1
    peak_mw=max((m for _,m in ctrl_mw_series),default=0.0)
    for s in SITES:
        try: await chargers[s]._connection.close()
        except Exception: pass
    srv.close(); await srv.wait_closed()
    return dict(curtail_start=dict(curtail_start), t_detect=t_detect, recovery=recovery, W0=W0, T0=t0_attack, W1=W1, denied_sites=sorted(aborted),
                dE_kwh=round(dE,1),denied=denied,ctrl_sites=len(curtail_start),ctrl_mw=round(peak_mw,3),
                tau_d_min=round((t_detect-t0_attack)/60,1) if t_detect else None,
                recovery_min=round((rec-t0_attack)/60,1) if recovery else None, n_cmds=len(cmd_log),
                obs_series=obs_series, ctrl_mw_series=ctrl_mw_series)

if __name__=="__main__":
    async def main():
        for lab,atk,dfn in [
            ("D0 无防御/快速攻击",{"mode":"curtail","rate":30},{}),
            ("D3+D5 检测+隔离/快速",{"mode":"curtail","rate":30},{"isolate":True}),
            ("D2 限速(2/min)/快速",{"mode":"curtail","rate":30},{"rate_limit":2}),
            ("D2+D3 限速+隔离/快速",{"mode":"curtail","rate":30},{"rate_limit":2,"isolate":True}),
            ("benign (无攻击)",{"mode":"curtail","rate":30},{"isolate":True}),
        ]:
            wa = lab!="benign (无攻击)"
            m=await run_scenario(atk,dfn,seed=1,with_attack=wa)
            print(lab,"->",{k:v for k,v in m.items() if "series" not in k})
    asyncio.run(main())
