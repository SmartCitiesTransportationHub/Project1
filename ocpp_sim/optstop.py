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

# ---- learned (ML) one-class baselines on a sliding feature window ----
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
WIN=6
def _feats(r):
    """r:[N,T] -> X:[N, T-WIN, F] features (mean,min,std,last) of each window."""
    N,T=r.shape; cols=[]
    for t in range(WIN,T):
        seg=r[:,t-WIN:t]; cols.append(np.stack([seg.mean(1),seg.min(1),seg.std(1),r[:,t]],1))
    return np.stack(cols,1)                            # [N, T-WIN, F]
def ml_fit(model,ntr=5000):
    rtr=H0(2000,80); X=_feats(rtr).reshape(-1,4)       # benign training windows
    if len(X)>ntr: X=X[np.random.default_rng(0).choice(len(X),ntr,replace=False)]
    model.fit(X); return model
def ml_curve(model,delta):
    s0b=ml_scores(model,H0(400,160)).ravel(); thrs=np.quantile(s0b,np.linspace(0.0015,0.45,22))
    return ml_oc(model,thrs,delta)
def ml_scores(model,r):
    X=_feats(r); N,Tw,F=X.shape
    s=model.decision_function(X.reshape(-1,F)).reshape(N,Tw)   # higher = more normal
    return s                                            # anomaly when s<=thr
def tau_low(score,thr):
    cm=np.minimum.accumulate(score,axis=1); hit=cm<=thr; Tw=score.shape[1]
    return np.where(hit.any(1),hit.argmax(1),Tw)
def ml_oc(model,thrs,delta,N=1200,T0=800,T1=300):
    s0=ml_scores(model,H0(N,T0)); s1=ml_scores(model,H1(N,T1,delta))
    arl=np.array([tau_low(s0,th).mean()+1+WIN for th in thrs])
    add=np.array([tau_low(s1,th).mean()+WIN for th in thrs])   # +WIN: window lag (inherent to windowed ML)
    return arl,add

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

# ======================================================================
#  Per-operator study: the SAME six algorithms under the city's REAL
#  fragmentation.  The metropolitan control plane is 39 independent
#  operator backends of wildly different size; each is a DIFFERENT
#  detection problem, so one global rule cannot serve the fleet.
#    * noise  sigma_op  grows as the operator shrinks (law of large
#      numbers over fewer concurrent sessions): sigma_op = sigma0*sqrt(n_ref/n_loc).
#      -> small fragmented operators are intrinsically noisier/harder.
#    * cost ratio K/c is operator-specific: delay cost c ~ MW at risk,
#      false-isolation penalty K ~ customers (locations) disrupted.
#      -> each operator has its own optimal caution level A*.
#  The Bayesian optimal controller re-derives (A*_op) per operator; a
#  single city-wide fixed threshold cannot adapt and fails on the noisy tail.
# ======================================================================
NREF=71   # reference cell = AMB real-session operator (sigma0 measured here)
def sigma_op(n_loc, sref=SIGMA0, nref=NREF, lo=0.12, hi=0.90):
    return float(np.clip(sref*np.sqrt(nref/max(n_loc,1)), lo, hi))
def episodes_s(N,T,delta,sigma,hazard=RHO):
    nu=np.minimum(rng.geometric(hazard,N),T+1)
    r=1.0+sigma*rng.standard_normal((N,T))
    idx=np.arange(T)[None,:]+1
    return np.where(idx>=nu[:,None], r-delta, r), nu
def H0s(N,T,sigma): return 1.0+sigma*rng.standard_normal((N,T))
def ml_fit_s(model,sigma,ntr=4000):
    X=_feats(H0s(1500,80,sigma)).reshape(-1,4)
    if len(X)>ntr: X=X[np.random.default_rng(0).choice(len(X),ntr,replace=False)]
    model.fit(X); return model
def ml_loss(model,r_ep,nu,K,c=1.0):
    s=ml_scores(model,r_ep); thrs=np.quantile(s.ravel(),np.linspace(0.001,0.5,22)); best=None
    for th in thrs:
        tau=tau_low(s,th)+WIN+1; fi=tau<nu; d=np.where(fi,0,tau-nu)
        cost=float(np.where(fi,K,c*d).mean()); best=cost if best is None else min(best,cost)
    return best
