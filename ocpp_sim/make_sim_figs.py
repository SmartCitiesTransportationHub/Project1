"""Measured figures from the real OCPP emulation (results.json), overwriting the
analytical-model figures fig16_matrix / fig17_latency / figA1_containment."""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"font.size":10,
    "axes.titlesize":11,"axes.titleweight":"bold","figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight",
    "axes.spines.top":False,"axes.spines.right":False})
OI=dict(orange="#E69F00",sky="#56B4E9",green="#009E73",blue="#0072B2",verm="#D55E00",purple="#CC79A7",grey="#8C8C8C")
INK="#222"; MUT="#6b6b6b"
OUT=os.environ.get("AMB_FIGS","./figs")
R=json.load(open(os.path.join(os.path.dirname(__file__),"results.json")))
cells=R["cells"]; fpr=R["fpr"]
ATK=["快速篡改(30/min)","隐蔽慢速(3/min)","批量远程停充(30/min)"]
DEF=["D0 无防御","D5 仅检测","D3+D5 检测+隔离","D2 限速","D2+D3+D5 限速+隔离"]
def cell(a,d,key):
    for c in cells:
        if c["attack"]==a and c["defense"]==d: return c[key]
    return None
def save(fig,n): fig.savefig(os.path.join(OUT,n)); plt.close(fig); print("[FIG]",n)

# ---- fig16_matrix: measured residual loss heatmap (attack x defense) ----
M=np.array([[cell(a,d,"dE_med") for d in DEF] for a in ATK])
fig,ax=plt.subplots(figsize=(8.2,3.3))
im=ax.imshow(M,cmap="OrRd",aspect="auto",norm=matplotlib.colors.LogNorm(vmin=5,vmax=M.max()))
ax.set_xticks(range(len(DEF))); ax.set_xticklabels(DEF,fontsize=8,rotation=10)
ax.set_yticks(range(len(ATK))); ax.set_yticklabels(ATK,fontsize=8)
for i in range(len(ATK)):
    for j in range(len(DEF)):
        v=M[i,j]; ax.text(j,i,f"{v:.0f}",ha="center",va="center",fontsize=8.5,
                          color="white" if v>80 else INK)
ax.set_title("场景矩阵实测：被发现前残余受控电量 ΔE (kWh)")
cb=fig.colorbar(im,ax=ax,fraction=.04,pad=.02); cb.set_label("ΔE (kWh, 对数)",fontsize=8)
ax.text(1.0,-0.42,f"OCPP 1.6 仿真实测（代表日 2025-12-05，16–22时，57 站真实会话）；误报 {fpr['false_alarms']}/{fpr['runs']}",
        transform=ax.transAxes,ha="right",va="top",fontsize=7,color=MUT)
save(fig,"fig17_matrix.png")

# ---- fig17_latency: measured dE (log) and detection latency by defense ----
fig,(a1,a2)=plt.subplots(1,2,figsize=(10.8,3.7))
cols=[OI["verm"],OI["orange"],OI["blue"]]
x=np.arange(len(DEF)); w=0.26
for k,a in enumerate(ATK):
    dE=[cell(a,d,"dE_med") for d in DEF]
    a1.bar(x+(k-1)*w,dE,w,color=cols[k],label=a.split("(")[0])
a1.set_yscale("log"); a1.set_xticks(x); a1.set_xticklabels(DEF,fontsize=7.5,rotation=12)
a1.set_ylabel("ΔE (kWh, 对数)"); a1.set_title("(a) 残余受控电量",fontsize=10); a1.legend(fontsize=7.5,frameon=False)
a1.axhline(2115,color=MUT,lw=.6,ls=":"); a1.text(0,2300,"无防御基线 ~2100 kWh",fontsize=7,color=MUT)
for k,a in enumerate(ATK):
    tau=[cell(a,d,"tau_med") for d in DEF]; tau=[t if t is not None else np.nan for t in tau]
    a2.plot(x,tau,marker="o",ms=5,color=cols[k],lw=1.6,label=a.split("(")[0])
a2.set_xticks(x); a2.set_xticklabels(DEF,fontsize=7.5,rotation=12); a2.set_ylabel("检测时延 τ_d (min)")
a2.set_title("(b) 检测时延",fontsize=10); a2.legend(fontsize=7.5,frameon=False); a2.set_ylim(-0.3,3)
fig.suptitle("OCPP 仿真实测：防御配置对残余损失与检测时延的影响",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig18_latency.png")

# ---- figA1_containment: measured controlled-MW over sim-time (fast attack) ----
ser=R["series"]; fig,ax=plt.subplots(figsize=(7.4,3.6))
colmap={"D0 无防御":OI["verm"],"D5 仅检测":OI["orange"],"D3+D5 检测+隔离":OI["blue"],
        "D2 限速":OI["purple"],"D2+D3+D5 限速+隔离":OI["green"]}
T0=18*3600
for d in DEF:
    if d not in ser: continue
    s=ser[d]["ctrl"]; t=[(x[0]-T0)/60 for x in s]; y=[x[1] for x in s]
    # keep from a few min before attack
    tt=[a for a in t if a>=-5]; yy=[y[i] for i,a in enumerate(t) if a>=-5]
    ax.plot(tt,yy,color=colmap[d],lw=2,label=d)
ax.axvline(0,color=MUT,lw=.7,ls=":"); ax.text(0.2,ax.get_ylim()[1]*0.95,"攻击注入",fontsize=7.5,color=MUT,va="top")
ax.set_xlabel("自攻击注入起的时间 (min)"); ax.set_ylabel("受控功率 (MW)")
ax.set_title("OCPP 仿真实测：受控功率随时间（快速篡改攻击）")
ax.legend(fontsize=7.5,frameon=False,loc="center right"); ax.set_xlim(-5,60)
save(fig,"figA1_containment.png")
print("[DONE] measured figs; D0 peak MW=%.3f"%max(x[1] for x in ser["D0 无防御"]["ctrl"]))
