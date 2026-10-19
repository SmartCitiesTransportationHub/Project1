"""图 13: adversarial-robustness + fragmentation-counterfactual + real-data safety battery.
  (a) E2 fragmentation vs monolithic single-compromise blast radius
  (b) E3 stealth evasion map (residual dE over curtail-fraction f x fan-out rate)
  (c) E5 optimal-stopping controller INSIDE the engine vs the fixed rule on stealth attacks
  (d) E1 synchrony gate: suppresses blackout false-isolation while catching the localized attack
Reads results_ablation2.json (+ results_realchecks.json for the benign-gate annotation)."""
import os, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":170})
FIGS="/home/user/Project1/figs"; HERE=os.path.dirname(__file__)
NAVY="#0F3D57"; TEAL="#1AA3C4"; RED="#E8384F"; GREEN="#1EA97C"; ORANGE="#F08A24"; PURPLE="#8B4DDB"; INK="#1A2633"; MUT="#5D6B7A"

R=json.load(open(os.path.join(HERE,"results_ablation2.json")))
RC=json.load(open(os.path.join(HERE,"results_realchecks.json"))) if os.path.exists(os.path.join(HERE,"results_realchecks.json")) else None

fig,axs=plt.subplots(2,2,figsize=(14.2,9.4),facecolor="white"); a,b,c,d=axs[0,0],axs[0,1],axs[1,0],axs[1,1]

# (a) fragmentation vs monolithic
e2=R["e2_monolithic"]; frag=e2["fragmented_single_max"]; mono=e2["monolithic"]
x=np.arange(2); w=0.5
vals=[frag["d0_ctrlMW"],mono["d0_ctrlMW"]]; aff=[frag["d0_aff"],mono["d0_aff"]]
bars=a.bar(x,vals,w,color=[TEAL,RED],edgecolor=NAVY,lw=.8)
for i,(v,af) in enumerate(zip(vals,aff)): a.text(i,v+0.12,f"{v:.2f} MW\n{af} 站",ha="center",fontsize=10,color=INK,fontweight="bold")
a.set_xticks(x); a.set_xticklabels([f"碎片化\n(单后台最大={frag['op'][:10]})","单一大平台\n(全城一个CSMS)"],fontsize=9.5)
a.set_ylabel("单次攻陷的受控功率 (MW)",fontsize=10); a.set_ylim(0,max(vals)*1.28)
mult=mono["d0_ctrlMW"]/frag["d0_ctrlMW"] if frag["d0_ctrlMW"] else 0
a.set_title(f"(a) 碎片化 vs 单一平台：单次攻陷爆炸半径\n碎片化把可控功率限制到约 1/{mult:.1f}（{frag['d0_aff']}站 vs 全城{mono['d0_aff']}站）",fontsize=10.6,fontweight="bold",color=NAVY)

# (b) stealth evasion heatmap: residual dE over f x rate
e3=R["e3_stealth"]; fs=sorted({r["f"] for r in e3},reverse=True); rates=sorted({r["rate"] for r in e3},reverse=True)
M=np.zeros((len(fs),len(rates))); DET=np.empty((len(fs),len(rates)),dtype=bool)
for r in e3:
    i=fs.index(r["f"]); j=rates.index(r["rate"]); M[i,j]=r["dE_kwh"]; DET[i,j]=r["detected"]
im=b.imshow(np.log10(M+1),cmap="YlOrRd",aspect="auto")
for i in range(len(fs)):
    for j in range(len(rates)):
        txt=f"{M[i,j]:.0f}"+("" if DET[i,j] else "\n未检出")
        b.text(j,i,txt,ha="center",va="center",fontsize=8,color=("white" if M[i,j]>500 else INK),fontweight=("bold" if not DET[i,j] else "normal"))
b.set_xticks(range(len(rates))); b.set_xticklabels([f"{r}/min" for r in rates],fontsize=9)
b.set_yticks(range(len(fs))); b.set_yticklabels([f"f={f}" for f in fs],fontsize=9)
b.set_xlabel("指令下发速率（越慢越隐蔽）",fontsize=10); b.set_ylabel("限功率深度 f（越浅越隐蔽）",fontsize=10)
b.set_title("(b) 自适应隐蔽攻击的检测盲区（残余ΔE kWh）\n仅当 速率≤1/min 且 f≤0.5（在带内）时两信号同时失明",fontsize=10.6,fontweight="bold",color=NAVY)

