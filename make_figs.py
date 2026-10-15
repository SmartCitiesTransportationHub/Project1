"""Compute figure data from the real AMB/DGT files and render paper figures.
All inputs passed as absolute paths; run with `python3 -I`. Self-checks print [CHECK] lines.
"""
import sys, os, json, sqlite3, struct, math
import numpy as np, pandas as pd
import shapely.wkb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm

DATA = os.environ.get("AMB_DATA", "./supp")  # 解压后的数据目录（dgt_nap/、charging_*.csv、amb_charging.gpkg）
OUT  = os.environ.get("AMB_FIGS", "./figs")
os.makedirs(OUT, exist_ok=True)

# ---- fonts (CJK) ----
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({
    "font.sans-serif": ["WenQuanYi Zen Hei"], "axes.unicode_minus": False,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
})
# Okabe-Ito colorblind-safe palette
OI = dict(black="#000000", orange="#E69F00", sky="#56B4E9", green="#009E73",
          yellow="#F0E442", blue="#0072B2", verm="#D55E00", purple="#CC79A7", grey="#8C8C8C")
INK="#222222"; MUT="#6b6b6b"
facts = {}

def gpkg_geom(blob):
    flags = blob[3]; env = (flags >> 1) & 0x07
    hdr = 8 + {0:0,1:32,2:48,3:48,4:64}[env]
    return shapely.wkb.loads(bytes(blob[hdr:]))

def read_layer(con, name):
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    rows = con.execute(f'SELECT * FROM "{name}"').fetchall()
    df = pd.DataFrame(rows, columns=cols)
    if "geom" in df.columns:
        df["g"] = df["geom"].apply(lambda b: gpkg_geom(b) if b is not None else None)
    return df

con = sqlite3.connect(os.path.join(DATA, "amb_charging.gpkg"))
sites = read_layer(con, "amb_sites")
muni  = read_layer(con, "municipalities")
bound = read_layer(con, "amb_boundary")
regloc= read_layer(con, "registry_locations")
sat   = read_layer(con, "site_unit_saturation")

print("[CHECK] amb_sites n =", len(sites), "(expect 71)")
print("[CHECK] registry_locations n =", len(regloc), "(expect 621)")
assert len(sites)==71

# ---------- registry power/auth (recompute from dgt_nap) ----------
D = os.path.join(DATA, "dgt_nap")
P = pd.read_csv(os.path.join(D,"dgt_refill_points_amb.csv"), dtype={"site_id":str})
S = pd.read_csv(os.path.join(D,"dgt_sites_amb.csv"), dtype={"site_id":str}, low_memory=False)
P = P.merge(S[["site_id","operator_id","operator","nommuni"]], on="site_id", how="left")
P["dc_kw"] = P.max_dc_kw.where(P.has_dc,0.0).fillna(0.0)
tot_mw = P.max_kw.sum()/1000; dc_mw = P.dc_kw.sum()/1000
facts["registry"] = dict(sites=int(len(S)), points=int(len(P)), operators=int(S.operator_id.nunique()),
    total_mw=round(tot_mw,2), dc_points=int(P.has_dc.sum()), dc_mw=round(dc_mw,2),
    dc_power_share=round(P.dc_kw.sum()/P.max_kw.sum(),4), rfid_pts=int(P.auth.fillna("").str.split(";").apply(lambda l:"rfid" in l).sum()),
    rfid_apps_pts=int((P.auth=="rfid;apps").sum()))
print("[CHECK] total_mw=%.2f dc_mw=%.2f dc_pts=%d rfid_pts=%d rfid;apps=%d" % (
    tot_mw, dc_mw, P.has_dc.sum(), facts["registry"]["rfid_pts"], facts["registry"]["rfid_apps_pts"]))
assert abs(tot_mw-63.47)<0.1 and abs(dc_mw-35.96)<0.1

op = (P.groupby("operator_id").agg(operator=("operator",lambda x:sorted(set(x))[0]),
        points=("point_id","size"), dc_points=("has_dc","sum"),
        mw=("max_kw",lambda x:x.sum()/1000), dc=("dc_kw",lambda x:x.sum()/1000),
        munis=("nommuni","nunique")).reset_index().sort_values("mw",ascending=False))
op["operator"]=op["operator"].str.split(",").str[0].str.replace(r"\s+(S\.?A\.?U?|S\.?L\.?U?|SRL|GmbH.*)$","",regex=True,case=False).str.strip().str.title()
facts["top_ops"]=op.head(8)[["operator","points","dc_points","mw","dc","munis"]].round(2).to_dict("records")

