"""Animated 3D-bar GIS attack/defense GIF from real OCPP-sim data (detect+isolate, curtail)."""
import os, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import matplotlib.font_manager as fm
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False})
BG="#070b11"; IDLE=(0.22,0.76,0.85); DANGER=(1,0.30,0.34); OK=(0.21,0.84,0.63); CSMS=(0.77,0.55,1); MUT="#7f90a6"; FG="#dce7f3"
AD=json.load(open(os.path.join(os.path.dirname(__file__),"artifact_data.json")))
sites={s["properties"]["site_id"]:(s["geometry"]["coordinates"],s["properties"]["pkw"]) for s in AD["geo"]["sites"]}
muni=AD["geo"]["muni"]; S=AD["sim"]["curtail"]["iso"]
lons=[v[0][0] for v in sites.values()]; lats=[v[0][1] for v in sites.values()]
cx=np.mean(lons); cyy=max(lats)+0.012; recov=S["recovery"]; detect=S["t_detect"]
def state(id,t):
    ct=S["attack"].get(id)
    if ct is None or t<ct: return "idle"
    if recov is not None and t>=recov: return "rec"
    return "cut"
def poly_lines(ax):
    for m in muni:
        gc=m["geometry"]["coordinates"]; polys=gc if m["geometry"]["type"]=="MultiPolygon" else [gc]
        for pg in polys:
            ring=pg[0] if isinstance(pg[0][0],list) else pg
            xs=[p[0] for p in ring]; ys=[p[1] for p in ring]
            ax.plot(xs,ys,[0]*len(xs),color="#24303f",lw=.5,zorder=1)
fig=plt.figure(figsize=(8,5),facecolor=BG)
ax=fig.add_subplot(111,projection="3d",facecolor=BG)
FRAMES=np.concatenate([np.arange(0,1.6,0.06), np.arange(1.6,3.01,0.18)])
def draw(t):
    ax.clear(); ax.set_facecolor(BG)
    poly_lines(ax)
    # CSMS marker
    ax.scatter([cx],[cyy],[600/80000],c=[CSMS],s=60,marker="s",depthshade=False,zorder=6)
    ax.text(cx,cyy,0.012,"CSMS",color="#c58bff",fontsize=7,ha="center")
    ncut=0; mw=0
    for sid,((lo,la),pk) in sites.items():
        st=state(sid,t)
        h=(pk/1200.0)*(0.30 if st=="cut" else 1.0)   # cut bars stay visibly red but shortened
        col=IDLE if st=="idle" else (DANGER if st=="cut" else OK)
        ax.bar3d(lo-0.0016,la-0.0016,0,0.0032,0.0032,max(h,0.0006),color=col,shade=True,alpha=.95,zorder=5)
        if st=="cut":
            ncut+=1
            ax.plot([cx,lo],[cyy,la],[0.012,h],color=DANGER,lw=.5,alpha=.35,zorder=4)
    kw=max(0,np.interp(t,[m for m in S["mins"] if m>=-1],[v for i,v in enumerate(S["ctrl_mw"]) if S["mins"][i]>=-1]))
    ax.set_title(f"GIS 3D 攻防回放 · 真实 OCPP 仿真   T+{t:04.1f} min   受控 {kw:.2f} MW · {ncut} 站",
                 color=FG,fontsize=11,fontweight="bold",pad=2)
    ax.view_init(elev=40, azim=-62+t*6.0)
    ax.set_xlim(min(lons)-.02,max(lons)+.02); ax.set_ylim(min(lats)-.02,max(lats)+.02); ax.set_zlim(0,0.09)
    ax.set_axis_off()
    # phase caption
    cap="攻击扩散" if (detect is None or t<detect) else ("检测触发 → 隔离" if (recov and t<recov) else "隔离后恢复")
    ax.text2D(0.5,0.02,cap,transform=ax.transAxes,color=MUT,fontsize=9,ha="center")
anim=FuncAnimation(fig,draw,frames=FRAMES,interval=120)
out=os.path.join(os.path.dirname(__file__),"attack_defense_3d.gif")
anim.save(out,writer=PillowWriter(fps=9),dpi=96,savefig_kwargs={"facecolor":BG})
print("[GIF]",out,"%.1f MB"%(os.path.getsize(out)/1e6),"frames",len(FRAMES))
