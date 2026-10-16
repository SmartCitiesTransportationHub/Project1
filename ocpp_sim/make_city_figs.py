"""City-scale (macro) figures from the real multi-operator OCPP simulation.
Reads results_city.json + city_geo.json (produced by export_city.py).
Outputs figC*.png into the project figs/ directory.

Clean macro/micro separation: every figure here is CITY-scale (37+ operators,
621 locations), measured by engine_city.run_city. The AMB cell is shown as the
single highlighted calibration domain, never silently merged with the rest.
"""
import os, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
import shapely.geometry as sg
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":175})

HERE=os.path.dirname(__file__)
FIGS="/home/user/Project1/figs"
R=json.load(open(os.path.join(HERE,"results_city.json")))
G=json.load(open(os.path.join(HERE,"city_geo.json")))
SITES=G["geo"]["sites"]; MUNI=G["geo"]["muni"]; BND=G["geo"]["boundary"]

# palette
BG="#070b11"; STAGE="#0b111a"; MUNI_F="#0e1823"; MUNI_E="#1b2838"; BND_C="#35506e"
IDLE="#39c2d8"; DANGER="#ff4d57"; WARN="#ffb02e"; OK="#35d6a0"; CSMS_C="#c58bff"; FG="#dbe6f2"; MUT="#8295ac"
OPCOLS=["#ff4d57","#ffb02e","#c58bff","#35d6a0","#39c2d8","#f26fb8","#9bd14a","#6f8cff"]
TOP=[o["op"] for o in R["s1_single_backend"]]          # top-8 operators (by MW)
SHORT={o["op"]:o["short"] for o in R["operators"]}
OPCOL={op:OPCOLS[i%len(OPCOLS)] for i,op in enumerate(TOP)}
CITY=R["city"]

def muni_polys():
    out=[]
    for m in MUNI:
        gj=m["geometry"]
        try: out.append((m["properties"].get("nommuni"),sg.shape(gj)))
        except Exception: pass
    return out
MP=muni_polys()
def op_sites(op): return [s for s in SITES if s["opfull"]==op]
def lit_munis(op):
    pts=[sg.Point(s["lon"],s["lat"]) for s in op_sites(op)]
    return set(nm for nm,poly in MP for pt in pts if poly.contains(pt))

def draw_munis(ax,fill=MUNI_F,edge=MUNI_E,lit=None,litcol=None):
    for nm,poly in MP:
        geoms=poly.geoms if poly.geom_type=="MultiPolygon" else [poly]
        fc=litcol if (lit is not None and nm in lit) else fill
        for g in geoms:
            xs,ys=g.exterior.xy
            ax.fill(list(xs),list(ys),fc=fc,ec=edge,lw=.5,zorder=1)
def extent(ax):
    lons=[s["lon"] for s in SITES]; lats=[s["lat"] for s in SITES]
    ax.set_xlim(min(lons)-.02,max(lons)+.02); ax.set_ylim(min(lats)-.02,max(lats)+.02)
    ax.set_aspect(1/np.cos(np.radians(np.mean(lats)))); ax.set_axis_off()