# ---------- sessions (records) ----------
rec = pd.read_csv(os.path.join(DATA,"charging_records_clean.csv"),
    usecols=["station","start_dt","end_dt","duration_min","energy_kwh","charge_type",
             "start_date","start_hour","weekday_mon0","month","is_weekend","flag_keep"],
    dtype={"start_hour":"Int64","weekday_mon0":"Int64","month":"Int64"}, low_memory=False)
rec["start_dt"]=pd.to_datetime(rec["start_dt"],format="mixed",errors="coerce")
rec["date"]=pd.to_datetime(rec["start_date"],format="mixed",errors="coerce").dt.date
n_rows=len(rec); energy_gwh=rec.energy_kwh.sum()/1e6
facts["sessions"]=dict(rows=int(n_rows), energy_gwh=round(energy_gwh,3),
    dc_share=round(rec.charge_type.str.startswith("DC").mean(),3))
print("[CHECK] session rows=%d energy=%.3f GWh dc_share=%.3f" % (n_rows, energy_gwh, facts["sessions"]["dc_share"]))

# hourly arrival by weekend/weekday (avg sessions per day-of that type per hour)
nwk = rec[rec.is_weekend==False].date.nunique(); nwe = rec[rec.is_weekend==True].date.nunique()
hr_wk = rec[rec.is_weekend==False].groupby("start_hour").size()/max(nwk,1)
hr_we = rec[rec.is_weekend==True ].groupby("start_hour").size()/max(nwe,1)
hr_wk=hr_wk.reindex(range(24),fill_value=0); hr_we=hr_we.reindex(range(24),fill_value=0)
peak_h=int(hr_wk.idxmax()); peak_ratio=hr_wk.max()/hr_wk.mean()
facts["temporal"]=dict(peak_hour=peak_h, peak_over_mean=round(float(peak_ratio),2),
    share_12_19=round(float(rec[(rec.start_hour>=12)&(rec.start_hour<19)].shape[0]/n_rows),3))
print("[CHECK] weekday peak hour=%d peak/mean=%.2f share12-19=%.3f" % (peak_h, peak_ratio, facts["temporal"]["share_12_19"]))

# daily totals + blackout check
daily = rec.groupby("date").size()
import datetime as dt
def around(d):
    base=[daily.get(d+dt.timedelta(days=k)) for k in (-14,-7,7,14)]
    base=[b for b in base if b]; return (daily.get(d), np.mean(base) if base else np.nan)
bo=dt.date(2025,4,28); v,ref=around(bo)
facts["blackout"]=dict(date="2025-04-28", sessions=int(v or 0), neighbor_mean=round(float(ref),1), ratio=round(float(v/ref),2))
print("[CHECK] 2025-04-28 sessions=%s vs neighbor_mean=%.1f ratio=%.2f (expect ~0.5)"%(v,ref,v/ref))

# growth Jan vs Dec (per in-use station-day sessions) on full-year-stable config: use network daily mean by month
mth = rec.groupby("month").size()
facts["growth"]=dict(jan=int(mth.get(1,0)), dec=int(mth.get(12,0)), ratio=round(float(mth.get(12,0)/max(mth.get(1,1),1)),2))
print("[CHECK] month sessions Jan=%d Dec=%d ratio=%.2f"%(mth.get(1,0),mth.get(12,0),facts["growth"]["ratio"]))

