"""GIS attack-defense maps (fig07-12) for the OCPP paper, from real AMB geodata.
Run: python3 -I make_gis.py   (prints [CHECK]/[FIG] lines)
"""
import os, sqlite3, math
import numpy as np, pandas as pd
import shapely.wkb
from shapely.geometry import Point
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

DATA = os.environ.get("AMB_DATA", "./supp")  # 解压后的数据目录（dgt_nap/、charging_*.csv、amb_charging.gpkg）
OUT  = os.environ.get("AMB_FIGS", "./figs")
os.makedirs(OUT,exist_ok=True)
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,
    "font.size":10,"axes.titlesize":11,"axes.titleweight":"bold","figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight"})
OI=dict(black="#000000",orange="#E69F00",sky="#56B4E9",green="#009E73",yellow="#F0E442",
        blue="#0072B2",verm="#D55E00",purple="#CC79A7",grey="#8C8C8C")
INK="#222"; MUT="#6b6b6b"

def gpkg_geom(b):
    f=b[3]; env=(f>>1)&7; hdr=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return shapely.wkb.loads(bytes(b[hdr:]))
def layer(con,name):
    cols=[r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
    df=pd.DataFrame(con.execute(f'SELECT * FROM "{name}"').fetchall(),columns=cols)
    if "geom" in df: df["g"]=df["geom"].apply(lambda b: gpkg_geom(b) if b is not None else None)
    return df
def polys(ax,df,**kw):
    for g in df["g"]:
        if g is None: continue
        for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
            xs,ys=p.exterior.xy; ax.fill(xs,ys,**kw)
def outline(ax,df,**kw):
    for g in df["g"]:
        if g is None: continue
        for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
            xs,ys=p.exterior.xy; ax.plot(xs,ys,**kw)
def nomap(ax):
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

con=sqlite3.connect(os.path.join(DATA,"amb_charging.gpkg"))
sites=layer(con,"amb_sites"); muni=layer(con,"municipalities"); bound=layer(con,"amb_boundary")
reg=layer(con,"registry_locations"); h3=layer(con,"h3_zones"); roads=layer(con,"roads_major")
sites["x"]=[g.x for g in sites.g]; sites["y"]=[g.y for g in sites.g]
reg["x"]=[g.x for g in reg.g]; reg["y"]=[g.y for g in reg.g]
# registry record centroids for muni assignment not needed; use DGT P table for operator->muni & muni MW
D=os.path.join(DATA,"dgt_nap")
P=pd.read_csv(os.path.join(D,"dgt_refill_points_amb.csv"),dtype={"site_id":str})
S=pd.read_csv(os.path.join(D,"dgt_sites_amb.csv"),dtype={"site_id":str},low_memory=False)
P=P.merge(S[["site_id","operator_id","operator","nommuni"]],on="site_id",how="left")
P["dc_kw"]=P.max_dc_kw.where(P.has_dc,0).fillna(0)
muni_mw=P.groupby("nommuni").agg(mw=("max_kw",lambda x:x.sum()/1000),dc=("dc_kw",lambda x:x.sum()/1000),
        pts=("point_id","size"),dcpts=("has_dc","sum")).reset_index()
muni["nm"]=muni["nommuni"].astype(str)
mm=muni.merge(muni_mw,left_on="nm",right_on="nommuni",how="left").fillna({"mw":0,"dc":0,"pts":0,"dcpts":0})
print("[CHECK] muni with MW:",(mm.mw>0).sum(),"of",len(mm),"; total muni MW=%.1f"%mm.mw.sum())

# per-site evening denied sessions (DoS 18-21h) from hourly csv
H=pd.read_csv(os.path.join(DATA,"charging_site_hourly_utc_v2.csv"))
H["hour_utc"]=pd.to_datetime(H["hour_utc"],utc=True,errors="coerce")
H["h"]=H["hour_utc"].dt.hour; H["d"]=H["hour_utc"].dt.date
ndays=H["d"].nunique()
ev=H[(H.h>=18)&(H.h<21)].groupby("site_id").session_count.sum()/ndays  # avg daily evening sessions per site (3h)
sites["ev_den"]=sites.site_id.map(ev).fillna(0)
site_muni_den=sites.groupby("muni").ev_den.sum()
mm["ev_den"]=mm["nm"].map(lambda m: site_muni_den.get(m,0))
print("[CHECK] evening-window daily sessions total=%.1f; top site=%.1f"%(sites.ev_den.sum(),sites.ev_den.max()))

def save(fig,n): fig.savefig(os.path.join(OUT,n)); plt.close(fig); print("[FIG]",n)
def basemap(ax,fill="#f3f3f1",ec="#dcdcd8"):
    polys(ax,muni,facecolor=fill,edgecolor=ec,lw=.4,zorder=1)
    outline(ax,bound,color=MUT,lw=1.0,zorder=2)

# ===== fig07 GIS attack-surface: operators + controllable MW =====
fig,ax=plt.subplots(figsize=(7.4,5.6)); basemap(ax)
# color 621 registry locations by DC capability; AMB sites outlined
reg["col"]=np.where(reg.has_dc100==1,OI["verm"],np.where(reg.has_dc==1,OI["orange"],"#b9b9b6"))
ax.scatter(reg.x,reg.y,s=10,c=reg.col,lw=0,alpha=.85,zorder=3)
ax.scatter(sites.x,sites.y,s=34,facecolor="none",edgecolor=OI["blue"],lw=1.3,zorder=5)
nd100=int((reg.has_dc100==1).sum()); ndc=int(((reg.has_dc==1)&(reg.has_dc100!=1)).sum()); nac=int((reg.has_dc!=1).sum())
nomap(ax); ax.set_title("攻击面地图：多运营商设施的直流能力分布（高价值目标）")
leg=[Line2D([0],[0],marker='o',color='w',markerfacecolor=OI["verm"],ms=8,label=f'登记点·含>100kW直流（{nd100}）'),
     Line2D([0],[0],marker='o',color='w',markerfacecolor=OI["orange"],ms=8,label=f'登记点·含直流（{ndc}）'),
     Line2D([0],[0],marker='o',color='w',markerfacecolor="#b9b9b6",ms=8,label=f'登记点·仅交流（{nac}）'),
     Line2D([0],[0],marker='o',color='w',markerfacecolor='none',markeredgecolor=OI["blue"],ms=9,label='AMB 网络站点(71)')]
ax.legend(handles=leg,loc="lower left",fontsize=7.5,frameon=False)
ax.text(.99,.01,"直流桩功率高、集中度高，是协同功率操纵的高价值目标",transform=ax.transAxes,ha="right",va="bottom",fontsize=7,color=MUT)
save(fig,"fig07_gis_surface.png")

# ===== fig08 GIS blast radius: 3 operators compromised =====
fig,axs=plt.subplots(1,3,figsize=(11,4.1))
targets=[("ENDESA X WAY","Endesa X Way",12.33),("IBERDROLA CLIENTES","Iberdrola Clientes",9.75),
         ("BARCELONA DE SERVEIS","BSM",8.67)]
for ax,(sub,lab,mw) in zip(axs,targets):
    munis_hit=set(P[P.operator.str.contains(sub,case=False,na=False)].nommuni.dropna())
    for _,r in mm.iterrows():
        g=r.g; hit=r.nm in munis_hit
        for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
            xs,ys=p.exterior.xy; ax.fill(xs,ys,facecolor=(OI["verm"] if hit else "#f0f0ee"),
                alpha=(.30 if hit else 1),edgecolor="#dcdcd8",lw=.4,zorder=1)
    outline(ax,bound,color=MUT,lw=.9,zorder=2)
    m=reg[reg.operator.str.contains(sub,case=False,na=False)]
    ax.scatter(m.x,m.y,s=16,c=OI["verm"],lw=0,zorder=4)
    nomap(ax); ax.set_title(f"{lab} 后台被攻破\n可控 {mw:.1f} MW · {len(munis_hit)} 市镇",fontsize=9.5)
fig.suptitle("后台沦陷的地理爆炸半径（红：受影响市镇与该运营商站点）",y=1.02,fontsize=11,fontweight="bold")
save(fig,"fig08_gis_blast.png")
print("[CHECK] blast munis: Endesa=%d Iberdrola=%d BSM=%d"%(
    len(set(P[P.operator.str.contains('ENDESA',case=False,na=False)].nommuni.dropna())),
    len(set(P[P.operator.str.contains('IBERDROLA',case=False,na=False)].nommuni.dropna())),
    len(set(P[P.operator.str.contains('BARCELONA DE SERVEIS',case=False,na=False)].nommuni.dropna()))))

# ===== fig09 GIS RFID clone exposure =====
fig,(a1,a2)=plt.subplots(1,2,figsize=(11,4.6))
# left: map of registry locations (RFID accepted at 92.5% -> treat nearly all as exposed); color by zone
basemap(a1)
a1.scatter(reg.x,reg.y,s=12,c=OI["orange"],lw=0,alpha=.8,zorder=3,label="接受 RFID 的登记地点")
a1.scatter(sites.x,sites.y,s=26,facecolor="none",edgecolor=OI["blue"],lw=1.1,zorder=5,label="AMB 网络站点")
nomap(a1); a1.set_title("(a) RFID 克隆暴露面（92.5% 充电点接受 RFID）",fontsize=10)
a1.legend(loc="lower left",fontsize=7.5,frameon=False)
# right: exposure by functional zone (count of DC points accepting rfid by zone of registry_locations)
reg["zone_zh"]=reg["zone_zh"].fillna("其他")
zc=reg.groupby("zone_zh").size().sort_values()
a2.barh(range(len(zc)),zc.values,color=OI["orange"],height=.6)
a2.set_yticks(range(len(zc))); a2.set_yticklabels(zc.index,fontsize=8)
for i,v in enumerate(zc.values): a2.text(v+2,i,str(v),va="center",fontsize=8,color=INK)
a2.set_xlabel("登记地点数"); a2.set_title("(b) 按功能分区的暴露密度",fontsize=10)
for s in ["top","right"]: a2.spines[s].set_visible(False)
fig.suptitle("RFID 克隆/重放攻击面的空间与分区分布",y=1.02,fontsize=11,fontweight="bold")
save(fig,"fig09_gis_rfid.png")

# ===== fig10 GIS DoS spatiotemporal choropleth =====
fig,ax=plt.subplots(figsize=(7.4,5.6))
norm=Normalize(0,mm.ev_den.max()); cmap=plt.cm.OrRd
for _,r in mm.iterrows():
    g=r.g
    for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
        xs,ys=p.exterior.xy; ax.fill(xs,ys,facecolor=cmap(norm(r.ev_den)),edgecolor="#cfcfca",lw=.4,zorder=1)
outline(ax,bound,color=MUT,lw=1.0,zorder=2)
ax.scatter(sites.x,sites.y,s=8+sites.ev_den*2.2,facecolor=OI["blue"],edgecolor="white",lw=.4,zorder=4)
nomap(ax); ax.set_title("DoS 时空暴露：傍晚(18–21时)后台中断的被拒会话（按市镇）")
sm=ScalarMappable(norm=norm,cmap=cmap); sm.set_array([])
cb=fig.colorbar(sm,ax=ax,fraction=.035,pad=.02); cb.set_label("被拒会话数/日（平均）",fontsize=8)
ax.text(.01,.01,"点大小∝该站傍晚被拒会话；时间维取自真实逐时会话",transform=ax.transAxes,fontsize=7,color=MUT)
save(fig,"fig10_gis_dos.png")
print("[CHECK] muni max evening denied=%.1f"%mm.ev_den.max())

# ===== fig11 GIS attack-defense timeline (4 panels) =====
fig,axs=plt.subplots(1,4,figsize=(13.2,3.9))
amb=sites.sort_values("rank_sess").reset_index(drop=True)  # entry at busiest
order=amb.index.values
n=len(amb)
# states per panel: 0 normal,1 compromised,2 detected(ring),3 isolated/recovered
scen=[
 ("t0 = 0：单站被攻破（入口）",np.where(order< 1,1,0)),
 ("t1 ≈ 5 min：指令扇出至约 30 站",np.where(order<30,1,0)),
 ("t2：物理一致性检测触发（全部告警）",np.full(n,2)),
 ("t3：按运营商隔离→本地充电恢复",np.where(order<5,1,3)),
]
cmap_state={0:"#c7c7c4",1:OI["verm"],2:OI["orange"],3:OI["green"]}
for ax,(title,st) in zip(axs,scen):
    basemap(ax,fill="#f4f4f2")
    for s in (0,3,2,1):
        sel=amb[st==s]
        if s==2:
            ax.scatter(sel.x,sel.y,s=40,facecolor="none",edgecolor=OI["orange"],lw=1.3,zorder=5)
        else:
            ax.scatter(sel.x,sel.y,s=26,c=cmap_state[s],edgecolor="white",lw=.4,zorder=4)
    nomap(ax); ax.set_title(title,fontsize=9)
leg=[Patch(facecolor="#c7c7c4",label="正常"),Patch(facecolor=OI["verm"],label="被控"),
     Line2D([0],[0],marker='o',color='w',markerfacecolor='none',markeredgecolor=OI["orange"],ms=9,label="已告警"),
     Patch(facecolor=OI["green"],label="已隔离/恢复")]
fig.legend(handles=leg,loc="lower center",ncol=4,fontsize=8.5,frameon=False,bbox_to_anchor=(.5,-.03))
fig.suptitle("GIS 攻防时间线回放（场景示意，AMB/Iberdrola 后台；地理为真实站点）",y=1.03,fontsize=11,fontweight="bold")
save(fig,"fig11_gis_timeline.png")

# ===== fig12 GIS functional zone x DC x attack value =====
fig,ax=plt.subplots(figsize=(7.4,5.6))
zones=sorted(h3["zone_zh"].dropna().unique())
zcol={z:c for z,c in zip(zones,[ "#dfe7ef","#e9e4f0","#e7efe4","#f0ebe0","#efe2e2","#e4eef0","#eeeeee"])}
for _,r in h3.iterrows():
    g=r.g
    for p in (g.geoms if g.geom_type=="MultiPolygon" else [g]):
        xs,ys=p.exterior.xy; ax.fill(xs,ys,facecolor=zcol.get(r.zone_zh,"#eee"),edgecolor="white",lw=.2,zorder=1)
outline(ax,bound,color=MUT,lw=1.0,zorder=2)
# registry DC points sized by attack value (max_dc_kw proxy via has_dc100)
dc=reg[reg.has_dc==1]
ax.scatter(dc.x,dc.y,s=np.where(dc.has_dc100==1,40,16),c=np.where(dc.has_dc100==1,OI["verm"],OI["orange"]),
           lw=0,alpha=.85,zorder=4)
nomap(ax); ax.set_title("功能分区 × 直流部署 × 攻击价值")
leg=[Patch(facecolor=zcol[z],label=z) for z in zones]+[
     Line2D([0],[0],marker='o',color='w',markerfacecolor=OI["verm"],ms=9,label='>100 kW 直流（高攻击价值）'),
     Line2D([0],[0],marker='o',color='w',markerfacecolor=OI["orange"],ms=7,label='40–100 kW 直流')]
ax.legend(handles=leg,loc="lower left",fontsize=6.8,frameon=False,ncol=1)
save(fig,"fig12_gis_zones.png")
print("[FIG] all GIS done")