# (c) optimal-stopping controller in-engine vs fixed, on stealth attacks (rate=1)
e5=R["e5_controller"]; fs5=[r["f"] for r in e5]; xx=np.arange(len(fs5)); w=0.26
b1=c.bar(xx-w,[r["fixed_dE"] for r in e5],w,color=ORANGE,label="固定规则(一致性)",edgecolor=NAVY,lw=.5)
b2=c.bar(xx,[r["shiryaev_dE"] for r in e5],w,color=TEAL,label="最优停止 Shiryaev(本文)",edgecolor=NAVY,lw=.5)
b3=c.bar(xx+w,[r["cusum_dE"] for r in e5],w,color=PURPLE,label="CUSUM",edgecolor=NAVY,lw=.5)
for i,r in enumerate(e5):
    if r["shi_reduction_pct"]>5: c.text(i,r["shiryaev_dE"]+30,f"−{r['shi_reduction_pct']:.0f}%",ha="center",fontsize=9,color=GREEN,fontweight="bold")
c.set_yscale("symlog"); c.set_xticks(xx); c.set_xticklabels([f"f={f}" for f in fs5],fontsize=9.5)
c.set_xlabel("限功率深度 f（速率=1/min，规避指令速率检测）",fontsize=9.5); c.set_ylabel("残余受控电量 ΔE (kWh)",fontsize=10)
c.set_title("(c) 最优停止控制器嵌入引擎 vs 固定规则（隐蔽攻击）\n对 f=0.5/0.3 降损 84%/64%；f=0.15 过浅，二者皆失（诚实盲区）",fontsize=10.6,fontweight="bold",color=NAVY)
c.legend(fontsize=8.5,loc="upper right")

# (d) synchrony gate: blackout false-isolation vs attack detection
sg=R.get("e1_synchrony_gate",{})
g0=sg.get("gate0",{}); g1=sg.get("gate10",{})
cats=["无同步门","有同步门"]; x=np.arange(2); w=0.36
bo=[g0.get("blackout_false_isolations",0),g1.get("blackout_false_isolations",0)]
at=[g0.get("attack_isolations",0),g1.get("attack_isolations",0)]
d.bar(x-w/2,bo,w,color=RED,label="大停电(全网同步)误隔离数",edgecolor=NAVY,lw=.6)
d.bar(x+w/2,at,w,color=GREEN,label="局部攻击正确隔离数",edgecolor=NAVY,lw=.6)
for i in range(2):
    d.text(i-w/2,bo[i]+0.6,f"{bo[i]}/39",ha="center",fontsize=9.5,color=INK,fontweight="bold")
    d.text(i+w/2,at[i]+0.6,f"{at[i]}/3",ha="center",fontsize=9.5,color=INK,fontweight="bold")
d.set_xticks(x); d.set_xticklabels(cats,fontsize=10); d.set_ylabel("后台隔离次数",fontsize=10); d.set_ylim(0,max(bo+at)+5)
fpr=RC["E1"]["fpr_joint_28d"] if RC else None
sub=f"真实数据良性日误隔离率 {fpr*100:.2f}%（1/348 天）" if fpr is not None else ""
d.set_title(f"(d) 同步门：区分电网级同步跌落与局部攻击\n抑制大停电误隔离(36→0)而不漏判局部攻击；{sub}",fontsize=10.6,fontweight="bold",color=NAVY)
d.legend(fontsize=8.5,loc="upper center")

for ax in (a,c,d):
    for sp in ax.spines.values(): sp.set_color("#C9D6E2")
    ax.tick_params(colors=MUT); ax.grid(axis="y",alpha=.2)
fig.suptitle("图 13　对抗性稳健与真实安全门：碎片化反事实 · 自适应隐蔽攻击 · 最优停止嵌入引擎 · 同步门良性甄别",
             color=NAVY,fontsize=13,fontweight="bold",y=1.0)
fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_ablation_adv.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)
print("[fig] ablation-adv (图13)")