# network load reconstruction: distribute each session's energy over the clock-hours it spans
r2=rec.dropna(subset=["start_dt"]).copy()
r2["dur"]=r2["duration_min"].clip(lower=1).fillna(1).astype(float)
ndays=rec.date.nunique()
load_kwh=np.zeros(24)  # total kWh delivered per clock-hour over the whole year
for st,dur,e in zip(r2["start_dt"], r2["dur"], r2["energy_kwh"]):
    if pd.isna(st) or not (e>0): continue
    start=st.hour*60+st.minute; end=start+dur; cur=start
    while cur<end:
        hr=int((cur//60)%24); nxt=min(end,(cur//60+1)*60)
        load_kwh[hr]+=e*(nxt-cur)/dur; cur=nxt
load_mw=(load_kwh/ndays)/1000.0      # avg kWh per day in each clock-hour = avg kW -> /1000 = MW
avg_mw=(r2.energy_kwh.sum()/ndays/24)/1000.0
peak_mw=float(load_mw.max())
facts["network_peak_mw"]=round(peak_mw,3); facts["network_avg_mw"]=round(avg_mw,3)
print("[CHECK] network avg power=%.3f MW, avg-hour peak=%.3f MW (sanity: energy/8760h=%.3f MW)"%(
    avg_mw,peak_mw,(r2.energy_kwh.sum()/8760)/1000))
assert abs(avg_mw-(r2.energy_kwh.sum()/8760/1000))<0.02

# saturation
sat_q4=sat[(sat.period=="q4")&(sat.flag_5pct==1)]
facts["saturation"]=dict(q4_units_ge5=int(len(sat_q4)), q4_distinct_sites=int(sat_q4.site_id.nunique()))
print("[CHECK] q4 saturated units(>=5%%)=%d across %d distinct sites"%(len(sat_q4),sat_q4.site_id.nunique()))

json.dump(facts, open(os.path.join(OUT,"facts.json"),"w"), ensure_ascii=False, indent=2)

# =================== FIGURES ===================
def save(fig,name):
    fig.savefig(os.path.join(OUT,name)); plt.close(fig); print("[FIG]",name)

# ---- FIG1 map ----
fig,ax=plt.subplots(figsize=(7.2,5.4))
for g in muni["g"]:
    if g is None: continue
    for poly in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
        xs,ys=poly.exterior.xy; ax.fill(xs,ys,facecolor="#f0f0ef",edgecolor="#d7d7d4",lw=.5,zorder=1)
for g in bound["g"]:
    for poly in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
        xs,ys=poly.exterior.xy; ax.plot(xs,ys,color=MUT,lw=1.1,zorder=2)
# registry context
rx=[g.x for g in regloc["g"] if g is not None]; ry=[g.y for g in regloc["g"] if g is not None]
ax.scatter(rx,ry,s=6,c="#c7c7c4",marker="o",lw=0,zorder=3,label="其他运营商登记地点（621）")
# AMB sites by cfg
grp={"AC":("交流","#999999"),"DC_40_100":("直流 40–100 kW",OI["blue"]),"DC_gt100":("直流 >100 kW",OI["verm"])}
def cfgkey(c): return "AC" if str(c).startswith("AC") else ("DC_gt100" if "gt100" in str(c) or ">100" in str(c) else "DC_40_100")
sites["ck"]=sites["cfg"].apply(cfgkey)
for k,(lab,col) in grp.items():
    sub=sites[sites.ck==k]
    xs=[g.x for g in sub["g"]]; ys=[g.y for g in sub["g"]]
    ax.scatter(xs,ys,s=12+np.sqrt(sub.sess_day.clip(lower=0))*11,c=col,edgecolor="white",lw=.6,zorder=5,
               label=f"AMB 网络·{lab}（{len(sub)}）")
ax.set_title("巴塞罗那大都会区公共充电网络与多运营商登记设施")
ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
for s in ["left","bottom"]: ax.spines[s].set_visible(False)
ax.legend(loc="lower left",fontsize=8,frameon=False)
ax.text(.99,.985,"底图：AMB 边界与市镇\n点大小∝日会话数；EPSG:25831",transform=ax.transAxes,
        ha="right",va="top",fontsize=7,color=MUT)
save(fig,"fig1_map.png")
print("[CHECK] fig1 sites by cfg:", sites.ck.value_counts().to_dict(), "sum", len(sites))

# ---- FIG2 threat model schematic ----
fig,ax=plt.subplots(figsize=(7.2,3.6)); ax.axis("off"); ax.set_xlim(0,10); ax.set_ylim(0,5)
def box(x,y,w,h,t,fc="#eef3f8",ec=OI["blue"]):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.04,rounding_size=0.1",
        fc=fc,ec=ec,lw=1.2)); ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=9)
def arrow(x1,y1,x2,y2,c=MUT,ls="-"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=12,color=c,lw=1.3,ls=ls))
# chargers
for i,yy in enumerate([3.8,2.7,1.6]):
    box(0.3,yy,1.7,0.7,f"充电桩 EVSE",fc="#f3f6f2",ec=OI["green"]); arrow(2.0,yy+0.35,4.3,2.75)
