"""Analytical fused figures fig13-20 for the OCPP paper, from real AMB data + clearly-labeled models.
Run: python3 -I make_figs3.py
"""
import os, sqlite3
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import Normalize

DATA = os.environ.get("AMB_DATA", "./supp")  # 解压后的数据目录（dgt_nap/、charging_*.csv、amb_charging.gpkg）
OUT  = os.environ.get("AMB_FIGS", "./figs")
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,
    "font.size":10,"axes.titlesize":11,"axes.titleweight":"bold","figure.dpi":150,"savefig.dpi":150,
    "savefig.bbox":"tight","axes.spines.top":False,"axes.spines.right":False})
OI=dict(black="#000000",orange="#E69F00",sky="#56B4E9",green="#009E73",yellow="#F0E442",
        blue="#0072B2",verm="#D55E00",purple="#CC79A7",grey="#8C8C8C")
INK="#222"; MUT="#6b6b6b"
def save(fig,n): fig.savefig(os.path.join(OUT,n)); plt.close(fig); print("[FIG]",n)

# registry power table
D=os.path.join(DATA,"dgt_nap")
P=pd.read_csv(os.path.join(D,"dgt_refill_points_amb.csv"),dtype={"site_id":str})
S=pd.read_csv(os.path.join(D,"dgt_sites_amb.csv"),dtype={"site_id":str},low_memory=False)
P=P.merge(S[["site_id","operator_id","operator"]],on="site_id",how="left")
P["dc_kw"]=P.max_dc_kw.where(P.has_dc,0).fillna(0)
tot_mw=P.max_kw.sum()/1000; dc_mw=P.dc_kw.sum()/1000; npts=len(P)
rfid_pts=int(P.auth.fillna("").str.split(";").apply(lambda l:"rfid" in l).sum())
op=P.groupby("operator_id").agg(mw=("max_kw",lambda x:x.sum()/1000),pts=("point_id","size")).reset_index().sort_values("mw",ascending=False)
op_top_mw=float(op.mw.iloc[0]); op_top_pts=int(op.pts.iloc[0])
print("[CHECK] tot_mw=%.2f dc_mw=%.2f rfid_pts=%d top_op_mw=%.2f/%dpts"%(tot_mw,dc_mw,rfid_pts,op_top_mw,op_top_pts))

# records
rec=pd.read_csv(os.path.join(DATA,"charging_records_clean.csv"),
    usecols=["charge_type","duration_min","energy_kwh","peak_kw_clean","start_hour","weekday_mon0","month","is_weekend"],
    low_memory=False)
