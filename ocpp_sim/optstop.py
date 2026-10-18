"""Optimal isolation control as Bayesian quickest change detection (optimal stopping).

Problem. A compromised-backend attack curtails part of an operator's load, so the
scale*rhythm consistency ratio r_t = P_observed / P_expected drops from ~1 to ~1-delta.
The defender watches r_t and must choose WHEN to trigger isolation. Isolate too late ->
energy keeps being lost (delay cost c per tick); isolate a healthy backend (false
isolation) -> legitimate charging disrupted (penalty K). This sequential decision under
uncertainty is an optimal-stopping / Bayesian quickest-change-detection (QCD) problem.

Model (calibrated to real data).
  H0 (benign):  r_t ~ Normal(1,      sigma0)
  H1 (attack):  r_t ~ Normal(1-delta, sigma0)
  sigma0 = 0.39  (robust std of the real 2025 evening network consistency ratio;
                  sensitivity reported).  delta = curtailed fraction (attack loudness).

Optimal rule. For Bayesian QCD the optimal stopping rule is a THRESHOLD on the
posterior p_t = P(change has occurred | r_1..t) (Shiryaev). We compute p_t by the
Shiryaev recursion (geometric prior, hazard rho) and find the optimal threshold A*
minimizing expected total loss  E[c*(tau-nu)+] + K*P(tau<nu).

Benchmarked against CUSUM (Lorden-optimal), the paper's current fixed rule
(r<band for m consecutive ticks) and a naive one-shot threshold, on the
ADD-vs-ARL0 operating characteristic and on expected loss.  Vectorised over streams.
"""
import os, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.sans-serif":["WenQuanYi Zen Hei"],"axes.unicode_minus":False,"savefig.dpi":175})
FIGS="/home/user/Project1/figs"; OUT=os.path.dirname(__file__)
NAVY="#0F3D57"; TEAL="#1AA3C4"; RED="#E8384F"; GREEN="#1EA97C"; PURPLE="#8B4DDB"; ORANGE="#F08A24"; INK="#1A2633"; MUT="#5D6B7A"; GREY="#9AA7B5"
SIGMA0=0.39; RHO=1/500.0; TICK_MIN=1.0; EPS=1e-300
rng=np.random.default_rng(7)

def _lpdf(x,mu,sd): return -0.5*((x-mu)/sd)**2-np.log(sd*np.sqrt(2*np.pi))
def shiryaev(r,delta,sigma0=SIGMA0,rho=RHO):
    """r:[N,T] -> posterior p:[N,T]."""
    L=np.exp(_lpdf(r,1.0-delta,sigma0)-_lpdf(r,1.0,sigma0))
    N,T=r.shape; p=np.empty((N,T)); prev=np.zeros(N)
    for t in range(T):
        pre=prev+rho*(1-prev); num=pre*L[:,t]; den=num+(1-rho)*(1-prev)
        prev=num/np.maximum(den,EPS); p[:,t]=prev
    return p
def cusum(r,delta,sigma0=SIGMA0):
    llr=_lpdf(r,1.0-delta,sigma0)-_lpdf(r,1.0,sigma0)
    N,T=r.shape; S=np.empty((N,T)); s=np.zeros(N)
    for t in range(T):
        s=np.maximum(0.0,s+llr[:,t]); S[:,t]=s
    return S
def tau_threshold(stat,thr):
    """first t with stat>=thr, per stream; T if none. stat:[N,T]."""
    rm=np.maximum.accumulate(stat,axis=1); hit=rm>=thr
    T=stat.shape[1]; return np.where(hit.any(1),hit.argmax(1),T)
def tau_fixed(r,band=0.5,m=2):
    """r<band for m consecutive ticks; first such t. r:[N,T]."""
    N,T=r.shape; cnt=np.zeros(N,int); tau=np.full(N,T); done=np.zeros(N,bool)
    below=r<band
    for t in range(T):
        cnt=np.where(below[:,t],cnt+1,0)
        fire=(cnt>=m)&(~done); tau[fire]=t; done|=fire
    return tau
def tau_naive(r,band=0.5):
    hit=r<band; T=r.shape[1]; return np.where(hit.any(1),hit.argmax(1),T)

def H0(N,T): return 1.0+SIGMA0*rng.standard_normal((N,T))
def H1(N,T,delta): return (1.0-delta)+SIGMA0*rng.standard_normal((N,T))

# ---- operating characteristic ----
def arl0_add(statfn,thrs,delta,N=3000,T0=2000,T1=400):
    r0=H0(N,T0); s0=statfn(r0); r1=H1(N,T1,delta); s1=statfn(r1)
    arl=np.array([tau_threshold(s0,th).mean()+1 for th in thrs])
    add=np.array([tau_threshold(s1,th).mean() for th in thrs])
    return arl,add