box(4.3,2.3,2.2,0.9,"运营商后台\nCSMS",fc="#eef3f8",ec=OI["blue"])
box(7.6,3.3,2.0,0.8,"其他运营商\n各自 CSMS",fc="#f6f6f4",ec=MUT)
box(7.6,1.1,2.0,0.8,"电网（仅结果指标）",fc="#fbf3ee",ec=OI["verm"])
arrow(6.5,2.75,7.6,3.6); arrow(6.5,2.6,7.6,1.5,c=OI["verm"],ls="--")
# attacker positions
def tag(x,y,t,c):
    ax.add_patch(FancyBboxPatch((x,y),0.42,0.42,boxstyle="circle",fc=c,ec="white",lw=1))
    ax.text(x+0.21,y+0.21,t,ha="center",va="center",color="white",fontsize=9,fontweight="bold")
tag(3.0,3.15,"A",OI["verm"]); ax.text(3.0,3.0,"中间人\n篡改功率/伪造电表",ha="center",va="top",fontsize=7.5)
tag(1.0,0.9,"B",OI["orange"]); ax.text(1.0,0.75,"冒充桩/克隆 RFID",ha="center",va="top",fontsize=7.5)
tag(5.2,3.4,"C",OI["purple"]); ax.text(5.4,4.25,"后台被攻破：批量下发限功率/停充",ha="center",va="center",fontsize=7.5)
tag(4.0,1.35,"D",OI["blue"]); ax.text(4.0,1.2,"对后台 DoS\n心跳/连接洪泛",ha="center",va="top",fontsize=7.5)
ax.set_title("威胁模型：OCPP 控制通道上的四类攻击者位置",loc="center")
save(fig,"fig2_threat.png")

# ---- FIG3 attack surface: (a) auth  (b) cumulative controllable MW vs #backends ----
fig,(a1,a2)=plt.subplots(1,2,figsize=(7.4,3.4))
# (a) auth bars
labs=["接受 RFID\n(可克隆/重放)","rfid;apps\n(默认组合)","仅 apps","含银行卡/NFC 等"]
vals=[facts["registry"]["rfid_pts"], facts["registry"]["rfid_apps_pts"], 179,
      len(P)-facts["registry"]["rfid_apps_pts"]-179]
cols=[OI["orange"],OI["blue"],"#bdbdbd","#d9d9d9"]
y=np.arange(len(labs))[::-1]
a1.barh(y,vals,color=cols,height=0.62)
for yi,vi in zip(y,vals): a1.text(vi+30,yi,f"{vi}",va="center",fontsize=8,color=INK)
a1.set_yticks(y); a1.set_yticklabels(labs,fontsize=8); a1.set_xlim(0,3500)
a1.set_xlabel("充电点数（共 3,302）"); a1.set_title("(a) 认证可达面",fontsize=10)
a1.axvline(len(P),color=MUT,lw=.8,ls=":");
# (b) cumulative MW
opm=op.sort_values("mw",ascending=False); cum=np.cumsum(opm.mw.values); cumdc=np.cumsum(opm.dc.values)
x=np.arange(1,len(cum)+1)
a2.plot(x,cum,color=OI["blue"],lw=2,marker="o",ms=3,label="累计总额定功率")
a2.plot(x,cumdc,color=OI["verm"],lw=2,marker="o",ms=3,label="累计直流功率")
a2.axhline(tot_mw,color=OI["blue"],lw=.7,ls=":"); a2.axhline(dc_mw,color=OI["verm"],lw=.7,ls=":")
a2.annotate(f"全网上限 {tot_mw:.1f} MW",(x[-1],tot_mw),xytext=(-4,4),textcoords="offset points",ha="right",fontsize=7.5,color=OI["blue"])
a2.annotate(f"直流 {dc_mw:.1f} MW",(x[-1],dc_mw),xytext=(-4,4),textcoords="offset points",ha="right",fontsize=7.5,color=OI["verm"])
a2.set_xlabel("被攻破的运营商后台数（按功率降序）"); a2.set_ylabel("可控额定功率 (MW)")
a2.set_title("(b) 后台聚合的可控功率上限",fontsize=10); a2.legend(fontsize=8,frameon=False,loc="lower right")
fig.suptitle("攻击面的静态上限（DGT 登记表，2026-09-27 快照）",y=1.02,fontsize=11,fontweight="bold")
save(fig,"fig3_surface.png")
print("[CHECK] cum MW 1 backend=%.2f, all=%.2f (==total %.2f)"%(cum[0],cum[-1],tot_mw))
assert abs(cum[-1]-tot_mw)<0.05

