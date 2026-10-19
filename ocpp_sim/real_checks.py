"""E1 + E8: validate the SAFETY claim on REAL full-year AMB data (no websocket, pure pandas).

E1  Benign-gate / real-data false-isolation rate. The paper asserts the 2025-04-28 Iberian
    blackout, the backend-migration id churn and the zero-record gaps are judged BENIGN, but
    this was never actually run. Here: reconstruct the AMB network's daily evening consistency
    ratio over the whole year against a 28-day robust (scale*rhythm) baseline, replay the
    deployed band predicate, and measure the empirical false-isolation rate and the blackout's
    margin to the 0.50 edge. Honest finding expected: blackout clears 0.50 only narrowly, and a
    zero-record GAP looks like a curtail attack to the consistency signal (needs the
    command-absence AND-gate / data-availability check) -- a claim/code nuance to report.

E8  Expected-power model ablation: 28-day scale*rhythm baseline vs a STATIC annual-mean
    expected (no rhythm/seasonality). Shows the adaptive baseline is necessary -- a static
    expected false-alarms on the real Jan->Dec demand growth (+~50%).

Writes results_realchecks.json.
"""
import os, json
import numpy as np, pandas as pd

DATA = os.environ.get("AMB_DATA", "/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/amb_data/supp")
BAND_LO, BAND_HI = 0.5, 1.5
EVE = range(16, 22)                              # evening window 16-22h (the attack/detection window)

def load_daily():
    r = pd.read_csv(os.path.join(DATA, "charging_records_clean.csv"),
                    usecols=["start_date", "start_hour", "energy_kwh"], low_memory=False)
    r["d"] = pd.to_datetime(r["start_date"], format="mixed", errors="coerce")
    r = r.dropna(subset=["d"]); r["date"] = r["d"].dt.date
    eve = r[r.start_hour.isin(list(EVE))]
    # full calendar so zero-record days appear (gaps)
    cal = pd.date_range(r["d"].min().normalize(), r["d"].max().normalize(), freq="D").date
    E = eve.groupby("date")["energy_kwh"].sum().reindex(cal, fill_value=0.0)
    C = eve.groupby("date").size().reindex(cal, fill_value=0)
    return pd.DataFrame({"date": cal, "E_eve": E.values, "n_eve": C.values})

def band_flags(ratio):
    return (ratio < BAND_LO) | (ratio > BAND_HI)

def main():
    df = load_daily()
    E = df["E_eve"].values.astype(float)
    # 28-day trailing robust baseline (scale*rhythm seasonal level); min_periods for warmup
    s = pd.Series(E)
    base = s.rolling(28, min_periods=14).median().bfill().values
    ratio_joint = np.divide(E, base, out=np.ones_like(E), where=base > 0)
    static = np.median(E[E > 0])
    ratio_static = E / static
    df["base28"] = base; df["ratio_joint"] = ratio_joint; df["ratio_static"] = ratio_static
    df["date"] = pd.to_datetime(df["date"])

    # anomaly days to inspect separately (NOT counted as ordinary benign for FPR)
    ANOM = {"2025-04-28": "伊比利亚大停电", "2025-11-30": "全网零记录缺口", "2025-12-11": "全网零记录缺口"}
    churn = (df["date"] >= "2025-01-01") & (df["date"] <= "2025-02-28")   # backend-migration id churn window
    is_anom = df["date"].dt.strftime("%Y-%m-%d").isin(ANOM.keys())
    is_zero = df["E_eve"] == 0

    # E1: empirical benign false-isolation rate on ORDINARY benign days (exclude the labelled anomalies & warmup)
    warm = np.arange(len(df)) >= 14
    benign = warm & (~is_anom.values) & (~is_zero.values)
    flags_joint = band_flags(df["ratio_joint"].values)
    fp_joint = int((flags_joint & benign).sum())
    n_benign = int(benign.sum())
    fpr_joint = fp_joint / max(n_benign, 1)
    arl0_days = (n_benign / fp_joint) if fp_joint else float(n_benign)

    # blackout + anomaly verdicts (margin to the 0.50 edge)
    anom_rows = []
    for ds, label in ANOM.items():
        row = df[df["date"].dt.strftime("%Y-%m-%d") == ds]
        if len(row):
            rj = float(row["ratio_joint"].iloc[0]); e = float(row["E_eve"].iloc[0])
            anom_rows.append({"date": ds, "label": label, "ratio_joint": round(rj, 3),
                              "E_eve": round(e, 1), "band_exceed": bool(rj < BAND_LO or rj > BAND_HI),
                              "margin_to_0.5": round(rj - BAND_LO, 3)})
    churn_ratios = df.loc[churn & ~is_zero, "ratio_joint"]
    churn_summary = {"days": int(churn.sum()), "mean_ratio": round(float(churn_ratios.mean()), 3),
                     "frac_in_band": round(float(((churn_ratios >= BAND_LO) & (churn_ratios <= BAND_HI)).mean()), 3)}

    # E8: static-expected (no rhythm) false-alarm rate on the SAME benign days
    flags_static = band_flags(df["ratio_static"].values)
    fp_static = int((flags_static & benign).sum())
    fpr_static = fp_static / max(n_benign, 1)

    res = {"n_days": int(len(df)), "n_benign_days": n_benign, "window": "16-22h",
           "E1": {"fpr_joint_28d": round(fpr_joint, 4), "false_iso_days": fp_joint,
                  "real_data_ARL0_days": round(arl0_days, 1),
                  "anomaly_days": anom_rows, "migration_churn": churn_summary,
                  "note": "zero-record gap days drive r->0 (look like a curtail attack to the consistency signal); "
                          "the deployed detector suppresses this via the command-absence AND-gate / data-availability, not a power test"},
           "E8": {"fpr_joint_28d_baseline": round(fpr_joint, 4), "fpr_static_annual_mean": round(fpr_static, 4),
                  "ratio": round(fpr_static / max(fpr_joint, 1e-9), 1),
                  "annual_growth_Jan_to_Dec": {"jan_mean_E": round(float(df[df.date.dt.month == 1]["E_eve"].mean()), 1),
                                               "dec_mean_E": round(float(df[df.date.dt.month == 12]["E_eve"].mean()), 1)}}}
    print(f"[E1] benign days={n_benign}  false-iso(28d baseline)={fp_joint}  FPR={fpr_joint:.4f}  real ARL0~{arl0_days:.0f} days")
    for a in anom_rows:
        print(f"     {a['date']} {a['label']}: ratio={a['ratio_joint']}  band_exceed={a['band_exceed']}  margin_to_0.5={a['margin_to_0.5']}")
    print(f"     migration churn (Jan-Feb): mean ratio={churn_summary['mean_ratio']} in-band frac={churn_summary['frac_in_band']}")
    print(f"[E8] FPR static-annual-mean={fpr_static:.4f} vs 28d-baseline={fpr_joint:.4f}  (static x{res['E8']['ratio']} more false alarms)")
    print(f"     annual growth Jan {res['E8']['annual_growth_Jan_to_Dec']['jan_mean_E']} -> Dec {res['E8']['annual_growth_Jan_to_Dec']['dec_mean_E']} kWh/eve")
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "results_realchecks.json"), "w"), ensure_ascii=False, indent=1)
    print("[SAVED] results_realchecks.json")

if __name__ == "__main__":
    main()