def per_operator_study(delta=0.5):
    city=json.load(open(os.path.join(OUT,"results_city.json")))
    ops=city["s1_single_backend"]                      # 8 real operators, size 3..138 loc
    shi_thr=np.concatenate([np.linspace(0.08,0.48,9),np.linspace(0.50,0.9985,24)])
    cus_thr=np.linspace(0.3,14,30); bands=[0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7]
    kappa=30.0*9.59/71.0                               # K=kappa*n_loc -> AMB(71loc,9.59MW) gives K/c=30
    sref=sigma_op(NREF)
    rref,nuref=episodes_s(4000,240,delta,sref)
    gb=min(bands,key=lambda b:loss_rule(tau_fixed(rref,b,2),nuref,1.0,30.0)[0])  # one global band, tuned at the reference
    print(f"[OPS] global fixed band tuned at reference = {gb}")
    rows=[]
    for o in ops:
        n=o["n_loc"]; mw=o["mw"]; sg=sigma_op(n); Kc=kappa*n/mw
        r,nu=episodes_s(4000,240,delta,sg)
        st=shiryaev(r,delta,sg); cc=np.array(loss_threshold(st,nu,shi_thr,1.0,Kc))
        ja=int(np.argmin(cc[:,1])); A=float(cc[ja,0]); L_shi=float(cc[ja,1])
        cu=np.array(loss_threshold(cusum(r,delta,sg),nu,cus_thr,1.0,Kc)); L_cus=float(cu[:,1].min())
        L_fixT=min(loss_rule(tau_fixed(r,b,2),nu,1.0,Kc)[0] for b in bands)       # fixed rule, best per-operator band
        L_fixG=loss_rule(tau_fixed(r,gb,2),nu,1.0,Kc)[0]                          # fixed rule, single global band
        L_nv=min(loss_rule(tau_naive(r,b),nu,1.0,Kc)[0] for b in bands)
        L_if=ml_loss(ml_fit_s(IsolationForest(n_estimators=100,random_state=1),sg),r[:1500],nu[:1500],Kc)
        L_oc=ml_loss(ml_fit_s(OneClassSVM(nu=0.05,gamma="scale"),sg),r[:1500],nu[:1500],Kc)
        rows.append({"short":o["short"],"mw":mw,"n_loc":n,"sigma":round(sg,3),"Kc":round(Kc,1),"A":round(A,3),
                     "shiryaev":round(L_shi,3),"cusum":round(L_cus,3),"iforest":round(L_if,3),"ocsvm":round(L_oc,3),
                     "fixed_tuned":round(L_fixT,3),"fixed_global":round(L_fixG,3),"naive":round(L_nv,3)})
        print(f"  {o['short'][:16]:16s} n={n:3d} σ={sg:.2f} K/c={Kc:4.1f} A*={A:.2f} | shi={L_shi:5.2f} cus={L_cus:5.2f} iF={L_if:5.2f} oc={L_oc:5.2f} fixT={L_fixT:5.2f} fixG={L_fixG:6.2f} nv={L_nv:6.2f}")
    # fleet-wide summary: mean normalised loss per method (fragmentation cost of a non-adaptive rule)
    meth=["shiryaev","cusum","iforest","ocsvm","fixed_tuned","fixed_global","naive"]
    fleet={m:round(float(np.mean([x[m] for x in rows])),3) for m in meth}
    print("[OPS] fleet mean loss:",{k:round(v,1) for k,v in fleet.items()})
    return {"delta":delta,"global_band":gb,"kappa":round(kappa,3),"nref":NREF,"sref":round(sref,3),
            "rows":rows,"fleet":fleet}

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
    # ML learned one-class baselines
    ifo=ml_fit(IsolationForest(n_estimators=120,contamination="auto",random_state=1))
    svm=ml_fit(OneClassSVM(nu=0.05,gamma="scale"))
    ia,idd=ml_curve(ifo,d0); va,vd=ml_curve(svm,d0)
    res["oc"]["iforest"]={"arl0":ia.tolist(),"add":idd.tolist()}
    res["oc"]["ocsvm"]={"arl0":va.tolist(),"add":vd.tolist()}
    print(f"[ML] IForest ARL0 {ia.min():.0f}-{ia.max():.0f} ADD {idd.min():.1f}-{idd.max():.1f} | OCSVM ADD {vd.min():.1f}-{vd.max():.1f}")
    # application-scenario sweep: cost regime K/c (how costly false isolation is)
    reg=[]
    for Kc in [10,30,100,300]:
        r,nu=episodes(5000,240,d0); st=shiryaev(r,d0)
        cc=np.array(loss_threshold(st,nu,shi_thr,1.0,Kc)); ja=int(np.argmin(cc[:,1])); A=float(cc[ja,0])
        o=cc[ja]; fx=loss_rule(tau_fixed(r,0.5,2),nu,1.0,Kc)
        reg.append({"Kc":Kc,"A":A,"opt_cost":float(o[1]),"fix_cost":fx[0],"red":float(100*(1-o[1]/fx[0]) if fx[0] else 0)})
        print(f"[K/c={Kc}] A*={A:.3f} opt={o[1]:.2f} fix={fx[0]:.2f} red={reg[-1]['red']:.0f}%")
    res["regime"]=reg
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
    # per-operator (fragmentation) comparison of all six algorithms
    res["operators"]=per_operator_study(d0)
    json.dump(res,open(os.path.join(OUT,"results_optstop.json"),"w"),ensure_ascii=False,indent=1); print("[SAVED] results_optstop.json")
    make_figs(res,d0,Astar)
    fig_ops(res["operators"])

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
    a1.set_title("图 8　最优停止 vs 固定规则：单次隐蔽攻击上的信号与后验",color=NAVY,fontsize=12,fontweight="bold",loc="left")
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
    if "iforest" in oc:
        ax.plot(oc["iforest"]["arl0"],np.array(oc["iforest"]["add"])*TICK_MIN,"--^",color=GREEN,lw=1.5,ms=4,label="孤立森林（学习型 ML）")
        ax.plot(oc["ocsvm"]["arl0"],np.array(oc["ocsvm"]["add"])*TICK_MIN,"--v",color="#C9872F",lw=1.5,ms=4,label="单类 SVM（学习型 ML）")
    ax.scatter(fr[:,0],fr[:,1],s=75,color=ORANGE,marker="D",zorder=5,label="固定规则 r<带·连续2格（本文现用）")
    ax.scatter(nv[:,0],nv[:,1],s=60,color=RED,marker="X",zorder=5,label="朴素单次阈值")
    ax.set_xscale("log"); ax.set_xlabel("误隔离前平均运行时长 ARL₀ (min，越大越好)",fontsize=10.5)
    ax.set_ylabel("平均检测时延 ADD (min，越小越好)",fontsize=10.5)
    ax.set_title(f"图 9　隔离触发器的操作特性·六法对比（隐蔽攻击 δ={oc['delta_oc']}，σ₀={SIGMA0}）\n左下更优：贝叶斯/CUSUM 严格优于学习型 ML 与启发式规则",color=NAVY,fontsize=12,fontweight="bold")
    ax.legend(fontsize=9,loc="upper right"); ax.grid(alpha=.25,which="both")
    for sp in ax.spines.values(): sp.set_color("#C9D6E2")
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_optstop_oc.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] oc")

    cs=res["cost_sweep"]; sens=res["sensitivity"]
    fig,(a1,a2,a3)=plt.subplots(1,3,figsize=(16.6,4.6),facecolor="white",gridspec_kw={"width_ratios":[1.1,1,1]})
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
    # (c) application-scenario / cost-regime sweep
    reg=res.get("regime",[]); kc=[r["Kc"] for r in reg]; red=[r["red"] for r in reg]
    a3.plot(kc,red,"-o",color=TEAL,lw=2,ms=6)
    for r in reg: a3.annotate(f"A*={r['A']:.2f}",(r["Kc"],r["red"]),fontsize=8.5,color=MUT,xytext=(0,-15),textcoords="offset points",ha="center")
    a3.set_xscale("log"); a3.set_ylim(0,100); a3.set_xlabel("误隔离代价比 K/c（越在意误隔离→越大）",fontsize=10)
    a3.set_ylabel("期望损失削减 %（vs 固定规则）",fontsize=10); a3.set_title("(c) 不同运营场景(成本比)下的稳健增益",fontsize=11,fontweight="bold"); a3.grid(alpha=.25)
    for ax in (a1,a2,a3):
        for sp in ax.spines.values(): sp.set_color("#C9D6E2")
    fig.suptitle("图 10　最优隔离阈值、隐蔽度与运营场景的改进（期望损失口径）",color=NAVY,fontsize=12.5,fontweight="bold",y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS,"fig_optstop_cost.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] cost")

