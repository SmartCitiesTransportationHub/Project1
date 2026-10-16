"""Plain-language logic framework diagram (figLOGIC) for non-experts — light & colourful."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":180})
FIGS="/home/user/Project1/figs"

fig=plt.figure(figsize=(14.2,8.2),facecolor="white")
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")

ax.text(50,96.5,"这项研究在讲什么？——给非专业读者的逻辑框架",ha="center",va="top",
        fontsize=19,fontweight="bold",color="#15293d")
ax.text(50,91.8,"巴塞罗那大都会区 · 电动汽车充电网络的「网络层」攻防仿真（电网只作参照，攻击全程仅在仿真中进行）",
        ha="center",va="top",fontsize=10.5,color="#5d6b7a")

# ---- 4 stage cards ----
cards=[
 dict(x=2.0, head="①  问题", hc="#e8701a", bc="#fdecd9", ec="#f3b270",
      title="城市充电怎么会被攻击？",
      body=["一座城市的充电桩分属","几十家运营商。每家用一个","「后台(CSMS)」通过网络","远程控制自己的桩——调功","率、远程启停。","","攻破一个后台，就能同时","操纵这家公司的所有桩。"]),
 dict(x=26.0, head="②  关键洞察", hc="#1f78c4", bc="#e2eefb", ec="#8bbce8",
      title="城市不是「一张网」",
      body=["全城是 37+ 个互相独立的","后台拼成的——这叫","「控制平面碎片化」。","","攻破一家后台，横向只能","波及这一家的机队，到不","了别家：这天然限制了一","次入侵的「爆炸半径」。"]),
 dict(x=50.0, head="③  怎么研究", hc="#7b3ff2", bc="#eee6fd", ec="#c0a6f4",
      title="一家标定，全城推演",
      body=["只有 AMB 一家有真实充电","记录。用它精确测出","「攻破→检测→隔离」全过","程，再按每家的规模推广","到全城 621 个地点、39 个","后台。","","全程只在隔离仿真里完成，","不接触任何真实系统。"]),
 dict(x=74.0, head="④  主要发现", hc="#1f9d6b", bc="#e0f3ea", ec="#92d6b6",
      title="实测结果",
      body=["• 攻破最大一家 = 全城","  17% 的充电功率","• 想控制全城，需同时攻破","  很多家后台（很难）","• 一旦检测到异常就「隔","  离」，1 分钟内把损失","  压到 <1%","• 对电网仅占峰值 0.16%，","  远不构成威胁"]),
]
CW=22.0
for i,c in enumerate(cards):
    x=c["x"]; y0=28; y1=86
    # card body
    ax.add_patch(FancyBboxPatch((x,y0),CW,y1-y0,boxstyle="round,pad=0.4,rounding_size=1.6",
                 fc=c["bc"],ec=c["ec"],lw=1.6,zorder=2))
    # header strip
    ax.add_patch(FancyBboxPatch((x,y1-7.5),CW,7.5,boxstyle="round,pad=0.4,rounding_size=1.6",
                 fc=c["hc"],ec="none",zorder=3))
    ax.text(x+CW/2,y1-3.7,c["head"],ha="center",va="center",fontsize=13.5,fontweight="bold",color="white",zorder=4)
    ax.text(x+CW/2,y1-11.2,c["title"],ha="center",va="center",fontsize=11.5,fontweight="bold",color="#1b2f42",zorder=4)
    yy=y1-16.5
    for line in c["body"]:
        ax.text(x+1.6,yy,line,ha="left",va="top",fontsize=9.6,color="#2b3b4c",zorder=4)
        yy-=4.35
    # arrow to next
    if i<len(cards)-1:
        ax.add_patch(FancyArrowPatch((x+CW+0.4,57),(x+CW+1.6,57),arrowstyle="-|>",mutation_scale=22,
                     lw=0,color=c["hc"],zorder=5))
        ax.annotate("",xy=(x+CW+1.9,57),xytext=(x+CW+0.1,57),
                    arrowprops=dict(arrowstyle="-|>",lw=2.4,color="#9aa7b5"),zorder=5)

# ---- conclusion banner ----
ax.add_patch(FancyBboxPatch((2.0,6.5),94.0,16.5,boxstyle="round,pad=0.5,rounding_size=2",
             fc="#0f3d57",ec="none",zorder=2))
ax.text(5,19.0,"一句话结论",ha="left",va="center",fontsize=13,fontweight="bold",color="#7fd4f0",zorder=3)
ax.text(5,12.3,"真正要防的是「网络层的后台控制通道」，而不是电网。",
        ha="left",va="center",fontsize=13.5,fontweight="bold",color="white",zorder=3)
ax.text(5,7.7,"城市的「碎片化」本身就是一道天然防线；再加上「检测 + 逐后台隔离」，一次攻击几乎打不出实际损失。",
        ha="left",va="center",fontsize=11.5,color="#d4e6f0",zorder=3)

# ---- tiny schematic (fragmented control plane) top-right of insight card could clutter; add mini legend bottom-left of banner right side
# small metaphor: attacker -> one backend -> its fleet; others grey
sx=78; sy=14.8
ax.scatter([sx],[sy+4],s=70,marker="s",c="#ff5a5a",zorder=4); ax.text(sx,sy+6.4,"黑客",ha="center",fontsize=8,color="#ffd9d9",zorder=4)
for dx,col,lab in [(-5,"#ff6b6b",None),(-2.5,"#ff6b6b",None),(0,"#ff6b6b","被控的一家")]:
    ax.plot([sx,sx+dx+6],[sy+4,sy-1],color="#ff8a8a",lw=.8,alpha=.6,zorder=3)
for dx in [1,3.5,6]:
    ax.scatter([sx+dx],[sy-1.5],s=34,c="#ff6b6b",zorder=4,edgecolors="#7a1f1f",lw=.4)
for dx in [10,12.5,15,10,12.5][:3]:
    ax.scatter([sx+dx],[sy-1.5],s=30,c="#9fb0c2",zorder=4,edgecolors="#5d6b7a",lw=.4)
ax.text(sx+3.5,sy-4.3,"仅波及这一家",ha="center",fontsize=7.6,color="#ffd9d9",zorder=4)
ax.text(sx+12.5,sy-4.3,"其他后台不受影响",ha="center",fontsize=7.6,color="#cfe0ec",zorder=4)

fig.savefig(os.path.join(FIGS,"figLOGIC_framework.png"),bbox_inches="tight",facecolor="white")
plt.close(fig)
print("[FIG] figLOGIC_framework.png")
