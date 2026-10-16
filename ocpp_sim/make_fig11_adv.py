"""Advanced dark SOC-style GIS attack-defense storyboard (fig11) from real OCPP-sim data."""
import os, json, sqlite3
import numpy as np, pandas as pd, shapely.wkb
from pyproj import Transformer
from shapely.ops import transform as _shp_transform
_T=Transformer.from_crs('EPSG:25831','EPSG:4326',always_xy=True)
_reproj=lambda g:_shp_transform(lambda x,y,z=None:_T.transform(x,y),g)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":170})
BG="#ffffff"; STAGE="#f4f7fb"; MUNI="#e6edf5"; MUNIE="#b7c6d6"; BND="#5b7b8a"
IDLE="#1aa3c4"; DANGER="#e8384f"; WARN="#f08a24"; OK="#1ea97c"; CSMS="#8b4ddb"; FG="#1a2633"; MUT="#5d6b7a"
DATA=os.environ.get("AMB_DATA","/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/amb_data/supp")
OUT="/home/user/Project1/figs"
AD=json.load(open(os.path.join(os.path.dirname(__file__),"artifact_data.json")))

def gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return shapely.wkb.loads(bytes(b[hdr:]))
con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
def layer(name,simp=40):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    df=pd.DataFrame(con.execute(f'SELECT * FROM "{name}"').fetchall(),columns=cols)
    df["g"]=df["geom"].apply(lambda b: _reproj(gpkg_geom(b).simplify(simp)) if b else None); return df
muni=layer("municipalities"); bnd=layer("amb_boundary")
sites={s["properties"]["site_id"]:s["geometry"]["coordinates"] for s in AD["geo"]["sites"]}
D0=AD["sim"]["curtail"]["none"]; DI=AD["sim"]["curtail"]["iso"]
cx=np.median([v[0] for v in sites.values()]); cyy=max(v[1] for v in sites.values())+0.013  # CSMS anchor top (deg)
def basemap(ax):
    ax.set_facecolor(STAGE)
    for g in muni["g"]:
        if g is None: continue
        for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
            xs,ys=p.exterior.xy; ax.fill(xs,ys,facecolor=MUNI,edgecolor=MUNIE,lw=.4,zorder=1)
    for g in bnd["g"]:
        for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
            xs,ys=p.exterior.xy; ax.plot(xs,ys,color=BND,lw=1.2,zorder=2)
    ax.set_aspect(1/np.cos(np.radians(41.4))); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(MUNIE)
def beams(ax,comp):
    for sid in comp:
        x,y=sites[sid]
        ax.add_patch(FancyArrowPatch((cx,cyy),(x,y),arrowstyle="-",color=DANGER,lw=.5,alpha=.35,zorder=3))
def nodes(ax,t,cfg,detect=None,rec=None,recovered=False):
    cur=cfg["attack"]
    comp=[s for s in sites if (s in cur and cur[s]<=t and not(recovered))]
    for sid,(x,y) in sites.items():
        st_c=sid in cur and cur[sid]<=t
        if recovered and st_c: col,r=OK,22
        elif st_c: col,r=DANGER,30
        else: col,r=IDLE,14
        if st_c and not recovered: ax.scatter([x],[y],s=r*3.2,facecolor=DANGER,alpha=.18,lw=0,zorder=4)
        ax.scatter([x],[y],s=r,c=col,edgecolor="#33465a",lw=.5,zorder=6)
        if detect and st_c and not recovered:
            ax.scatter([x],[y],s=r*4.5,facecolor="none",edgecolor=WARN,lw=1.1,zorder=5)
    return comp
def csms(ax,hit):
    ax.scatter([cx],[cyy],s=150,c=(DANGER if hit else CSMS),edgecolor="#4a2580",lw=1.2,zorder=8,marker="s")
    ax.text(cx,cyy+0.009,"CSMS",color=(DANGER if hit else CSMS),fontsize=8,ha="center",va="bottom",zorder=8)

fig=plt.figure(figsize=(13.4,4.3)); fig.patch.set_facecolor(BG)
phases=[
 ("T+0.0 min","CSMS 被攻破，首站被控", D0, 0.05, None, False, None),
 ("T+0.6 min","指令扇出，攻击沿地理扩散", D0, 0.6, None, False, None),
 ("T+2.0 min","无遏制 → 全网 57 站被控", D0, 3.0, None, False, "受控≈0.89 MW"),
 ("检测+隔离 · T+1 min","告警→按运营商隔离→恢复", DI, 1.0, True, True, "ΔE 9.5 kWh（无防御 2115）"),
]
for i,(tt,sub,cfg,t,det,recov,note) in enumerate(phases):
    ax=fig.add_subplot(1,4,i+1); basemap(ax)
    comp=nodes(ax,t,cfg,detect=det,recovered=recov)
    if not recov: beams(ax,comp)
    csms(ax,hit=len(comp)>0 and not recov)
    ax.set_title(tt,color=FG,fontsize=10.5,fontweight="bold",pad=6,loc="left")
    ax.text(0.0,1.005,"",transform=ax.transAxes)
    ax.text(0.5,-0.04,sub,transform=ax.transAxes,color=MUT,fontsize=8.5,ha="center",va="top")
    nc=len([s for s in cfg["attack"] if cfg["attack"][s]<=t])
    tag=f"受控 {nc} 站" + (f" · {note}" if note else "")
    ax.text(0.02,0.03,tag,transform=ax.transAxes,color=(OK if recov else DANGER),fontsize=8,
            ha="left",va="bottom",family="WenQuanYi Zen Hei",
            bbox=dict(boxstyle="round,pad=0.3",fc="#ffffff",ec="#c2cedb"))
fig.suptitle("GIS 攻防时间线：真实 OCPP 1.6 仿真回放（AMB/Iberdrola 后台；地理为真实站点）",
             color=FG,fontsize=12,fontweight="bold",y=1.04)
fig.text(0.5,-0.02,"正常站点 ● 青  ·  被控 ● 红  ·  告警 ○ 橙环  ·  已隔离/恢复 ● 绿  ·  ■ 运营商后台 CSMS  ·  红线=攻击指令扇出",
         color=MUT,fontsize=8.5,ha="center")
fig.savefig(os.path.join(OUT,"fig11_gis_timeline.png"),facecolor=BG,bbox_inches="tight")
print("[FIG] fig11_gis_timeline.png (advanced dark storyboard)")
print("D0 sites@0.6min:",len([s for s in D0['attack'] if D0['attack'][s]<=0.6]),"| DI curtailed:",len(DI['attack']))