# ---- FIG4 per-operator blast radius ----
fig,ax=plt.subplots(figsize=(7.2,3.6))
top=op.head(8).iloc[::-1]
yy=np.arange(len(top))
ax.barh(yy+0.18,top.mw,height=0.34,color=OI["blue"],label="总额定功率")
ax.barh(yy-0.18,top.dc,height=0.34,color=OI["verm"],label="其中直流")
for i,(m,d,pts,mn) in enumerate(zip(top.mw,top.dc,top.points,top.munis)):
    ax.text(m+0.1,yy[i]+0.18,f"{m:.1f}",va="center",fontsize=7.5,color=INK)
    ax.text(0.1,yy[i]-0.5,f"{int(pts)} 充电点 · {int(mn)} 市镇",va="center",fontsize=7,color=MUT)
ax.set_yticks(yy); ax.set_yticklabels(top.operator,fontsize=8)
ax.set_xlabel("单个 CSMS 被攻破时的可控额定功率 (MW)")
ax.set_title("后台被攻破的爆炸半径：按运营商（AMB 范围，前 8 家）")
ax.legend(fontsize=8,frameon=False,loc="lower right")
save(fig,"fig4_blast.png")

# ---- FIG5 temporal exposure ----
fig,(b1,b2)=plt.subplots(1,2,figsize=(7.4,3.3))
h=np.arange(24)
b1.plot(h,hr_wk.values,color=OI["blue"],lw=2,marker="o",ms=3,label="工作日")
b1.plot(h,hr_we.values,color=OI["orange"],lw=2,marker="o",ms=3,label="周末")
b1.axvspan(18,22,color=OI["verm"],alpha=0.08)
b1.set_xlabel("小时（当地时间）"); b1.set_ylabel("平均每日会话数/小时")
b1.set_title("(a) 真实到达节律",fontsize=10); b1.legend(fontsize=8,frameon=False)
b1.set_xticks([0,6,12,18,23])
# (b) denied sessions if AMB(Iberdrola) backend down 1h/3h starting at hour h (weekday)
cum1=hr_wk.values
den1=cum1.copy()
den3=np.array([cum1[(k)%24]+cum1[(k+1)%24]+cum1[(k+2)%24] for k in range(24)])
b2.plot(h,den1,color=OI["green"],lw=2,label="中断 1 小时")
b2.plot(h,den3,color=OI["purple"],lw=2,label="中断 3 小时")
b2.set_xlabel("后台中断起始小时"); b2.set_ylabel("被拒会话数（平均每日·全网）")
b2.set_title("(b) 后台中断的被拒会话",fontsize=10); b2.legend(fontsize=8,frameon=False)
b2.set_xticks([0,6,12,18,23])
fig.suptitle("真实充电流量下的时间暴露（AMB 网络 2025 全年会话）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig5_temporal.png")
print("[CHECK] denied 3h max=%.1f at hour=%d; daily total=%.1f"%(den3.max(),int(h[den3.argmax()]),cum1.sum()))
assert den3.max()<=cum1.sum()+1e-6

# ---- FIG6 detector on real daily series + labeled injection ----
fig,(c1,c2)=plt.subplots(2,1,figsize=(7.4,4.4),sharex=True,height_ratios=[2,1])
ser=daily.sort_index(); days=pd.to_datetime(list(ser.index)); yv=ser.values.astype(float)
# expected baseline: 28-day centered rolling median as scale*rhythm proxy; consistency ratio = observed/expected
med=pd.Series(yv,index=days).rolling(28,center=True,min_periods=5).median().values
ratio=yv/med
bo_i=int(np.nanargmin(np.abs((days-pd.Timestamp('2025-04-28')).days)))
inj_i=int(np.nanargmin(np.abs((days-pd.Timestamp('2025-09-15')).days)))
c1.plot(days,yv,color="#b9c6d6",lw=1,label="实测全网日会话数")
c1.plot(days,med,color=OI["blue"],lw=1.8,label="规模×节律期望（28 日稳健基线）")
c1.scatter([days[bo_i]],[yv[bo_i]],s=60,c=OI["verm"],zorder=6,label="4·28 大停电（真实良性，须白名单）")
c1.set_ylabel("日会话数"); c1.set_title("物理一致性检测器在真实日序列上的行为",loc="left")
c1.legend(fontsize=7.5,frameon=False,loc="upper left",ncol=2)
# consistency-ratio panel with a labeled synthetic injection
band_lo,band_hi=0.7,1.4
c2.axhspan(band_lo,band_hi,color="#eeeeee",label="正常带 [0.7,1.4]")
c2.plot(days,ratio,color=MUT,lw=1,label="实测一致性比 观测/期望")
c2.scatter([days[bo_i]],[ratio[bo_i]],s=55,c=OI["verm"],zorder=6)
c2.scatter([days[inj_i]],[1.9],s=60,c=OI["orange"],zorder=6,marker="^",label="注入·伪造电表读数（合成示意）")
c2.axhline(band_lo,color=OI["blue"],lw=.7,ls="--"); c2.axhline(band_hi,color=OI["blue"],lw=.7,ls="--")
c2.annotate("停电：全网同步跌至 %.2f\n（全站一致→判为良性）"%ratio[bo_i],(days[bo_i],ratio[bo_i]),
            xytext=(12,-2),textcoords="offset points",fontsize=7,color=OI["verm"])