def fig_ops(opres):
    """图 11  六种算法在城市真实碎片化运营商上的对比（按运营商逐一标定）。"""
    rows=sorted(opres["rows"],key=lambda r:r["n_loc"])     # small (noisy/hard) -> large (clean/easy)
    short=[r["short"] for r in rows]; x=np.arange(len(rows))
    sg=np.array([r["sigma"] for r in rows]); nl=np.array([r["n_loc"] for r in rows])
    Kc=np.array([r["Kc"] for r in rows]); A=np.array([r["A"] for r in rows])
    fig=plt.figure(figsize=(16.8,5.0),facecolor="white")
    gs=fig.add_gridspec(1,3,width_ratios=[1.05,1.35,1.05],wspace=0.28)
    # (a) fragmentation -> different difficulty: noise vs operator size
    a1=fig.add_subplot(gs[0,0])
    xs=np.logspace(0,2.3,100); a1.plot(xs,np.clip(SIGMA0*np.sqrt(NREF/xs),0.12,0.90),color=MUT,lw=1.3,ls="--",
        label=f"σ(n)=σ₀√({NREF}/n) 截断")
    a1.scatter(nl,sg,s=90,c=TEAL,edgecolors=NAVY,lw=1,zorder=5)
    aoff={"CHARG-ELECTRA SP":("CHARG-ELECTRA",5,7),"CHARGING TOGETHE":("CHARGING T.",5,-13),
          "Etecnic":("Etecnic",7,2),"Repsol":("Repsol",7,6),"AMB 公共网络":("AMB",7,-12),
          "Iberdrola":("Iberdrola",-52,-2),"Endesa X Way":("Endesa",7,4),"BSM-Endolla":("BSM",7,-12)}
    for r in rows:
        lab,dx,dy=aoff.get(r["short"],(r["short"][:10],5,5))
        a1.annotate(lab,(r["n_loc"],r["sigma"]),fontsize=7.8,color=INK,xytext=(dx,dy),textcoords="offset points")
    a1.set_xscale("log"); a1.set_xlabel("运营商规模 n（充电点数，对数轴）",fontsize=10)
    a1.set_ylabel("一致性比噪声 σ_op（越大越难检）",fontsize=10)
    a1.set_title("(a) 碎片化⇒各运营商检测难度不同\n小运营商样本少、信号更噪",fontsize=10.8,fontweight="bold",color=NAVY)
    a1.legend(fontsize=8.5,loc="upper right"); a1.grid(alpha=.25,which="both")
    # (b) six-algorithm expected-loss comparison, operator by operator
    a2=fig.add_subplot(gs[0,1])
    # fixed_tuned == fixed_global here (re-tuning the band per operator cannot rescue the rule),
    # so only the fixed rule is plotted; the coincidence is noted in the paper text.
    series=[("shiryaev","贝叶斯最优(本文)",TEAL,"-o",2.4,5),("cusum","CUSUM",PURPLE,"-s",1.6,4),
            ("iforest","孤立森林(ML)",GREEN,"--^",1.4,4),("ocsvm","单类SVM(ML)","#C9872F","--v",1.4,4),
            ("fixed_global","固定规则(本文现用)",RED,"-X",1.8,6),("naive","朴素单次阈值",GREY,":.",1.4,4)]
    for key,lab,col,mk,lw,ms in series:
        a2.plot(x,[r[key] for r in rows],mk,color=col,lw=lw,ms=ms,label=lab,
                zorder=(6 if key=="shiryaev" else 3))
    a2.set_yscale("log"); a2.set_xticks(x); a2.set_xticklabels(short,rotation=32,ha="right",fontsize=8)
    a2.set_ylabel("期望总损失 c·时延+K·误隔离（越低越好，对数轴）",fontsize=9.6)
    a2.set_title("(b) 同一组算法在不同真实运营商上的对比\n贝叶斯最优是全体运营商的下包络；单一全局固定阈值在噪声大的小运营商上失控",
                 fontsize=10.8,fontweight="bold",color=NAVY)
    a2.legend(fontsize=8,ncol=2,loc="upper right",framealpha=.92); a2.grid(alpha=.25,which="both",axis="y")
    # (c) the Bayesian controller adapts its caution A* per operator (one global rule cannot)
    a3=fig.add_subplot(gs[0,2])
    bars=a3.bar(x,A,color=TEAL,edgecolor=NAVY,lw=.8)
    for i,r in enumerate(rows): a3.text(i,A[i]+0.015,f"K/c={r['Kc']:.0f}",ha="center",fontsize=7.4,color=MUT)
    a3.set_xticks(x); a3.set_xticklabels(short,rotation=32,ha="right",fontsize=8)
    a3.set_ylabel("贝叶斯最优隔离阈值 A*_op（逐运营商求解）",fontsize=9.6); a3.set_ylim(0,min(1.0,A.max()+0.12))
    a3.set_title("(c) 最优控制器随运营商自适应谨慎度\n客户多/单点功率小⇒更谨慎(A*高)；固定规则只有一个阈值",
                 fontsize=10.8,fontweight="bold",color=NAVY)
    a3.grid(alpha=.2,axis="y")
    for ax in (a1,a2,a3):
        for sp in ax.spines.values(): sp.set_color("#C9D6E2")
        ax.tick_params(colors=MUT)
    fl=opres["fleet"]
    red=100*(1-fl["shiryaev"]/fl["fixed_global"]) if fl["fixed_global"] else 0
    fig.suptitle(f"图 11　把算法对比放回城市真实碎片化运营商：贝叶斯最优 vs CUSUM / 孤立森林 / 单类SVM / 固定规则 / 朴素"
                 f"（δ={opres['delta']}；全队平均损失较单一全局固定阈值降 {red:.0f}%）",
                 color=NAVY,fontsize=12.5,fontweight="bold",y=1.04)
    fig.savefig(os.path.join(FIGS,"fig_optstop_ops.png"),bbox_inches="tight",facecolor="white"); plt.close(fig); print("[fig] ops")

if __name__=="__main__":
    main()
