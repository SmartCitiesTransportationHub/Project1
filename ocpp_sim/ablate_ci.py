"""E6: bootstrap 95% CI on the per-operator PAIRED loss difference (CUSUM - Shiryaev).

Settles honestly whether "Bayesian is the fleet-wide best" survives Monte-Carlo noise:
on the fleet MEAN CUSUM (4.43) < Shiryaev (4.45), so the two optimal-class methods are
statistically indistinguishable -- this quantifies by how much, per operator and pooled.
Pure numpy; writes results_ci.json.
"""
import json, os
import numpy as np
import optstop as O

shi_thr = np.concatenate([np.linspace(0.08,0.48,9), np.linspace(0.50,0.9985,24)])
cus_thr = np.linspace(0.3,14,30)

def per_ep_loss(stat, nu, thr, K, c=1.0):
    tau = O.tau_threshold(stat, thr) + 1; fi = tau < nu; d = np.where(fi, 0, tau-nu)
    return np.where(fi, K, c*d).astype(float)

def main():
    rows = json.load(open(os.path.join(os.path.dirname(__file__), "results_optstop.json")))["operators"]["rows"]
    rng = np.random.default_rng(0); B = 3000
    out = []; pooled = []
    for o in rows:
        sg, Kc = o["sigma"], o["Kc"]
        r, nu = O.episodes_s(8000, 240, 0.5, sg)
        cc = np.array(O.loss_threshold(O.shiryaev(r,0.5,sg), nu, shi_thr, 1.0, Kc)); A = shi_thr[int(np.argmin(cc[:,1]))]
        ls = per_ep_loss(O.shiryaev(r,0.5,sg), nu, A, Kc)
        cu = np.array(O.loss_threshold(O.cusum(r,0.5,sg), nu, cus_thr, 1.0, Kc)); ct = cus_thr[int(np.argmin(cu[:,1]))]
        lc = per_ep_loss(O.cusum(r,0.5,sg), nu, ct, Kc)
        diff = lc - ls                                     # >0 => Shiryaev better
        pooled.append(diff)
        idx = rng.integers(0, len(diff), (B, len(diff))); bs = diff[idx].mean(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        sig = (lo > 0) or (hi < 0)
        out.append({"short": o["short"], "shiryaev": round(float(ls.mean()),3), "cusum": round(float(lc.mean()),3),
                    "diff_mean": round(float(diff.mean()),3), "ci": [round(float(lo),3), round(float(hi),3)],
                    "significant": bool(sig)})
        print(f"  {o['short'][:16]:16s} shi={ls.mean():5.2f} cus={lc.mean():5.2f} diff(cus-shi)={diff.mean():+.3f} "
              f"95%CI[{lo:+.3f},{hi:+.3f}] {'SIG' if sig else 'ns (overlaps 0)'}")
    alld = np.concatenate(pooled)
    idx = rng.integers(0, len(alld), (B, len(alld))); bsf = alld[idx].mean(1)
    flo, fhi = np.percentile(bsf, [2.5, 97.5])
    fleet = {"diff_mean": round(float(alld.mean()),3), "ci": [round(float(flo),3), round(float(fhi),3)],
             "significant": bool((flo>0) or (fhi<0))}
    nsig = sum(1 for o in out if o["significant"])
    print(f"[FLEET] pooled diff(cus-shi)={alld.mean():+.4f} 95%CI[{flo:+.3f},{fhi:+.3f}] "
          f"{'SIG' if fleet['significant'] else 'ns'} | per-op significant: {nsig}/{len(out)}")
    json.dump({"per_operator": out, "fleet": fleet, "n_sig": nsig, "n_op": len(out), "B": B},
              open(os.path.join(os.path.dirname(__file__), "results_ci.json"), "w"), ensure_ascii=False, indent=1)
    print("[SAVED] results_ci.json")

if __name__ == "__main__":
    main()