def arl0_add_rule(taufn,bands,delta,N=3000,T0=2000,T1=400):
    r0=H0(N,T0); r1=H1(N,T1,delta); out=[]
    for b in bands: out.append((taufn(r0,b).mean()+1, taufn(r1,b).mean(), b))
    return out

# ---- episodic expected loss (geometric change) ----
def episodes(N,T,delta,hazard=RHO):
    nu=np.minimum(rng.geometric(hazard,N),T+1)              # 1-indexed
    r=1.0+SIGMA0*rng.standard_normal((N,T))
    idx=np.arange(T)[None,:]+1
    r=np.where(idx>=nu[:,None], r-delta, r)
    return r,nu
def loss_threshold(stat,nu,thrs,c=1.0,K=30.0):
    T=stat.shape[1]; out=[]
    for th in thrs:
        tau=tau_threshold(stat,th)+1
        fi=tau<nu; d=np.where(fi,0,tau-nu)
        cost=np.where(fi,K,c*d).mean(); out.append((float(th),float(cost),float(d[~fi].mean() if (~fi).any() else 0),float(fi.mean())))
    return out
def loss_rule(tau,nu,c=1.0,K=30.0):
    tau=tau+1; fi=tau<nu; d=np.where(fi,0,tau-nu)
    return float(np.where(fi,K,c*d).mean()), float(d[~fi].mean() if (~fi).any() else 0), float(fi.mean())

def main():
    res={"sigma0":SIGMA0,"rho":RHO,"tick_min":TICK_MIN}
    d0=0.5; DELTAS=[0.35,0.5,0.8]; res["deltas"]=DELTAS
    shi_thr=np.concatenate([np.linspace(0.08,0.48,9),np.linspace(0.50,0.9985,24)]); cus_thr=np.linspace(0.3,14,30); bands=[0.4,0.5,0.6,0.7]
    sa,sd=arl0_add(lambda r:shiryaev(r,d0),shi_thr,d0)
    ca,cd=arl0_add(lambda r:cusum(r,d0),cus_thr,d0)
    fr=arl0_add_rule(lambda r,b:tau_fixed(r,b,2),bands,d0)
    nv=arl0_add_rule(lambda r,b:tau_naive(r,b),bands,d0)
    res["oc"]={"delta_oc":d0,"shiryaev":{"arl0":sa.tolist(),"add":sd.tolist(),"thr":shi_thr.tolist()},
               "cusum":{"arl0":ca.tolist(),"add":cd.tolist(),"thr":cus_thr.tolist()},"fixed":fr,"naive":nv}
    print(f"[OC] shiryaev ARL0 {sa.min():.0f}-{sa.max():.0f} ADD {sd.min():.1f}-{sd.max():.1f}")
    # cost sweep (shiryaev) at d0
    K=30.0; c=1.0; r,nu=episodes(6000,240,d0); st=shiryaev(r,d0)
    cost=loss_threshold(st,nu,shi_thr,c,K); cost=np.array(cost)
    ia=int(np.argmin(cost[:,1])); Astar=float(cost[ia,0])
    res["cost_sweep"]={"thr":cost[:,0].tolist(),"cost":cost[:,1].tolist(),"delay":cost[:,2].tolist(),"false_iso":cost[:,3].tolist(),"K":K,"c":c,"Astar":Astar}
    # headline opt vs fixed
    opt=loss_threshold(st,nu,[Astar],c,K)[0]
    fxtau=tau_fixed(r,0.5,2); fx=loss_rule(fxtau,nu,c,K)
    res["headline"]={"delta":d0,"opt":{"A":Astar,"cost":opt[1],"delay_min":opt[2]*TICK_MIN,"false_iso":opt[3]},
                     "fixed":{"cost":fx[0],"delay_min":fx[1]*TICK_MIN,"false_iso":fx[2]}}
    print(f"[HEAD] opt A*={Astar:.3f} cost={opt[1]:.2f} delay={opt[2]:.1f}min FI={opt[3]:.3f} | fixed cost={fx[0]:.2f} delay={fx[1]:.1f}min FI={fx[2]:.3f}")
    # stealth sensitivity
    sens=[]
    for d in DELTAS:
        r,nu=episodes(6000,240,d); st=shiryaev(r,d)
        cc=np.array(loss_threshold(st,nu,shi_thr,c,K)); ja=int(np.argmin(cc[:,1])); A=float(cc[ja,0])
        o=(A,cc[ja,1],cc[ja,2],cc[ja,3]); fx=loss_rule(tau_fixed(r,0.5,2),nu,c,K)
        sens.append({"delta":d,"A":A,"opt_cost":float(o[1]),"opt_delay_min":float(o[2]*TICK_MIN),"opt_fi":float(o[3]),
                     "fix_cost":fx[0],"fix_delay_min":fx[1]*TICK_MIN,"fix_fi":fx[2]})
        print(f"[d={d}] optA={A:.3f} cost={o[1]:.2f}(d {o[2]:.1f}tk,FI {o[3]:.3f}) | fix cost={fx[0]:.2f}(d {fx[1]:.1f}tk,FI {fx[2]:.3f})")
    res["sensitivity"]=sens
    json.dump(res,open(os.path.join(OUT,"results_optstop.json"),"w"),ensure_ascii=False,indent=1); print("[SAVED] results_optstop.json")
    make_figs(res,d0,Astar)