# ---------------------------------------------------------------- figC0 bridge
def fig_bridge():
    fig=plt.figure(figsize=(11,4.3),facecolor="white")
    gs=fig.add_gridspec(1,20,wspace=0)
    axL=fig.add_subplot(gs[0,:8]); axM=fig.add_subplot(gs[0,8:12]); axR=fig.add_subplot(gs[0,12:])
    for ax in (axL,axM,axR): ax.set_axis_off()
    # LEFT: city = 39 backends, one = AMB calibration cell
    axL.set_title("城市层(宏观)：37+ 家运营商 CSMS 后台",fontsize=11,fontweight="bold",color="#16324f")
    rng=np.random.RandomState(7)
    n=len(R["operators"]); xs=rng.rand(n); ys=rng.rand(n)
    sizes=[max(40,o["mw"]/CITY["mw"]*2600) for o in R["operators"]]
    for i,o in enumerate(R["operators"]):
        is_amb=(o["op"]=="AMB公共网络")
        col=OPCOL.get(o["op"],"#c3cad6")
        axL.scatter(xs[i],ys[i],s=sizes[i],c=("#1f6feb" if is_amb else col),
                    edgecolors=("#0b3d91" if is_amb else "white"),lw=(1.6 if is_amb else .6),
                    alpha=.92,zorder=3 if is_amb else 2)
        if is_amb:
            axL.annotate("AMB 公共网络\n(唯一真实会话\n= 标定单元)",(xs[i],ys[i]),xytext=(xs[i]-.02,ys[i]-.34),
                         fontsize=8.2,color="#0b3d91",fontweight="bold",ha="center",
                         arrowprops=dict(arrowstyle="-",color="#0b3d91",lw=1))
    axL.scatter([],[],s=120,c="#c3cad6",label="其他 36 家后台(仅登记容量)")
    axL.text(.02,-.02,f"621 个地点 · {CITY['mw']} MW · 气泡∝额定功率",transform=axL.transAxes,fontsize=8,color=MUT)
    axL.set_xlim(-.05,1.05); axL.set_ylim(-.42,1.08)
    # MIDDLE: transfer arrow
    axM.set_xlim(0,1); axM.set_ylim(0,1)
    axM.annotate("",xy=(.92,.52),xytext=(.08,.52),arrowprops=dict(arrowstyle="-|>",color="#0b3d91",lw=2.4))
    axM.text(.5,.62,"标定迁移",fontsize=10.5,fontweight="bold",color="#0b3d91",ha="center")
    axM.text(.5,.40,"实测每后台攻防动力学\n(扇出速率·检测阈值·\n隔离时间) 按额定容量\n迁移到其余 36 家",
             fontsize=8,color="#33475c",ha="center",va="top")
    # RIGHT: micro cell detail
    axR.set_title("运营商层(微观)：AMB 标定单元",fontsize=11,fontweight="bold",color="#16324f")
    axR.set_xlim(0,1); axR.set_ylim(0,1)
    box=FancyBboxPatch((.06,.12),.88,.78,boxstyle="round,pad=0.02",fc="#eef4fb",ec="#1f6feb",lw=1.4)
    axR.add_patch(box)
    s1_amb=next((x for x in R["s1_single_backend"] if x["op"]=="AMB公共网络"),None)
    lines=["71 个站点 · 2025 全年真实会话","真实 OCPP 1.6 消息回放",
           "——— 实测(真实数据) ———",
           f"攻破后 D0 受控电量 ≈ {s1_amb['d0_dE']:.0f} kWh" if s1_amb else "",
           f"检测+隔离后 ≈ {s1_amb['iso_dE']:.1f} kWh (>99%)" if s1_amb else "",
           "检测时延 τ_d ≈ 0–1 min · 误报 0"]
    for i,t in enumerate(lines):
        axR.text(.5,.80-i*.115,t,fontsize=8.6 if "———" not in t else 8,ha="center",
                 color=("#0b3d91" if "实测" in t or ">99" in t else "#33475c"),
                 fontweight=("bold" if (">99" in t or "真实会话" in t) else "normal"))
    fig.suptitle("图 B　宏观↔微观桥接：城市=各运营商后台之和；以 AMB 一家真实标定，按容量迁移至全城",
                 fontsize=11.5,fontweight="bold",y=1.02,color="#0b1f33")
    fig.savefig(os.path.join(FIGS,"figC0_bridge.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("[figC0] bridge")

# ---------------------------------------------------------------- figC1 city map
def fig_citymap():
    fig,ax=plt.subplots(figsize=(9.6,7.2),facecolor=BG); ax.set_facecolor(STAGE)
    draw_munis(ax)
    for nm,poly in [(b["properties"].get("name"),sg.shape(b["geometry"])) for b in BND]:
        geoms=poly.geoms if poly.geom_type in("MultiPolygon","GeometryCollection") else [poly]
        for g in geoms:
            if g.geom_type!="Polygon": continue
            xs,ys=g.exterior.xy; ax.plot(list(xs),list(ys),color=BND_C,lw=1.1,zorder=2)
    # other operators (grey)
    oth=[s for s in SITES if s["opfull"] not in OPCOL]
    ax.scatter([s["lon"] for s in oth],[s["lat"] for s in oth],s=[max(5,s["cap"]/12) for s in oth],
               c="#45566b",alpha=.55,lw=0,zorder=3,label=None)
    # top-8 operators colored
    for op in TOP:
        ss=op_sites(op)
        ax.scatter([s["lon"] for s in ss],[s["lat"] for s in ss],s=[max(7,s["cap"]/10) for s in ss],
                   c=OPCOL[op],alpha=.9,lw=.3,edgecolors="#0b0f14",zorder=4)
    extent(ax)
    # legend
    hd=[Line2D([0],[0],marker="o",ls="",mfc=OPCOL[op],mec="none",ms=8,
               label=f"{SHORT[op]} · {next(o['mw'] for o in R['operators'] if o['op']==op)} MW") for op in TOP]
    hd.append(Line2D([0],[0],marker="o",ls="",mfc="#45566b",mec="none",ms=7,label="其余 31 家运营商"))
    ax.legend(handles=hd,loc="upper left",fontsize=8.1,framealpha=.15,labelcolor=FG,
              facecolor="#0e1823",edgecolor="#223246",ncol=1)
    ax.set_title(f"图 C1　巴塞罗那大都会区多运营商充电控制平面：{CITY['n_loc']} 个地点 · {CITY['mw']} MW · "
                 f"{CITY['n_operators']} 个独立 CSMS 后台",color=FG,fontsize=11.5,fontweight="bold",pad=8)
    ax.text(.01,.01,"点大小∝额定功率 · 颜色=运营商后台(前 8 家) · 底图=36 个市镇",transform=ax.transAxes,color=MUT,fontsize=8)
    fig.savefig(os.path.join(FIGS,"figC1_citymap.png"),bbox_inches="tight",facecolor=BG); plt.close(fig)
    print("[figC1] citymap")

# ---------------------------------------------------------------- figC2 single-backend blast radius
def fig_blast_single():
    # pick the widest-reach (Endesa) and the most-concentrated (BSM) among top ops by munis
    s1={x["op"]:x for x in R["s1_single_backend"]}
    # macro contrast: largest/widest backend (Endesa) vs dense city-center backend (BSM)
    W="ENDESA X WAY, S.L."; C="BARCELONA DE SERVEIS MUNICIPALS, SA"
    wide=(W,len(lit_munis(W)),s1[W]); conc=(C,len(lit_munis(C)),s1[C])
    fig,axs=plt.subplots(1,2,figsize=(13,6),facecolor=BG)
    for ax,(op,nmun,rec) in zip(axs,[(wide[0],wide[1],wide[2]),(conc[0],conc[1],conc[2])]):
        ax.set_facecolor(STAGE); lm=lit_munis(op)
        draw_munis(ax,lit=lm,litcol="#2a1420")
        ss=op_sites(op)
        oth=[s for s in SITES if s["opfull"]!=op]
        ax.scatter([s["lon"] for s in oth],[s["lat"] for s in oth],s=5,c="#2f3d4e",alpha=.5,lw=0,zorder=3)
        ax.scatter([s["lon"] for s in ss],[s["lat"] for s in ss],s=[max(10,s["cap"]/8) for s in ss],
                   c=DANGER,alpha=.92,lw=.3,edgecolors="#120608",zorder=5)
        extent(ax)
        share=rec["share"]*100
        ax.set_title(f"攻破 {SHORT[op]} 后台",color=FG,fontsize=12,fontweight="bold",pad=6)
        txt=(f"可控 {rec['mw']} MW ({share:.1f}% 城市功率) · {rec['n_loc']} 站 · {nmun} 市镇\n"
             f"无防御受控电量 {rec['d0_dE']:.0f} kWh → 检测+隔离 {rec['iso_dE']:.1f} kWh (−{100*(1-rec['iso_dE']/rec['d0_dE']):.1f}%)")
        ax.text(.5,-.02,txt,transform=ax.transAxes,color=FG,fontsize=8.8,ha="center",va="top")
    fig.suptitle("图 C2(GIS)　单后台沦陷的地理爆炸半径：覆盖面 vs 集中度（真实城市仿真实测）",
                 color=FG,fontsize=12.5,fontweight="bold",y=1.02)
    fig.savefig(os.path.join(FIGS,"figC2_blast_single.png"),bbox_inches="tight",facecolor=BG); plt.close(fig)
    print(f"[figC2] blast_single wide={SHORT[wide[0]]}({wide[1]}muni) conc={SHORT[conc[0]]}({conc[1]}muni)")

# ---------------------------------------------------------------- figC3 per-operator measured
def fig_single_backend():
    s1=R["s1_single_backend"]
    ops=[x["short"] for x in s1]; d0=[x["d0_dE"] for x in s1]; iso=[x["iso_dE"] for x in s1]
    share=[x["share"]*100 for x in s1]; y=np.arange(len(ops))
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,4.8),facecolor="white",gridspec_kw={"width_ratios":[2.3,1]})
    ax1.barh(y+.18,d0,height=.36,color="#e2506a",label="无防御 D0（被发现前受控电量）")
    ax1.barh(y-.18,iso,height=.36,color="#2f9e6f",label="检测+隔离 D3+D5")
    ax1.set_yticks(y); ax1.set_yticklabels(ops,fontsize=9); ax1.invert_yaxis()
    ax1.set_xlabel("单后台沦陷的受控电量 ΔE (kWh)",fontsize=9.5)
    for i,(a,b) in enumerate(zip(d0,iso)):
        ax1.text(a+max(d0)*.01,i+.18,f"{a:.0f}",va="center",fontsize=7.6,color="#b3324c")
        cut=100*(1-b/a) if a else 0
        ax1.text(max(d0)*.01,i-.18,f"{b:.1f}  (−{cut:.1f}%)",va="center",fontsize=7.4,color="#1f6f4c")
    ax1.legend(fontsize=8.6,loc="lower right"); ax1.set_title("(a) 每家后台：爆炸半径与逐后台遏制（实测）",fontsize=10,fontweight="bold")
    ax1.grid(axis="x",alpha=.25)
    # share vs dE scatter
    ax2.scatter(share,d0,s=70,c=[OPCOL.get(x["op"],"#8aa") for x in s1],edgecolors="#333",lw=.5,zorder=3)
    for x,sh,dd in zip(s1,share,d0): ax2.annotate(x["short"],(sh,dd),fontsize=7,color="#334",xytext=(3,2),textcoords="offset points")
    ax2.set_xlabel("占城市功率份额 (%)",fontsize=9); ax2.set_ylabel("ΔE (kWh)",fontsize=9)
    ax2.set_title("(b) 爆炸半径∝后台份额",fontsize=10,fontweight="bold"); ax2.grid(alpha=.25)
    fig.suptitle("图 C3　单后台沦陷：爆炸半径由运营商份额决定，逐后台隔离普遍 >99% 削减（城市仿真实测）",
                 fontsize=11.5,fontweight="bold",y=1.02)
    fig.savefig(os.path.join(FIGS,"figC3_single_backend.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("[figC3] single_backend")

# ---------------------------------------------------------------- figC4 coordinated campaign
def fig_campaign():
    s2=R["s2_campaign"]
    fig=plt.figure(figsize=(13,5.6),facecolor=BG)
    gs=fig.add_gridspec(1,2,width_ratios=[1.05,1],wspace=.12)
    axm=fig.add_subplot(gs[0,0]); axm.set_facecolor(STAGE)
    K=5; campaign_ops=TOP[:K]
    lm=set().union(*[lit_munis(op) for op in campaign_ops])
    draw_munis(axm,lit=lm,litcol="#241526")
    oth=[s for s in SITES if s["opfull"] not in campaign_ops]
    axm.scatter([s["lon"] for s in oth],[s["lat"] for s in oth],s=5,c="#2f3d4e",alpha=.5,lw=0,zorder=3)
    shades=["#ff3b46","#ff7a2e","#ffb02e","#ffd24a","#f26fb8"]
    for i,op in enumerate(campaign_ops):
        ss=op_sites(op)
        axm.scatter([s["lon"] for s in ss],[s["lat"] for s in ss],s=[max(9,s["cap"]/9) for s in ss],
                    c=shades[i],alpha=.9,lw=.2,edgecolors="#120608",zorder=5,label=f"{SHORT[op]}")
    extent(axm)
    axm.legend(loc="upper left",fontsize=7.8,framealpha=.15,labelcolor=FG,facecolor="#0e1823",edgecolor="#223246",title="协同攻破的后台",title_fontsize=8)
    axm.get_legend().get_title().set_color(FG)
    axm.set_title(f"(a)(GIS) 协同攻破前 {K} 家后台：{s2[K-1]['mw']:.1f} MW 波及 {len(lm)} 市镇",color=FG,fontsize=10.5,fontweight="bold",pad=6)
    # curve
    axc=fig.add_subplot(gs[0,1]); axc.set_facecolor("#0d141d")
    k=[x["k"] for x in s2]; de0=[x["d0_dE"] for x in s2]; dei=[x["iso_dE"] for x in s2]; mw=[x["mw"] for x in s2]
    axc.plot(k,de0,"-o",color=DANGER,lw=2,ms=5,label="无防御 ΔE")
    axc.plot(k,dei,"-o",color=OK,lw=2,ms=5,label="各后台检测+隔离 ΔE")
    axc.fill_between(k,de0,dei,color=DANGER,alpha=.12)
    axc.set_xlabel("协同攻破的后台数 k (按功率降序)",color=FG,fontsize=9.5)
    axc.set_ylabel("城市被发现前受控电量 ΔE (kWh)",color=DANGER,fontsize=9.5)
    axc.tick_params(colors=FG);
    for s in axc.spines.values(): s.set_color("#223246")
    ax2=axc.twinx(); ax2.plot(k,mw,"--s",color=WARN,lw=1.4,ms=4,label="攻破容量 (MW)")
    ax2.set_ylabel("攻破额定功率 (MW)",color=WARN,fontsize=9.5); ax2.tick_params(colors=WARN)
    lines=axc.get_legend_handles_labels()[0]+ax2.get_legend_handles_labels()[0]
    labs=axc.get_legend_handles_labels()[1]+ax2.get_legend_handles_labels()[1]
    axc.legend(lines,labs,fontsize=8,loc="center right",framealpha=.2,labelcolor=FG,facecolor="#0e1823",edgecolor="#223246")
    axc.set_title("(b) 协同campaign的累积爆炸半径：需多次独立攻破才接近全城",color=FG,fontsize=10.5,fontweight="bold")
    axc.grid(alpha=.15)
    fig.suptitle("图 C4　协同多后台campaign：控制平面碎片化把爆炸半径下界锁死——逐后台隔离即便在协同攻击下仍遏制(实测)",
                 color=FG,fontsize=11.5,fontweight="bold",y=1.03)
    fig.savefig(os.path.join(FIGS,"figC4_campaign.png"),bbox_inches="tight",facecolor=BG); plt.close(fig)
    print("[figC4] campaign")

# ---------------------------------------------------------------- figC6 vector matrix (city)
def fig_vectors():
    s3=R["s3_vectors_top3"]
    vks=["curtail","remote_stop","mitm_meter","dos"]; dks=["none","iso","rliso"]
    dlab={"none":"D0 无防御","iso":"D3+D5 检测+隔离","rliso":"D2+D3+D5 限速+隔离"}
    fig,axs=plt.subplots(1,2,figsize=(12.5,4.6),facecolor="white",gridspec_kw={"width_ratios":[1.4,1]})
    ax=axs[0]
    M=np.array([[s3[v][d]["dE"] for d in dks] for v in vks])
    im=ax.imshow(np.log10(M+1),cmap="RdYlGn_r",aspect="auto")
    ax.set_xticks(range(3)); ax.set_xticklabels([dlab[d] for d in dks],fontsize=8.5)
    ax.set_yticks(range(4)); ax.set_yticklabels([s3[v]["label"] for v in vks],fontsize=9)
    for i in range(4):
        for j in range(3):
            v=M[i,j]; ax.text(j,i,f"{v:.0f}",ha="center",va="center",fontsize=9,
                              color="white" if np.log10(v+1)>2.4 else "#15200f",fontweight="bold")
    ax.set_title("(a) 城市受控电量 ΔE (kWh，攻破前 3 家后台)",fontsize=10,fontweight="bold")
    # billing / denied bars
    ax2=axs[1]
    bill=[s3["mitm_meter"][d]["billing"] for d in dks]; den=[s3["dos"][d]["denied"] for d in dks]
    x=np.arange(3); w=.38
    ax2.bar(x-w/2,bill,w,color="#c58bff",label="A1 篡改电表计费偏差 (€)")
    ax2b=ax2.twinx(); ax2b.bar(x+w/2,den,w,color="#39c2d8",label="A4 DoS 被拒会话")
    ax2.set_xticks(x); ax2.set_xticklabels([dlab[d].split()[0] for d in dks],fontsize=8.5)
    ax2.set_ylabel("计费偏差 (€)",color="#7a4fd0",fontsize=9); ax2b.set_ylabel("被拒会话",color="#2b8fa3",fontsize=9)
    ax2.set_title("(b) 偷电/拒绝类后果与遏制",fontsize=10,fontweight="bold")
    h1,l1=ax2.get_legend_handles_labels(); h2,l2=ax2b.get_legend_handles_labels()
    ax2.legend(h1+h2,l1+l2,fontsize=7.6,loc="upper right")
    fig.suptitle("图 C6　城市层攻击向量 × 防御（真实多运营商仿真实测）：隔离对限功率/停充/ DoS 决定性有效，TLS 才压制篡改",
                 fontsize=11,fontweight="bold",y=1.02)
    fig.savefig(os.path.join(FIGS,"figC6_vectors.png"),bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("[figC6] vectors")

# ---------------------------------------------------------------- figC5 city storyboard (dark SOC)
def fig_storyboard():
    s2={x["k"]:x for x in R["s2_campaign"]}
    stages=[("t₀  入口：攻破最大后台",[TOP[0]],"spread"),
            ("t+1min  协同扩散：前 3 家后台",TOP[:3],"spread"),
            ("无遏制  协同前 5 家后台=最大爆炸半径",TOP[:5],"blast"),
            ("检测+隔离  逐后台遏制→本地恢复",TOP[:5],"contain")]
    fig,axs=plt.subplots(1,4,figsize=(17,4.8),facecolor=BG)
    for ax,(cap,ops,mode) in zip(axs,stages):
        ax.set_facecolor(STAGE)
        lm=set().union(*[lit_munis(o) for o in ops]) if mode!="t0" else lit_munis(ops[0])
        draw_munis(ax,lit=lm,litcol=("#241526" if mode!="contain" else "#122017"))
        oth=[s for s in SITES if s["opfull"] not in ops]
        ax.scatter([s["lon"] for s in oth],[s["lat"] for s in oth],s=4,c="#2a3645",alpha=.5,lw=0,zorder=3)
        # CSMS anchor (top center)
        lons=[s["lon"] for s in SITES]; lats=[s["lat"] for s in SITES]
        cx=np.mean(lons); cyy=max(lats)+.012
        col=OK if mode=="contain" else DANGER
        for op in ops:
            ss=op_sites(op)
            ax.scatter([s["lon"] for s in ss],[s["lat"] for s in ss],s=[max(8,s["cap"]/9) for s in ss],
                       c=col,alpha=.92,lw=.2,edgecolors="#120608",zorder=5)
            if mode in("spread","blast"):
                for s in ss[:: max(1,len(ss)//14)]:
                    ax.plot([cx,s["lon"]],[cyy,s["lat"]],color=DANGER,lw=.4,alpha=.25,zorder=4)
        ax.scatter([cx],[cyy],s=70,c=CSMS_C,marker="s",zorder=6,edgecolors="white",lw=.5)
        ax.text(cx,cyy+.004,"攻击者 → CSMS 后台",color="#d8b6ff",fontsize=7.5,ha="center")
        extent(ax)
        ax.set_title(cap,color=FG,fontsize=9.8,fontweight="bold",pad=4)
        if mode=="blast":
            ax.text(.5,-.03,f"受控 {s2[5]['d0_dE']:.0f} kWh · {s2[5]['d0_aff']} 站 · {s2[5]['mw']:.1f} MW",
                    transform=ax.transAxes,color=DANGER,fontsize=8.6,ha="center",va="top",fontweight="bold")
        if mode=="contain":
            cut=100*(1-s2[5]['iso_dE']/s2[5]['d0_dE'])
            ax.text(.5,-.03,f"受控电量 {s2[5]['d0_dE']:.0f} → {s2[5]['iso_dE']:.1f} kWh (−{cut:.1f}%)",
                    transform=ax.transAxes,color=OK,fontsize=8.6,ha="center",va="top",fontweight="bold")
    fig.suptitle("图 C5(GIS)　城市协同campaign攻防时间线回放（真实多运营商仿真驱动）：协同扩散 → 最大爆炸半径 → 逐后台隔离遏制",
                 color=FG,fontsize=12,fontweight="bold",y=1.03)
    fig.savefig(os.path.join(FIGS,"figC5_storyboard.png"),bbox_inches="tight",facecolor=BG); plt.close(fig)
    print("[figC5] storyboard")

if __name__=="__main__":
    os.makedirs(FIGS,exist_ok=True)
    fig_bridge(); fig_citymap(); fig_blast_single(); fig_single_backend(); fig_campaign(); fig_storyboard(); fig_vectors()
    print("[DONE] city figures ->",FIGS)
