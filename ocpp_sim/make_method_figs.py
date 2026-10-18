"""Method/protocol diagrams for the explainer deck (light, colorful):
  fig_ocpp_seq.png  — real OCPP message sequence (normal session + attack mapping)
  fig_sim_arch.png  — simulation architecture (621 clients -> 39 CSMS backends + virtual clock)
"""
import os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":180})
FIGS="/home/user/Project1/figs"
NAVY="#0F3D57"; TEAL="#1AA3C4"; RED="#E8384F"; GREEN="#1EA97C"; PURPLE="#8B4DDB"; ORANGE="#F08A24"; INK="#1A2633"; MUT="#5D6B7A"
CARD="#F4F7FB"; CARDE="#C9D6E2"

# ------------------------------------------------------------ OCPP sequence
def ocpp_seq():
    fig,ax=plt.subplots(figsize=(12.6,7.0),facecolor="white"); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")
    xL,xR=22,78
    # actor headers
    for x,lab,col in [(xL,"充电桩 (EVSE)\nPython ocpp 客户端",TEAL),(xR,"运营商后台 (CSMS)\nWebSocket 服务端",PURPLE)]:
        ax.add_patch(FancyBboxPatch((x-11,92),22,6,boxstyle="round,pad=0.3,rounding_size=1.2",fc=col,ec="none"))
        ax.text(x,95,lab,ha="center",va="center",fontsize=11,fontweight="bold",color="white")
    # lifelines
    ax.plot([xL,xL],[7,92],color=CARDE,lw=1.6,zorder=1); ax.plot([xR,xR],[7,92],color=CARDE,lw=1.6,zorder=1)
    ax.text(50,88.5,"传输：OCPP over WebSocket（1.6 下 TLS 可选）",ha="center",fontsize=10,color=MUT,style="italic")
    def msg(y,text,tag,direction,col):
        a,b=(xL,xR) if direction=="R" else (xR,xL)
        if tag: ax.text((a+b)/2,y+4.0,tag,ha="center",va="bottom",fontsize=8.8,color=col,fontweight="bold")
        ax.annotate("",xy=(b,y),xytext=(a,y),arrowprops=dict(arrowstyle="-|>",color=col,lw=2))
        ax.text((a+b)/2,y+0.9,text,ha="center",va="bottom",fontsize=10,color=INK,fontweight="bold")
    # normal phase
    ax.add_patch(FancyBboxPatch((9,48.5),82,36,boxstyle="round,pad=0.4,rounding_size=1.2",fc="#F2FAFC",ec="#BFE4EE",lw=1.2,zorder=0))
    ax.text(11,82.3,"① 正常充电：一次会话的真实 OCPP 报文序列（桩→后台上报）",fontsize=11,fontweight="bold",color=TEAL)
    msg(77,"BootNotification   上线注册",None,'R',TEAL)
    msg(71,"Heartbeat   心跳（周期）",None,'R',TEAL)
    msg(65,"Authorize(idTag)   RFID/App 鉴权",None,'R',TEAL)
    msg(59,"StartTransaction   开始充电·上报起始电表",None,'R',TEAL)
    msg(53,"MeterValues   周期上报功率/电量  ·  StopTransaction   结束",None,'R',TEAL)
    # attack phase
    ax.add_patch(FancyBboxPatch((9,6.5),82,38,boxstyle="round,pad=0.4,rounding_size=1.2",fc="#FDEEEF",ec="#F3B9BF",lw=1.2,zorder=0))
    ax.text(11,42.3,"② 攻击：复用同一批 OCPP 报文，只改变来源 / 内容 / 节律",fontsize=11,fontweight="bold",color=RED)
    msg(33,"SetChargingProfile(limit = 0 W)","A3 后台沦陷 · 限功率",'L',RED)
    msg(24,"RemoteStopTransaction","A3 后台沦陷 · 批量停充",'L',RED)
    # MitM on the uplink
    ax.text(50,18.5,"A1 链路中间人（偷电 / 计费偏差）",ha="center",va="bottom",fontsize=8.8,color=ORANGE,fontweight="bold")
    ax.annotate("",xy=(xR,15),xytext=(xL,15),arrowprops=dict(arrowstyle="-|>",color=ORANGE,lw=2))
    ax.scatter([50],[15],s=150,marker="X",color=ORANGE,zorder=5,edgecolors="white",lw=1)
    ax.text(50,15.9,"MeterValues  ✎ 篡改 × 2.2",ha="center",va="bottom",fontsize=10,fontweight="bold",color=INK)
    ax.text(50,9.3,"A4 后台 DoS：Heartbeat / 连接洪泛 → 后台离线、整支机队失联",ha="center",fontsize=9.3,color=RED,fontweight="bold")
    fig.suptitle("真实 OCPP 报文序列：正常充电 vs 四类攻击如何映射到协议",fontsize=14.5,fontweight="bold",color=NAVY,y=1.0)
    fig.savefig(os.path.join(FIGS,"fig_ocpp_seq.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig_ocpp_seq]")

# ------------------------------------------------------------ simulation architecture
def sim_arch():
    fig,ax=plt.subplots(figsize=(12.8,6.8),facecolor="white"); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")
    # attacker
    ax.add_patch(FancyBboxPatch((3,60),15,12,boxstyle="round,pad=0.3,rounding_size=1.4",fc=RED,ec="none"))
    ax.text(10.5,66,"攻击者",ha="center",va="center",fontsize=13,fontweight="bold",color="white")
    ax.text(10.5,55.5,"攻破某个\n(或多个)后台",ha="center",va="center",fontsize=9,color=RED)
    # CSMS backends (center)
    opcol=[RED,ORANGE,PURPLE,GREEN,TEAL]; names=["Endesa","Iberdrola","AMB","BSM-Endolla","Repsol"]
    cy=[82,68,54,40,26]
    for i,(c,nm,y) in enumerate(zip(opcol,names,cy)):
        comp=(i==0)
        ax.add_patch(FancyBboxPatch((33,y-4.5),20,9,boxstyle="round,pad=0.25,rounding_size=1.0",fc=("#FDECEC" if comp else CARD),ec=(RED if comp else CARDE),lw=(2 if comp else 1.2)))
        ax.add_patch(Circle((37,y),1.9,color=c));
        ax.text(41.5,y+0.8,f"后台 CSMS · {nm}",ha="left",va="center",fontsize=9.5,fontweight="bold",color=INK)
        ax.text(41.5,y-1.9,"检测+隔离",ha="left",va="center",fontsize=7.5,color=GREEN)
        if comp:
            ax.annotate("",xy=(33,y),xytext=(18,66),arrowprops=dict(arrowstyle="-|>",color=RED,lw=2.2))
    ax.text(43,20,"…… 共 39 个相互独立的后台（控制平面碎片化）",ha="center",fontsize=9.5,color=MUT,style="italic")
    # charge points (right) for a few backends
    rng=np.random.RandomState(3)
    for i,(c,y) in enumerate(zip(opcol,cy)):
        n=[9,7,7,8,5][i]
        for j in range(n):
            px=66+ (j%5)*5.6 + rng.uniform(-1,1); py=y + (1 if j<5 else -1)*3.0 + rng.uniform(-0.6,0.6)
            ax.plot([53,px],[y, py],color=c,lw=0.5,alpha=0.5,zorder=1)
            ax.scatter([px],[py],s=42,color=("#f06a78" if i==0 else c),edgecolors="white",lw=.5,zorder=3)
    ax.add_patch(FancyBboxPatch((63,86),34,7,boxstyle="round,pad=0.3,rounding_size=1.0",fc="#EEF6FB",ec="#BFE0EE",lw=1))
    ax.text(80,89.5,"621 个真实 OCPP 客户端（每个=一个充电点）",ha="center",va="center",fontsize=10,fontweight="bold",color=NAVY)
    # bottom bands
    ax.add_patch(FancyBboxPatch((3,8),45,10,boxstyle="round,pad=0.3,rounding_size=1.0",fc="#EAF6F0",ec="#A8D9C2",lw=1))
    ax.text(25.5,13,"离散虚拟时钟：1 分钟/步，与墙钟解耦\n（消息处理延迟不污染仿真时间）",ha="center",va="center",fontsize=9.5,color="#1C7A57",fontweight="bold")
    ax.add_patch(FancyBboxPatch((52,8),45,10,boxstyle="round,pad=0.3,rounding_size=1.0",fc=CARD,ec=CARDE,lw=1))
    ax.text(74.5,13,"技术栈：Python ocpp 库 · websockets\n真实 OCPP 1.6-JSON 报文经真实 WebSocket 交换",ha="center",va="center",fontsize=9.5,color=INK,fontweight="bold")
    fig.suptitle("仿真建模：621 个真实 OCPP 客户端 → 39 个独立运营商后台",fontsize=14.5,fontweight="bold",color=NAVY,y=0.99)
    fig.savefig(os.path.join(FIGS,"fig_sim_arch.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig_sim_arch]")

if __name__=="__main__":
    ocpp_seq(); sim_arch(); print("done")