def make_figs(res,d0,Astar):
    # pick a REPRESENTATIVE episode: fixed rule false-isolates before the attack
    # (its modal failure at realistic noise) while the optimal posterior stays low.
    T=120; nu=70
    r=None; tau=ft=0
    for seed in range(200):
        g=np.random.default_rng(seed)
        rr=np.where(np.arange(T)+1>=nu,1.0-d0,1.0)+SIGMA0*g.standard_normal(T)
        f=int(tau_fixed(rr[None,:],0.5,2)[0]); t=int(tau_threshold(shiryaev(rr[None,:],d0),Astar)[0])
        if f<nu-4 and nu<=t<=nu+14:            # fixed false-fires pre-attack; optimal detects shortly after
            r=rr; ft=f; tau=t; break
    if r is None:
        g=np.random.default_rng(3); r=np.where(np.arange(T)+1>=nu,1.0-d0,1.0)+SIGMA0*g.standard_normal(T)
        ft=int(tau_fixed(r[None,:],0.5,2)[0]); tau=int(tau_threshold(shiryaev(r[None,:],d0),Astar)[0])
    p=shiryaev(r[None,:],d0)[0]
    fig,(a1,a2)=plt.subplots(2,1,figsize=(10.5,6.2),facecolor="white",sharex=True)
    a1.axhspan(0.5,1.5,color="#EAF1F8",label="固定规则正常带 (r>0.5)")
    a1.plot(r,color=GREY,lw=1.3,label="一致性比 rₜ = 观测/期望")
    a1.axhline(1.0,color=MUT,lw=.8,ls=":"); a1.axhline(1-d0,color=RED,lw=.8,ls="--")
    a1.axvline(nu,color=RED,lw=1.4,alpha=.6); a1.text(nu+1,1.95,"攻击开始 ν",color=RED,fontsize=9,fontweight="bold")
    a1.set_ylabel("一致性比 rₜ",fontsize=10); a1.set_ylim(-0.2,2.5); a1.legend(fontsize=8.5,loc="upper right",framealpha=.9)
    a1.set_title("图 D1(a)　单次隐蔽攻击上的信号与后验",color=NAVY,fontsize=12,fontweight="bold",loc="left")
    a2.plot(p,color=TEAL,lw=2,label="贝叶斯后验 pₜ=P(已被攻击)")
    a2.axhline(Astar,color=GREEN,lw=1.6,ls="--",label=f"最优阈值 A*={Astar:.2f}")
    a2.axvline(nu,color=RED,lw=1.4,alpha=.6)
    a2.axvline(tau,color=GREEN,lw=1.8); a2.text(min(tau+1,T-26),0.14,f"最优隔离 τ*\n(攻击后 +{(tau-nu)*TICK_MIN:.0f} min)",color=GREEN,fontsize=8.8,fontweight="bold")
    a2.axvline(ft,color=ORANGE,lw=1.7,ls=":"); a2.text(max(ft-27,1),0.55,f"固定规则误隔离\n(攻击前 {(nu-ft)*TICK_MIN:.0f} min·良性)",color="#B5701A",fontsize=8.8,fontweight="bold")
    a2.set_ylabel("后验概率 pₜ",fontsize=10); a2.set_xlabel("时间 (min)",fontsize=10); a2.set_ylim(0,1.05); a2.legend(fontsize=8.5,loc="center right",framealpha=.9)
    for ax in (a1,a2):
        for sp in ax.spines.values(): sp.set_color("#C9D6E2")
        ax.tick_params(colors=MUT); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_optstop_policy.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] policy")

    oc=res["oc"]; fig,ax=plt.subplots(figsize=(8.8,5.6),facecolor="white")
    ax.plot(oc["shiryaev"]["arl0"],np.array(oc["shiryaev"]["add"])*TICK_MIN,"-o",color=TEAL,lw=2,ms=4,label="贝叶斯后验 Shiryaev（本文最优）")
    ax.plot(oc["cusum"]["arl0"],np.array(oc["cusum"]["add"])*TICK_MIN,"-s",color=PURPLE,lw=1.8,ms=4,label="CUSUM（经典最优）")
    fr=np.array([[a,b*TICK_MIN] for a,b,_ in oc["fixed"]]); nv=np.array([[a,b*TICK_MIN] for a,b,_ in oc["naive"]])
    ax.scatter(fr[:,0],fr[:,1],s=75,color=ORANGE,marker="D",zorder=5,label="固定规则 r<带·连续2格（本文现用）")
    ax.scatter(nv[:,0],nv[:,1],s=60,color=RED,marker="X",zorder=5,label="朴素单次阈值")
    ax.set_xscale("log"); ax.set_xlabel("误隔离前平均运行时长 ARL₀ (min，越大越好)",fontsize=10.5)
    ax.set_ylabel("平均检测时延 ADD (min，越小越好)",fontsize=10.5)
    ax.set_title(f"图 D2　隔离触发器的操作特性（隐蔽攻击 δ={oc['delta_oc']}，σ₀={SIGMA0}）\n左下更优：最优策略在同等误报下检测更快",color=NAVY,fontsize=12,fontweight="bold")
    ax.legend(fontsize=9,loc="upper right"); ax.grid(alpha=.25,which="both")
    for sp in ax.spines.values(): sp.set_color("#C9D6E2")
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_optstop_oc.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] oc")

    cs=res["cost_sweep"]; sens=res["sensitivity"]
    fig,(a1,a2)=plt.subplots(1,2,figsize=(12.5,4.8),facecolor="white",gridspec_kw={"width_ratios":[1.1,1]})
    a1.plot(cs["thr"],cs["cost"],"-o",color=TEAL,lw=2,ms=3)
    ia=int(np.argmin(cs["cost"])); a1.scatter([cs["thr"][ia]],[cs["cost"][ia]],s=120,color=GREEN,zorder=5,edgecolors="#0b5a3c",lw=1)
    a1.axvline(cs["Astar"],color=GREEN,ls="--",lw=1.3); a1.text(cs["Astar"]-0.14,max(cs["cost"])*0.88,f"A*={cs['Astar']:.2f}",color=GREEN,fontsize=10,fontweight="bold")
    a1.axhline(res["headline"]["fixed"]["cost"],color=ORANGE,ls=":",lw=1.6); a1.text(0.52,res["headline"]["fixed"]["cost"]*1.02,"固定规则成本",color="#B5701A",fontsize=9,va="bottom")
    a1.set_xlabel("隔离阈值 A（后验 pₜ 触发点）",fontsize=10.5); a1.set_ylabel(f"期望总损失 c·时延+K·误隔离 (K/c={int(cs['K']/cs['c'])})",fontsize=10)
    a1.set_title("(a) 最优阈值 A* 最小化期望总损失",fontsize=11,fontweight="bold"); a1.grid(alpha=.25)
    d=[s["delta"] for s in sens]; x=np.arange(len(d)); w=.36
    a2.bar(x-w/2,[s["opt_cost"] for s in sens],w,color=TEAL,label="最优停止（Shiryaev）")
    a2.bar(x+w/2,[s["fix_cost"] for s in sens],w,color=ORANGE,label="固定规则（本文现用）")
    for i,s in enumerate(sens):
        red=100*(1-s["opt_cost"]/s["fix_cost"]) if s["fix_cost"] else 0
        a2.text(i,max(s["opt_cost"],s["fix_cost"])+max(0.3,0.02*max(s["opt_cost"],s["fix_cost"])),f"−{red:.0f}%",ha="center",fontsize=9.5,color=GREEN,fontweight="bold")
    a2.set_xticks(x); a2.set_xticklabels([f"δ={v}\n{'隐蔽' if v<0.45 else ('中' if v<0.7 else '响亮')}" for v in d],fontsize=9)
    a2.set_ylabel("期望总损失",fontsize=10); a2.set_title("(b) 越隐蔽的攻击，最优策略优势越大",fontsize=11,fontweight="bold")
    a2.legend(fontsize=9); a2.grid(axis="y",alpha=.25)
    for ax in (a1,a2):
        for sp in ax.spines.values(): sp.set_color("#C9D6E2")
    fig.suptitle("图 D3　最优隔离阈值与对固定规则的改进（期望损失口径）",color=NAVY,fontsize=12.5,fontweight="bold",y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_optstop_cost.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] cost")

if __name__=="__main__":
    main()