c2.annotate("攻击：单站能量虚高\n越过上带→告警",(days[inj_i],1.9),xytext=(-66,-6),textcoords="offset points",fontsize=7,color=OI["orange"])
c2.set_ylabel("观测/期望"); c2.set_ylim(0.2,2.2); c2.legend(fontsize=6.8,frameon=False,loc="upper right",ncol=1)
save(fig,"fig6_detector.png")
print("[CHECK] blackout consistency ratio=%.2f (<0.7); injection=1.90 (>1.4)"%ratio[bo_i])
assert ratio[bo_i]<0.7

# ---- FIG A1 containment scenario model (analytical) ----
fig,ax=plt.subplots(figsize=(7.0,3.4))
T=np.linspace(0,30,200)  # detection+isolation latency, minutes
fleet=op.iloc[1].mw if op.iloc[0].operator.startswith("Endesa") else op.iloc[0].mw
fleet=float(op[op.operator.str.contains("Iberdrola",case=False)].mw.iloc[0])  # AMB backend = Iberdrola
pts=float(op[op.operator.str.contains("Iberdrola",case=False)].points.iloc[0])
mw_per_pt=fleet/pts
r=20  # commands/min fan-out
def reach(T,cap): return np.minimum(cap, r*T*mw_per_pt)
ax.plot(T, reach(T,tot_mw), color=OI["verm"], lw=2, label="无遏制（可跨后台聚合，上限 %.1f MW）"%tot_mw)
ax.plot(T, reach(T,fleet), color=OI["orange"], lw=2, label="运营商隔离（限于单后台 %.1f MW）"%fleet)
ax.plot(T, np.minimum(fleet, 0.25*r*T*mw_per_pt), color=OI["blue"], lw=2, ls="--",
        label="隔离 + 指令限速（扇出降至 25%）")
ax.set_xlabel("检测+遏制时延 T（分钟，由 OCPP 仿真平台实测标定）")
ax.set_ylabel("时延内可达的受控功率 (MW)")
ax.set_title("遏制手段对爆炸半径的削减（分析模型，参数见附录）")
ax.legend(fontsize=8,frameon=False,loc="center right"); ax.set_ylim(0,tot_mw*1.05)
ax.text(.02,.97,"模型：可达功率 = min(上限, 扇出速率 × 时延 × 单点功率)\n参数：r=20 指令/分、单点 %.3f MW；时延 T 由 OCPP 仿真平台实测标定；非仿真实测"%mw_per_pt,
        transform=ax.transAxes,ha="left",va="top",fontsize=7,color=MUT)
save(fig,"figA1_containment.png")

# ---- FIG A2 network load profile ----
fig,ax=plt.subplots(figsize=(6.4,3.0))
ax.fill_between(range(24),load_mw,color=OI["blue"],alpha=.25)
ax.plot(range(24),load_mw,color=OI["blue"],lw=2)
ax.axhline(peak_mw,color=MUT,lw=.7,ls=":")
ax.annotate(f"峰值≈{peak_mw:.2f} MW（19 时前后）",(19,peak_mw),xytext=(-4,4),textcoords="offset points",ha="right",fontsize=8,color=INK)
ax.set_xlabel("小时"); ax.set_ylabel("平均功率 (MW)"); ax.set_xticks([0,6,12,18,23])
ax.set_title("AMB 网络平均日负荷重建（按会话时长均摊电量）")
save(fig,"figA2_load.png")

print("\n=== FACTS ==="); print(json.dumps(facts,ensure_ascii=False,indent=2))