smc=pd.read_sql("select * from site_month_connector", sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg")))

# ===== fig13 reachability model heatmap (points & MW) =====
pos=["A1 中间人","A2 克隆RFID","A3 后台攻陷\n(最大运营商)","A4 后台DoS\n(最大运营商)"]
post=["1.6 明文","1.6+TLS","2.0.1 档2/3","2.1 P&C"]
# reachable POINTS under (position, posture): upper-bound model
Rp=np.array([
 [npts, 0, 0, 0],                       # A1 MitM: only on unencrypted links
 [rfid_pts, rfid_pts, rfid_pts, int(rfid_pts*0.1)],  # A2 RFID: reuse idTag; 2.1 P&C cert cuts it
 [op_top_pts]*4,                         # A3 backend compromise: link security irrelevant
 [op_top_pts]*4,                         # A4 DoS: connection flood regardless
],float)
Rmw=np.array([
 [tot_mw,0,0,0],
 [tot_mw*rfid_pts/npts, tot_mw*rfid_pts/npts, tot_mw*rfid_pts/npts, tot_mw*rfid_pts/npts*0.1],
 [op_top_mw]*4,
 [op_top_mw]*4,
],float)
fig,(a1,a2)=plt.subplots(1,2,figsize=(10.5,3.9))
for ax,M,ttl,fmt in [(a1,Rp,"(a) 可达充电点数","%d"),(a2,Rmw,"(b) 可达额定功率 (MW)","%.1f")]:
    im=ax.imshow(M,cmap="OrRd",aspect="auto")
    ax.set_xticks(range(4)); ax.set_xticklabels(post,fontsize=8)
    ax.set_yticks(range(4)); ax.set_yticklabels(pos,fontsize=8)
    for i in range(4):
        for j in range(4):
            ax.text(j,i,fmt%M[i,j],ha="center",va="center",fontsize=8,
                    color="white" if M[i,j]>M.max()*.55 else INK)
    ax.set_title(ttl,fontsize=10)
fig.suptitle("可达性上界模型：攻击者位置 × OCPP 安全配置（非实测，上界）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig13_reach.png")
print("[CHECK] A1明文可控MW=%.1f(应=总%.1f); A3=%.1f"%(Rmw[0,0],tot_mw,Rmw[2,0]))

# ===== fig14 arrival heatmaps hour x weekday, hour x month =====
fig,(b1,b2)=plt.subplots(1,2,figsize=(11,3.9))
wd=rec.pivot_table(index="weekday_mon0",columns="start_hour",values="energy_kwh",aggfunc="size",fill_value=0)
wd=wd.reindex(index=range(7),columns=range(24),fill_value=0)
ndw=rec.groupby("weekday_mon0").apply(lambda d:d.assign().shape[0]);
# normalize to avg sessions per that-weekday occurrence (~52 each)
wd_days=rec.drop_duplicates(["weekday_mon0","month","start_hour"])  # not exact; use count/~52
im1=b1.imshow(wd.values/52.0,cmap="YlOrRd",aspect="auto")
b1.set_yticks(range(7)); b1.set_yticklabels(["周一","周二","周三","周四","周五","周六","周日"],fontsize=8)
b1.set_xticks([0,6,12,18,23]); b1.set_xlabel("小时"); b1.set_title("(a) 到达热图：星期 × 小时",fontsize=10)
fig.colorbar(im1,ax=b1,fraction=.046,pad=.02).set_label("会话/小时(约)",fontsize=7)
mh=rec.pivot_table(index="month",columns="start_hour",values="energy_kwh",aggfunc="size",fill_value=0).reindex(index=range(1,13),columns=range(24),fill_value=0)
im2=b2.imshow(mh.values/30.0,cmap="YlOrRd",aspect="auto")
b2.set_yticks(range(12)); b2.set_yticklabels([f"{m}月" for m in range(1,13)],fontsize=7)
b2.set_xticks([0,6,12,18,23]); b2.set_xlabel("小时"); b2.set_title("(b) 到达热图：月份 × 小时",fontsize=10)
fig.colorbar(im2,ax=b2,fraction=.046,pad=.02).set_label("会话/小时(约)",fontsize=7)
fig.suptitle("真实充电到达的时间结构（支撑 DoS 时窗与检测基线）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig14_arrival.png")

# ===== fig15 charge-type attack value =====
order=["AC_SCHUKO_LT7","AC_TYPE2_7_40","DC_CHA_CCS_40_100","DC_CCS_GT100"]
labs=["交流Schuko\n<7kW","交流Type2\n7–40kW","直流\n40–100kW","直流\n>100kW"]
g=rec.groupby("charge_type").agg(dur=("duration_min","median"),kwh=("energy_kwh","median"),
    kw=("peak_kw_clean","median"),n=("energy_kwh","size")).reindex(order)
fig,axs=plt.subplots(1,3,figsize=(11,3.4))
cols=["#bdbdbd","#9e9e9e",OI["blue"],OI["verm"]]
for ax,col,ttl,unit in [(axs[0],"dur","(a) 中位时长 (min)","min"),(axs[1],"kwh","(b) 中位电量 (kWh)","kWh"),(axs[2],"kw","(c) 中位功率 (kW)","kW")]:
    ax.bar(range(4),g[col].values,color=cols)
    for i,v in enumerate(g[col].values): ax.text(i,v,f"{v:.0f}",ha="center",va="bottom",fontsize=8)
    ax.set_xticks(range(4)); ax.set_xticklabels(labs,fontsize=7.5); ax.set_title(ttl,fontsize=10)
fig.suptitle("按接口类型的攻击价值：直流桩短时、高功率、高电量（功率操纵的主要目标）",y=1.04,fontsize=11,fontweight="bold")
save(fig,"fig15_chargetype.png")
print("[CHECK] DC>100 median kW=%.1f vs Schuko %.1f"%(g.loc["DC_CCS_GT100","kw"],g.loc["AC_SCHUKO_LT7","kw"]))

# ===== fig16 monthly growth by interface =====
piv=smc.groupby(["month","group"]).sessions.sum().unstack().reindex(range(1,13))
fig,(c1,c2)=plt.subplots(1,2,figsize=(10.5,3.6))
cmap={"DC":OI["verm"],"AC_T2":OI["blue"],"SCHUKO":OI["grey"]}
nm={"DC":"直流","AC_T2":"交流 Type2","SCHUKO":"交流 Schuko"}
for col in ["DC","AC_T2","SCHUKO"]:
    c1.plot(piv.index,piv[col],color=cmap[col],lw=2,marker="o",ms=3,label=nm[col])
    c2.plot(piv.index,piv[col]/piv[col].iloc[0],color=cmap[col],lw=2,marker="o",ms=3,label=nm[col])
c1.set_xlabel("月份"); c1.set_ylabel("会话数"); c1.set_title("(a) 月度会话量",fontsize=10); c1.legend(fontsize=8,frameon=False)
c2.axhline(1,color=MUT,lw=.6,ls=":"); c2.set_xlabel("月份"); c2.set_ylabel("相对 1 月"); c2.set_title("(b) 归一化增长",fontsize=10); c2.legend(fontsize=8,frameon=False)
fig.suptitle("各接口的月度增长不同步（负荷构成随时间变化，规则须定期更新）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig16_monthly.png")
print("[CHECK] DC Dec/Jan=%.2f AC_T2=%.2f SCHUKO=%.2f"%(piv.DC.iloc[-1]/piv.DC.iloc[0],piv.AC_T2.iloc[-1]/piv.AC_T2.iloc[0],piv.SCHUKO.iloc[-1]/piv.SCHUKO.iloc[0]))

# ===== fig17 scenario-matrix qualitative loss heatmap (expected) =====
Ap=["A1 中间人","A2 克隆RFID","A3 后台攻陷","A4 后台DoS"]
Dc=["D0 无防御","D1 加密认证","D2 指令限速","D3 隔离","D4 联邦检测","D5 一致性检测"]
# qualitative residual loss 0(无)-3(高), expected (design), labeled
L=np.array([
 [3,0,2,1,1,1],  # A1 MitM: encryption kills it; limiter/isolation/detection partial
 [3,1,3,2,2,1],  # A2 RFID: cert auth(D1) helps; consistency detection(D5) catches kWh anomaly
 [3,3,1,1,2,2],  # A3 backend: encryption no help; limiter+isolation cut blast; detection mid
 [3,3,2,1,1,3],  # A4 DoS: isolation best; consistency detection weak (no energy signal)
],float)
fig,ax=plt.subplots(figsize=(7.6,3.4))
im=ax.imshow(L,cmap="RdYlGn_r",aspect="auto",vmin=0,vmax=3)
ax.set_xticks(range(6)); ax.set_xticklabels(Dc,fontsize=8,rotation=12)
ax.set_yticks(range(4)); ax.set_yticklabels(Ap,fontsize=8)
lv={0:"无",1:"低",2:"中",3:"高"}
for i in range(4):
    for j in range(6): ax.text(j,i,lv[int(L[i,j])],ha="center",va="center",fontsize=8,color=INK)
ax.set_title("场景矩阵：各防御配置下的残余损失（预期/定性，待仿真实测标定）")
save(fig,"fig17_matrix.png")

# ===== fig18 detection-latency vs residual loss (analytical) =====
fig,(d1,d2)=plt.subplots(1,2,figsize=(10.5,3.6))
T=np.linspace(0,30,200); r=20; m=op_top_mw/op_top_pts
reach=lambda cap,rate: np.minimum(cap, rate*T*m)
# residual energy-at-risk (MWh) = integral of reachable power over time ~ 0.5*reach*T/60 (triangular ramp)
def loss(cap,rate): rc=reach(cap,rate); return rc*(T/60.0)*0.5
d1.plot(T,loss(tot_mw,r),color=OI["verm"],lw=2,label="无遏制(上限 %.1f MW)"%tot_mw)
d1.plot(T,loss(op_top_mw,r),color=OI["orange"],lw=2,label="运营商隔离(%.1f MW)"%op_top_mw)
d1.plot(T,loss(op_top_mw,r*0.25),color=OI["blue"],lw=2,ls="--",label="隔离+限速(扇出25%)")
d1.set_xlabel("检测+遏制时延 T (分钟)"); d1.set_ylabel("时延内受控电量 (MWh)")
d1.set_title("(a) 被发现前损失随时延增长",fontsize=10); d1.legend(fontsize=7.5,frameon=False,loc="upper left")
# panel b: marginal loss reduction at T=15min by adding each defense (analytical, same model family)
Tref=15; base=float(np.interp(Tref,T,loss(tot_mw,r)))
vals=[base,
      float(np.interp(Tref,T,loss(op_top_mw,r))),
      float(np.interp(Tref,T,loss(op_top_mw,r*0.25))),
      float(np.interp(Tref,T,loss(op_top_mw,r*0.25)))*0.3]  # +早检测缩短T (示意)
names=["无遏制","+隔离","+限速","+早检测(缩短T)"]
d2.bar(range(4),vals,color=[OI["verm"],OI["orange"],OI["blue"],OI["green"]])
for i,v in enumerate(vals): d2.text(i,v,f"{v:.1f}",ha="center",va="bottom",fontsize=8)
d2.set_xticks(range(4)); d2.set_xticklabels(names,fontsize=8); d2.set_ylabel("T=15min 残余受控电量 (MWh)")
d2.set_title("(b) 叠加遏制手段的边际削减",fontsize=10)
fig.suptitle("遏制时延-残余损失权衡（分析模型；T 由 OCPP 仿真平台实测标定）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig18_latency.png")

# ===== fig19 MW concentration Lorenz =====
mw=np.sort(op.mw.values)[::-1]; cum=np.cumsum(mw)/mw.sum(); x=np.arange(1,len(mw)+1)/len(mw)
# Lorenz uses ascending
mws=np.sort(op.mw.values); lor=np.concatenate([[0],np.cumsum(mws)/mws.sum()]); xx=np.arange(len(mws)+1)/len(mws)
gini=1-2*np.trapezoid(lor,xx)
fig,(e1,e2)=plt.subplots(1,2,figsize=(10,3.6))
e1.plot(x,cum,color=OI["blue"],lw=2,marker="o",ms=3)
e1.axhline(0.8,color=MUT,lw=.7,ls=":");
n80=int(np.searchsorted(cum,0.8))+1
e1.annotate(f"前 {n80} 家后台 ≈ 80% 功率",(x[n80-1],0.8),xytext=(6,-14),textcoords="offset points",fontsize=8,color=INK)
e1.set_xlabel("被攻破后台比例(按功率降序)"); e1.set_ylabel("累计可控功率占比"); e1.set_title("(a) 可控功率集中度",fontsize=10)
e2.plot(xx,lor,color=OI["purple"],lw=2,label=f"洛伦兹曲线 (Gini={gini:.2f})"); e2.plot([0,1],[0,1],color=MUT,lw=.8,ls="--")
e2.set_xlabel("运营商比例"); e2.set_ylabel("功率占比"); e2.set_title("(b) 运营商功率不均",fontsize=10); e2.legend(fontsize=8,frameon=False,loc="upper left")
fig.suptitle("可控功率在运营商间高度集中（少数后台即聚合大部分功率）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig19_lorenz.png")
print("[CHECK] n80=%d gini=%.2f"%(n80,gini))

# ===== fig20 SISCOM grid-context =====
fig,ax=plt.subplots(figsize=(7.2,3.8))
p=np.linspace(0,0.14,300); nadir=50-10.0*p  # linearized SFR: nadir=49.0 at p=0.10 (UFLS)
ax.plot(p*100,nadir,color=OI["blue"],lw=2,label="频率最低点(SFR 模型,H=5s 线性化)")
ax.axhspan(49.9,50.1,color="#eaf2ea",label="正常频带 ±0.1 Hz")
ax.axhline(49.0,color=OI["verm"],lw=1.2,ls="--")
ax.axvspan(9,11,color=OI["verm"],alpha=.12)
ax.text(10,49.05,"UFLS 触发带 9–11%",fontsize=8,color=OI["verm"],ha="center")
amb_p=tot_mw/40000*100
ax.axvline(amb_p,color=OI["green"],lw=1.5)
ax.annotate(f"AMB 全部登记 63.47 MW\n= 本土峰值(~40GW)的 {amb_p:.2f}%",(amb_p,49.5),
            xytext=(30,0),textcoords="offset points",fontsize=8,color=OI["green"],
            arrowprops=dict(arrowstyle="->",color=OI["green"]))
ax.set_xlabel("受控直流负荷比例 p (%系统峰值)"); ax.set_ylabel("频率最低点 (Hz)")
ax.set_title("网络层可控量→电网结果指标：AMB 远低于减载阈值")
ax.legend(fontsize=8,frameon=False,loc="lower left"); ax.set_ylim(48.5,50.2); ax.set_xlim(0,14)
ax.text(.99,.02,"据[SISCOM]的 SFR 阈值(9–11%)线性化；AMB 位置为本文计算，示意",transform=ax.transAxes,ha="right",va="bottom",fontsize=7,color=MUT)
save(fig,"fig20_grid.png")
print("[CHECK] AMB p=%.3f%% (<<9-11%% UFLS band)"%amb_p)
print("[DONE] analytical figs")
