# =====================================================================
# pklnprt.py — LK PKLNPRT Triwulanan Kab. Cirebon (Rebasing 2025=100)
# VERSI 3:
#  - 2 MODE KERJA: SIMULASI (data contoh) & TEMPLATE KOSONG (data riil)
#  - Ganti mode fleksibel dari sidebar (dengan konfirmasi)
#  - Simpan/Muat pekerjaan (.pkl) + Ekspor Excel ala template BPS
# Jalankan: streamlit run pklnprt.py
# =====================================================================
import math
import pickle
from datetime import date
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="LK PKLNPRT Kab. Cirebon (2025=100)",
                   page_icon="📊", layout="wide")

# ---------------------------------------------------------------------
# 0. KONFIGURASI WILAYAH & PARAMETER
# ---------------------------------------------------------------------
KODE_PROV, NAMA_PROV = "32", "Jawa Barat"
KODE_KAB, NAMA_KAB = "09", "Kabupaten Cirebon"
BASE_YEAR = 2025

KODE_LEMBAGA = {
    "1": "Organisasi Kemasyarakatan", "2": "Organisasi Sosial",
    "3": "Organisasi Profesi dan Serikat Buruh",
    "4": "Organisasi Kebudayaan, Olahraga, dan Rekreasi",
    "5": "Partai Politik", "6": "Lembaga Keagamaan",
}
SHORT = {"1": "Ormas", "2": "Orsos", "3": "Orprof",
         "4": "Orseni", "5": "Parpol", "6": "Lemb. Keagamaan"}
LEMBAGA_COLS = list(SHORT.values())
LEMBAGA_SHARE = {"1": 0.20, "2": 0.12, "3": 0.08,
                 "4": 0.07, "5": 0.08, "6": 0.45}
RINCIAN_KEAGAMAAN = ["Masjid", "Musholla", "Gereja Kristen", "Gereja Katolik",
                     "Pura", "Vihara", "Klenteng", "Badan Sosial Keagamaan"]

B4A_COMPONENTS = [f"b4a_r{i}" for i in range(1, 12)]
B4A_LABEL = {
    "b4a_r1": "Konsumsi Bahan Bakar/BBM", "b4a_r2": "Listrik, Air, dan Gas",
    "b4a_r3": "Pos, Giro, Telepon, Internet", "b4a_r4": "ATK, Fotokopi, Percetakan",
    "b4a_r5": "Pemeliharaan & Perbaikan Ringan", "b4a_r6": "Sewa Gedung & Peralatan",
    "b4a_r7": "Jasa Konsultan/Hukum/Tenaga Ahli", "b4a_r8": "Perjalanan Dinas & Transportasi",
    "b4a_r9": "Pertemuan, Rapat, Konsumsi", "b4a_r10": "Upah, Gaji & Honorarium",
    "b4a_r11": "Biaya Operasional Lainnya",
}
IHK_MAP = {
    "b4a_r1": "IHK Bensin/Bahan Bakar", "b4a_r2": "IHK Tarif Listrik & Air",
    "b4a_r3": "IHK Layanan Informasi & Komunikasi", "b4a_r4": "IHK Perlengkapan RT & ATK",
    "b4a_r5": "IHK Pemeliharaan Rumah/Gedung", "b4a_r6": "IHK Sewa Rumah",
    "b4a_r7": "IHK Jasa Lainnya", "b4a_r8": "IHK Angkutan/Transportasi",
    "b4a_r9": "IHK Makanan Jadi/Restoran", "b4a_r10": "IHK Umum (Upah)",
    "b4a_r11": "IHK Umum",
}
IHK_COLS = list(dict.fromkeys(IHK_MAP.values()))
COPNI_MAP = {
    "1. Pelayanan Keagamaan": ["Lemb. Keagamaan"],
    "2. Layanan Sosial & Kemanusiaan": ["Orsos"],
    "3. Layanan Kemasyarakatan, Profesi & Ketenagakerjaan": ["Ormas", "Orprof"],
    "4. Rekreasi, Seni & Budaya": ["Orseni"],
    "5. Politik": ["Parpol"],
}
QUARTERS = [f"{y}Q{q}" for y in range(2019, 2026) for q in range(1, 5)]
Q_SURVEI = [q for q in QUARTERS if q >= "2023Q1"]
Q_DEFL_AVAILABLE = [q for q in QUARTERS if q >= "2024Q1"]

MODE_LABEL = {"simulasi": "🎮 SIMULASI — ada data contoh",
              "kosong": "📄 TEMPLATE KOSONG — input data riil"}

# ---------------------------------------------------------------------
# 0b. DATA JANGKAR BPS (seri rilis resmi template LK BPS)
# ---------------------------------------------------------------------
RILIS_JABAR_ADHB = [51368.08, 53041.56, 50719.66, 50965.18, 50283.85, 49998.24,
                    50394.67, 50774.80, 49142.10, 52798.84, 52654.56, 53320.72,
                    53238.46, 57558.74, 58706.37, 59495.45, 59552.44, 65084.42,
                    64258.97, 72314.36, 75820.02, 73343.90, 73007.84, 77908.65,
                    78588.47, 80508.20, 77603.16, 84843.66]
RILIS_JABAR_ADHK = [34348.26, 35070.44, 33238.36, 33370.36, 32635.16, 32340.50,
                    32600.18, 32730.64, 31444.18, 33654.94, 33535.67, 33777.13,
                    33302.23, 35348.66, 35544.14, 35708.60, 35397.38, 38452.02,
                    37819.46, 42269.60, 43939.34, 42217.95, 42152.66, 44832.84,
                    45287.91, 45520.04, 43737.46, 47478.74]
SHARE_CIREBON = 0.047

DATA_BPS = pd.DataFrame({
    "Indikator": ["Jumlah Penduduk Kab. Cirebon (2024, jiwa)", "Luas Wilayah (km²)",
                  "Jumlah Kecamatan", "Masjid (unit)", "Musholla (unit)",
                  "Gereja (unit)", "Pura/Vihara/Klenteng (unit)",
                  "Parpol Peserta Pemilu 2024", "Pertumbuhan Ekonomi 2024 (%)"],
    "Nilai (aproksimasi)": ["± 2.360.000", "± 984", "40", "± 2.867", "± 4.408",
                            "± 70", "± 16", "18", "± 4,9"],
    "Sumber": ["Kab. Cirebon Dalam Angka (BPS)"] * 3 +
              ["Podes / SIMAS Kemenag"] * 4 + ["KPU", "BPS Kab. Cirebon"],
})
PORTAL_LINKS = {
    "BPS Kab. Cirebon": "https://cirebonkab.bps.go.id",
    "BPS Prov. Jawa Barat": "https://jabar.bps.go.id",
    "BPS Republik Indonesia": "https://www.bps.go.id",
    "Dashboard LNPRT (raw data SKLNPRT)": "https://lnprt.web.bps.go.id",
}

# ---------------------------------------------------------------------
# 1. UTILITAS (anti #DIV/0!)
# ---------------------------------------------------------------------
def safe_div(a, b, default=0.0):
    try:
        if b is None or pd.isna(b) or b == 0:
            return default
        v = float(a) / float(b)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return default

def clean_pct(v):
    try:
        v = float(v)
        return 0.0 if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return 0.0

def year_of(q): return int(q[:4])
def growth_qtq(df): return df.pct_change(axis=0) * 100.0
def growth_yoy(df): return df.pct_change(periods=4, axis=0) * 100.0
def fmt_num(v, nd=2):
    try:
        return "-" if pd.isna(v) else f"{v:,.{nd}f}"
    except Exception:
        return "-"

# ---------------------------------------------------------------------
# 2. GENERATOR DATA SIMULASI (berbasis jangkar BPS)
# ---------------------------------------------------------------------
RNG = np.random.default_rng(2025)

def build_ihk_simulasi():
    inflasi = {"IHK Bensin/Bahan Bakar": 0.035, "IHK Tarif Listrik & Air": 0.030,
               "IHK Layanan Informasi & Komunikasi": 0.015, "IHK Perlengkapan RT & ATK": 0.025,
               "IHK Pemeliharaan Rumah/Gedung": 0.030, "IHK Sewa Rumah": 0.028,
               "IHK Jasa Lainnya": 0.026, "IHK Angkutan/Transportasi": 0.032,
               "IHK Makanan Jadi/Restoran": 0.035, "IHK Umum (Upah)": 0.027, "IHK Umum": 0.025}
    data = {}
    for comp, rate in inflasi.items():
        vals = np.empty(len(QUARTERS)); vals[-1] = 100.0 + RNG.uniform(-0.4, 0.4)
        for i in range(len(QUARTERS) - 2, -1, -1):
            vals[i] = vals[i + 1] / (1.0 + rate / 4.0 + RNG.normal(0, 0.002))
        idx25 = [i for i, q in enumerate(QUARTERS) if year_of(q) == 2025]
        data[comp] = np.round(vals / vals[idx25].mean() * 100.0, 2)
    return pd.DataFrame(data, index=QUARTERS)

def build_populasi_simulasi():
    pop = pd.DataFrame({"Kode": list(KODE_LEMBAGA.keys()),
                        "Lembaga": [KODE_LEMBAGA[k] for k in KODE_LEMBAGA],
                        "Jumlah": [465, 128, 92, 104, 18, 0],
                        "Sumber": ["Bakesbangpol", "Podes & Dinsos", "Podes & Disnaker",
                                   "Podes & Dispora", "KPU Kab. Cirebon", "Podes, Kemenag & SIMAS"]})
    rinci = pd.DataFrame({"Rincian": RINCIAN_KEAGAMAAN,
                          "Jumlah": [2867, 4408, 61, 9, 6, 6, 4, 64],
                          "Sumber": ["Podes / SIMAS Kemenag"] * 8})
    return pop, rinci

def build_raw_sklnp_simulasi():
    rows, sid = [], 0
    n_sampel = {"1": 8, "2": 5, "3": 4, "4": 4, "5": 6, "6": 12}
    skala = {"1": 9.5e6, "2": 12.0e6, "3": 7.5e6, "4": 8.0e6, "5": 22.0e6, "6": 6.5e6}
    bobot = [0.06, 0.10, 0.07, 0.09, 0.08, 0.10, 0.07, 0.09, 0.10, 0.18, 0.06]
    for q in Q_SURVEI:
        y, t = year_of(q), int(q[-1])
        for kode, nama in KODE_LEMBAGA.items():
            for _ in range(max(2, int(n_sampel[kode] + RNG.integers(-1, 2)))):
                sid += 1
                total_q = skala[kode] * (1 + 0.025 * (y - 2023) + 0.01 * (t - 1)) * RNG.uniform(0.75, 1.30)
                if kode == "5" and q == "2024Q1": total_q *= 2.35
                if kode == "5" and q in ("2024Q3", "2024Q4"): total_q *= 1.85
                if kode == "6" and t == 2: total_q *= 1.28
                rec = {"triwulan": q, "kode_lembaga": kode, "lembaga": nama,
                       "id_sample": f"CRB-{sid:05d}"}
                for c, w in zip(B4A_COMPONENTS, bobot):
                    rec[c] = round(float(total_q * w * RNG.uniform(0.8, 1.2)), 0)
                rows.append(rec)
    return pd.DataFrame(rows)

def build_rilis_kabupaten():
    adhb = {nm: [] for nm in LEMBAGA_COLS}; adhk = {nm: [] for nm in LEMBAGA_COLS}
    for i, q in enumerate(QUARTERS):
        seas = 1.0 + 0.03 * math.sin(2 * math.pi * (int(q[-1]) - 1) / 4.0)
        tot_h = RILIS_JABAR_ADHB[i] * SHARE_CIREBON
        tot_k = RILIS_JABAR_ADHK[i] * SHARE_CIREBON
        for kode, nm in SHORT.items():
            v = tot_h * LEMBAGA_SHARE[kode] * seas * (1 + RNG.normal(0, 0.008))
            if kode == "5" and q == "2024Q1": v *= 1.9
            if kode == "5" and q in ("2024Q3", "2024Q4"): v *= 1.5
            adhb[nm].append(v)
            adhk[nm].append(v / (tot_h / tot_k))
    return (pd.DataFrame(adhb, index=QUARTERS).round(2),
            pd.DataFrame(adhk, index=QUARTERS).round(2))

def build_sut_simulasi():
    vals = {"Ormas": 6420.0, "Orsos": 3980.0, "Orprof": 2660.0, "Orseni": 2280.0,
            "Parpol": 3540.0, "Lemb. Keagamaan": 13750.0}
    return pd.DataFrame({"Lembaga": list(vals.keys()),
                         "SUT_2025 (juta Rp)": [round(v * SHARE_CIREBON * RNG.uniform(1.0, 1.05), 2)
                                                for v in vals.values()]})

def build_adjustment_simulasi():
    zero = pd.DataFrame(0.0, index=QUARTERS, columns=LEMBAGA_COLS)
    kurban, zakat, bencana, pilkada = zero.copy(), zero.copy(), zero.copy(), zero.copy()
    for q in ("2024Q2", "2025Q2"):
        kurban.loc[q, "Lemb. Keagamaan"] = 190.0; kurban.loc[q, "Orsos"] = 40.0; kurban.loc[q, "Ormas"] = 19.0
    for q in ("2024Q1", "2025Q1"):
        zakat.loc[q, "Lemb. Keagamaan"] = 290.0; zakat.loc[q, "Orsos"] = 112.0; zakat.loc[q, "Ormas"] = 51.0
    for q in ("2024Q4", "2025Q4"):
        bencana.loc[q, "Orsos"] = 84.0; bencana.loc[q, "Ormas"] = 44.0; bencana.loc[q, "Lemb. Keagamaan"] = 61.0
    pilkada.loc["2024Q1", "Parpol"] = 680.0
    pilkada.loc["2024Q3", "Parpol"] = 460.0
    pilkada.loc["2024Q4", "Parpol"] = 525.0
    return kurban, zakat, bencana, pilkada

def build_indikator_simulasi():
    data = {}
    for nm in LEMBAGA_COLS:
        v = np.empty(len(QUARTERS)); v[-1] = 100.0
        for i in range(len(QUARTERS) - 2, -1, -1):
            v[i] = v[i + 1] / (1 + RNG.normal(0.006, 0.002))
        data[nm] = np.round(v, 2)
    return pd.DataFrame(data, index=QUARTERS)

FENOMENA_DEFAULT = {
    "1": "Meningkatnya penghimpunan zakat, infak, sedekah, dan donasi, serta kegiatan bantuan "
         "kemanusiaan akibat banjir/rob di wilayah pantura Cirebon mendorong organisasi "
         "kemasyarakatan memperluas penyaluran bantuan.",
    "2": "Kenaikan harga bahan pangan meningkatkan biaya operasional panti asuhan/wreda; "
         "penyaluran bantuan ZIS dan donasi kemanusiaan meningkat.",
    "3": "Penyesuaian UMK Kab. Cirebon mendorong aktivitas advokasi dan pendidikan "
         "ketenagakerjaan oleh serikat buruh.",
    "4": "Penyelenggaraan festival budaya, turnamen olahraga, dan event akhir tahun "
         "meningkatkan aktivitas Orseni.",
    "5": "Pasca-Pemilu/Pilkada 2024, partai politik melakukan konsolidasi internal dan "
         "kaderisasi; belanja kampanye non-APBD tercatat pada triwulan pemilu.",
    "6": "Peringatan hari besar keagamaan, penyaluran zakat/kurban, serta operasional "
         "rumah ibadah meningkat.",
    "0": "Aktivitas LNPRT didorong filantropi, layanan sosial, kegiatan keagamaan, "
         "serta penanganan bencana.",
}

# ---------------------------------------------------------------------
# 3. DATASET PER MODE + GANTI MODE + RESET
# ---------------------------------------------------------------------
def build_dataset_simulasi():
    pop, rinci = build_populasi_simulasi()
    rh, rk = build_rilis_kabupaten()
    k, z, b, p = build_adjustment_simulasi()
    return dict(ihk=build_ihk_simulasi(), populasi=pop, pop_rinci=rinci,
                raw=build_raw_sklnp_simulasi(), rilis_adhb=rh, rilis_adhk=rk,
                sut=build_sut_simulasi(), adj_kurban=k, adj_zakat=z,
                adj_bencana=b, adj_pilkada=p,
                indikator=build_indikator_simulasi(), fenomena=FENOMENA_DEFAULT.copy())

def build_dataset_kosong():
    nol6 = pd.DataFrame(0.0, index=QUARTERS, columns=LEMBAGA_COLS)
    return dict(
        ihk=pd.DataFrame(np.nan, index=QUARTERS, columns=IHK_COLS),
        populasi=pd.DataFrame({"Kode": list(KODE_LEMBAGA.keys()),
                               "Lembaga": [KODE_LEMBAGA[k] for k in KODE_LEMBAGA],
                               "Jumlah": [0] * 6, "Sumber": ["-"] * 6}),
        pop_rinci=pd.DataFrame({"Rincian": RINCIAN_KEAGAMAAN,
                                "Jumlah": [0] * 8, "Sumber": ["-"] * 8}),
        raw=pd.DataFrame(columns=["triwulan", "kode_lembaga", "lembaga", "id_sample"] + B4A_COMPONENTS),
        rilis_adhb=nol6.copy(), rilis_adhk=nol6.copy(),
        sut=pd.DataFrame({"Lembaga": LEMBAGA_COLS, "SUT_2025 (juta Rp)": [0.0] * 6}),
        adj_kurban=nol6.copy(), adj_zakat=nol6.copy(),
        adj_bencana=nol6.copy(), adj_pilkada=nol6.copy(),
        indikator=pd.DataFrame(np.nan, index=QUARTERS, columns=LEMBAGA_COLS),
        fenomena={k: "" for k in ["1", "2", "3", "4", "5", "6", "0"]},
    )

def apply_dataset(mode):
    ds = build_dataset_simulasi() if mode == "simulasi" else build_dataset_kosong()
    for k, v in ds.items():
        st.session_state[k] = v
    st.session_state.pop("_last_loaded", None)

def apply_mode_cb(target):
    st.session_state.mode = target
    apply_dataset(target)
    st.session_state.mode_radio = MODE_LABEL[target]

def reset_cb():
    apply_dataset(st.session_state.mode)
    st.session_state.periode = "2025Q4"
    st.session_state.beta = 1.0
    st.session_state.periode_sel = "2025Q4"
    st.session_state.beta_num = 1.0

# ---------------------------------------------------------------------
# 4. SIMPAN / MUAT PEKERJAAN
# ---------------------------------------------------------------------
STATE_KEYS = ["mode", "periode", "beta", "ihk", "populasi", "pop_rinci", "raw",
              "rilis_adhb", "rilis_adhk", "sut", "adj_kurban", "adj_zakat",
              "adj_bencana", "adj_pilkada", "indikator", "fenomena"]

def build_save_bytes():
    payload = {k: st.session_state.get(k) for k in STATE_KEYS}
    payload["_meta"] = {"tanggal_simpan": str(date.today()),
                        "wilayah": f"{NAMA_KAB} - {NAMA_PROV}",
                        "mode": st.session_state.mode,
                        "periode": st.session_state.periode}
    return pickle.dumps(payload)

def restore_save(raw_bytes):
    payload = pickle.loads(raw_bytes)
    for k in STATE_KEYS:
        if k in payload and payload[k] is not None:
            st.session_state[k] = payload[k]
    st.session_state.setdefault("mode", "simulasi")
    return payload.get("_meta", {})

def init_state():
    if "initialized" in st.session_state:
        return
    st.session_state.mode = "simulasi"
    st.session_state.periode = "2025Q4"
    st.session_state.beta = 1.0
    apply_dataset("simulasi")
    st.session_state.initialized = True

init_state()

# ---------------------------------------------------------------------
# 5. PIPELINE WORKBOOK 1 (aman utk data kosong)
# ---------------------------------------------------------------------
def wb1_total_biaya(raw, ihk):
    df = raw.copy()
    if df.empty:
        df["b4a_jml_adhb"] = pd.Series(dtype=float)
        df["b4a_jml_adhk"] = pd.Series(dtype=float)
        return df
    for c in B4A_COMPONENTS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["b4a_jml_adhb"] = df[B4A_COMPONENTS].sum(axis=1)
    real = 0.0
    for c in B4A_COMPONENTS:
        idx = ihk[IHK_MAP[c]].reindex(df["triwulan"]).values.astype(float)
        real += np.where(np.where(idx == 0, np.nan, idx) > 0,
                         df[c].values / np.where(idx == 0, np.nan, idx) * 100.0, 0.0)
    df["b4a_jml_adhk"] = np.nan_to_num(real, nan=0.0)
    return df

def wb1_rata_rata(df_total):
    if df_total.empty:
        return pd.DataFrame(columns=["triwulan", "kode_lembaga", "n_sampel",
                                     "sum_adhb", "sum_adhk", "rata_adhb", "rata_adhk"])
    g = df_total.groupby(["triwulan", "kode_lembaga"], as_index=False).agg(
        n_sampel=("id_sample", "count"),
        sum_adhb=("b4a_jml_adhb", "sum"), sum_adhk=("b4a_jml_adhk", "sum"))
    g["rata_adhb"] = np.where(g["n_sampel"] > 0, g["sum_adhb"] / g["n_sampel"].clip(lower=1), 0.0)
    g["rata_adhk"] = np.where(g["n_sampel"] > 0, g["sum_adhk"] / g["n_sampel"].clip(lower=1), 0.0)
    return g

def wb1_agregat(rata, populasi, pop_rinci):
    kosong_h = pd.DataFrame(0.0, index=Q_SURVEI, columns=LEMBAGA_COLS)
    if rata.empty:
        return kosong_h.copy(), kosong_h.copy(), pd.DataFrame(
            columns=["triwulan", "kode", "lembaga", "n_sampel", "populasi",
                     "total_adhb_jt", "total_adhk_jt"])
    pop_map = dict(zip(populasi["Kode"].astype(str),
                       pd.to_numeric(populasi["Jumlah"], errors="coerce").fillna(0)))
    pop_map["6"] = float(pd.to_numeric(pop_rinci["Jumlah"], errors="coerce").fillna(0).sum())
    rec = []
    for _, r in rata.iterrows():
        pop = pop_map.get(str(r["kode_lembaga"]), 0)
        rec.append({"triwulan": r["triwulan"], "kode": r["kode_lembaga"],
                    "lembaga": SHORT.get(str(r["kode_lembaga"]), "Lainnya"),
                    "n_sampel": r["n_sampel"], "populasi": pop,
                    "total_adhb_jt": r["rata_adhb"] * pop / 1e6,
                    "total_adhk_jt": r["rata_adhk"] * pop / 1e6})
    a = pd.DataFrame(rec)
    p_adhb = a.pivot(index="triwulan", columns="lembaga", values="total_adhb_jt").fillna(0.0)
    p_adhk = a.pivot(index="triwulan", columns="lembaga", values="total_adhk_jt").fillna(0.0)
    p_adhb = p_adhb.reindex(index=Q_SURVEI, columns=LEMBAGA_COLS, fill_value=0.0)
    p_adhk = p_adhk.reindex(index=Q_SURVEI, columns=LEMBAGA_COLS, fill_value=0.0)
    return p_adhb, p_adhk, a

# ---------------------------------------------------------------------
# 6. PIPELINE WORKBOOK 2
# ---------------------------------------------------------------------
def wb2_ipd(h, k):
    ipd = pd.DataFrame(index=h.index, columns=h.columns, dtype=float)
    for c in h.columns:
        ipd[c] = [safe_div(a, b) * 100.0 for a, b in zip(h[c], k[c])]
    return ipd.astype(float)

def wb2_backcast(agg_h, agg_k, r_h, r_k):
    out_h = pd.DataFrame(0.0, index=QUARTERS, columns=LEMBAGA_COLS)
    out_k = pd.DataFrame(0.0, index=QUARTERS, columns=LEMBAGA_COLS)
    for c in LEMBAGA_COLS:
        out_h.loc[agg_h.index, c] = agg_h[c]
        out_k.loc[agg_k.index, c] = agg_k[c]
        anchor = agg_h.index.min()
        i0 = QUARTERS.index(anchor)
        v = out_h.loc[anchor, c]
        for i in range(i0 - 1, -1, -1):
            q, qn = QUARTERS[i], QUARTERS[i + 1]
            v = v * safe_div(r_h.loc[q, c], r_h.loc[qn, c], 1.0)
            out_h.loc[q, c] = v
        v = out_k.loc[anchor, c]
        for i in range(i0 - 1, -1, -1):
            q, qn = QUARTERS[i], QUARTERS[i + 1]
            v = v * safe_div(r_k.loc[q, c], r_k.loc[qn, c], 1.0)
            out_k.loc[q, c] = v
    return out_h.astype(float), out_k.astype(float)

def wb2_theta(sut, e1_h):
    rows = []
    for _, r in sut.iterrows():
        nm = r["Lembaga"]
        s25 = float(pd.to_numeric(e1_h.loc[e1_h.index.map(year_of) == 2025, nm],
                                  errors="coerce").sum()) if nm in e1_h.columns else 0.0
        rows.append({"Lembaga": nm, "SUT_2025": float(r["SUT_2025 (juta Rp)"]),
                     "Sum_Agregat_2025": round(s25, 2),
                     "Theta": round(safe_div(float(r["SUT_2025 (juta Rp)"]), s25, 1.0), 4)})
    return pd.DataFrame(rows)

def wb2_deflator(ihk, ipd):
    defl = pd.Series(index=QUARTERS, dtype=float)
    for q in Q_DEFL_AVAILABLE:
        defl[q] = ihk.loc[q, "IHK Umum"] if "IHK Umum" in ihk.columns else np.nan
    i0 = QUARTERS.index(min(Q_DEFL_AVAILABLE))
    for i in range(i0 - 1, -1, -1):
        q, qn = QUARTERS[i], QUARTERS[i + 1]
        a = float(ipd.loc[q].mean()) if q in ipd.index else 0.0
        b = float(ipd.loc[qn].mean()) if qn in ipd.index else 0.0
        defl[q] = defl[qn] * safe_div(a, b, 1.0)
    return defl.fillna(0.0).astype(float)

def wb2_inisial(e1_h, theta_df, defl):
    th = dict(zip(theta_df["Lembaga"], theta_df["Theta"]))
    nom = e1_h.copy()
    for c in nom.columns:
        nom[c] = nom[c] * th.get(c, 1.0)
    real = pd.DataFrame(index=nom.index, columns=nom.columns, dtype=float)
    for c in nom.columns:
        real[c] = [safe_div(v, d) * 100.0 for v, d in zip(nom[c], defl)]
    return nom.astype(float), real.astype(float)

def wb2_final(nom, adj_total, defl, beta):
    h = beta * nom + adj_total
    k = pd.DataFrame(index=h.index, columns=h.columns, dtype=float)
    for c in h.columns:
        k[c] = [safe_div(v, d) * 100.0 for v, d in zip(h[c], defl)]
    return h.astype(float), k.astype(float)

def wb2_copni(h):
    out = pd.DataFrame(index=h.index)
    for fungsi, anggota in COPNI_MAP.items():
        out[fungsi] = h[[c for c in anggota if c in h.columns]].sum(axis=1)
    out["TOTAL"] = h.sum(axis=1)
    return out

def wb2_qc(h, adj_k, adj_z, adj_p, theta_df, beta, populasi, raw, defl):
    cek = []
    yoy = growth_yoy(h); last_q = st.session_state.periode
    def add(no, nama, ok, ket):
        cek.append({"No": no, "Pemeriksaan": nama,
                    "Status": "✅ LULUS" if ok else "⚠️ PERHATIAN", "Keterangan": ket})
    q_kurban = [q for q in adj_k.index if q in ("2024Q2", "2025Q2")]
    q_zakat = [q for q in adj_z.index if q in ("2024Q1", "2025Q1")]
    q_pilkada = [q for q in adj_p.index if year_of(q) == 2024]
    v_k = float(adj_k.loc[q_kurban].sum().sum()) if q_kurban else 0.0
    v_z = float(adj_z.loc[q_zakat].sum().sum()) if q_zakat else 0.0
    v_p = float(adj_p.loc[q_pilkada].sum().sum()) if q_pilkada else 0.0
    add(1, "Lonjakan musiman Kurban (Iduladha Q2)", v_k > 0,
        f"Adjustment kurban Q2 = {fmt_num(v_k)} juta Rp." if v_k > 0 else "Adjustment kurban Q2 kosong.")
    add(2, "Lonjakan musiman Zakat (Ramadan Q1)", v_z > 0,
        f"Adjustment zakat Q1 = {fmt_num(v_z)} juta Rp." if v_z > 0 else "Adjustment zakat Q1 kosong.")
    p24 = float(h.loc[h.index.map(year_of) == 2024, "Parpol"].sum())
    p23 = float(h.loc[h.index.map(year_of) == 2023, "Parpol"].sum())
    add(3, "Anomali tahun politik Parpol (2024 vs 2023)",
        p24 > p23 and v_p > 0,
        f"Parpol 2024 ({fmt_num(p24)}) vs 2023 ({fmt_num(p23)}).")
    for i, c in enumerate(LEMBAGA_COLS):
        v = clean_pct(yoy.loc[last_q, c]) if last_q in yoy.index else 0.0
        add(4 + i, f"Outlier YoY {c} ({last_q})", not (v > 20 or v < -15),
            f"YoY = {fmt_num(v)}% (ambang -15% s.d. 20%).")
    add(10, "Balancing factor Beta wajar (0.90-1.10)", 0.90 <= beta <= 1.10, f"Beta = {beta:.4f}.")
    ext = theta_df[(theta_df["Theta"] < 0.8) | (theta_df["Theta"] > 1.2)]
    add(11, "Theta SUT 2025 wajar (0.8-1.2)", len(ext) == 0,
        "Semua Theta dalam rentang." if len(ext) == 0 else f"Di luar rentang: {', '.join(ext['Lembaga'])}.")
    add(12, "Deflator positif & konsisten", bool((defl > 0).all()),
        "Seluruh deflator > 0." if bool((defl > 0).all()) else "Ada deflator 0/kosong — lengkapi IHK Umum.")
    add(13, "Konsistensi ADHB/ADHK terhadap deflator", True,
        "ADHK_Final = ADHB_Final/Deflator x 100 diterapkan seluruh baris.")
    tot_pop = int(pd.to_numeric(populasi["Jumlah"], errors="coerce").fillna(0).head(5).sum()) + \
              int(pd.to_numeric(st.session_state.pop_rinci["Jumlah"], errors="coerce").fillna(0).sum())
    add(14, "Populasi lembaga terisi (>0)", tot_pop > 0, f"Total populasi = {tot_pop} lembaga.")
    add(15, "Sampel SKLNP tersedia", raw["triwulan"].nunique() >= 8,
        f"Mencakup {raw['triwulan'].nunique()} triwulan survei.")
    return pd.DataFrame(cek)

def compute_all():
    ihk, raw = st.session_state.ihk, st.session_state.raw
    total = wb1_total_biaya(raw, ihk)
    rata = wb1_rata_rata(total)
    agg_h, agg_k, det = wb1_agregat(rata, st.session_state.populasi, st.session_state.pop_rinci)
    ipd = wb2_ipd(st.session_state.rilis_adhb, st.session_state.rilis_adhk)
    e1_h, e1_k = wb2_backcast(agg_h, agg_k, st.session_state.rilis_adhb, st.session_state.rilis_adhk)
    theta = wb2_theta(st.session_state.sut, e1_h)
    defl = wb2_deflator(ihk, ipd)
    nom, real = wb2_inisial(e1_h, theta, defl)
    adj_total = (st.session_state.adj_kurban + st.session_state.adj_zakat +
                 st.session_state.adj_bencana + st.session_state.adj_pilkada)
    h_f, k_f = wb2_final(nom, adj_total, defl, st.session_state.beta)
    copni = wb2_copni(h_f)
    qc = wb2_qc(h_f, st.session_state.adj_kurban, st.session_state.adj_zakat,
                st.session_state.adj_pilkada, theta, st.session_state.beta,
                st.session_state.populasi, raw, defl)
    return dict(total=total, rata=rata, det=det, agg_adhb=agg_h, agg_adhk=agg_k,
                ipd=ipd, e1_adhb=e1_h, e1_adhk=e1_k, theta=theta, defl=defl,
                nom_in=nom, real_in=real, total_adj=adj_total,
                adhb_f=h_f, adhk_f=k_f, copni=copni, qc=qc)

# ---------------------------------------------------------------------
# 7. EKSPOR EXCEL
# ---------------------------------------------------------------------
def export_excel(R):
    buf = BytesIO()
    home = pd.DataFrame({"Item": ["Kode Provinsi", "Provinsi", "Kode Kabupaten/Kota",
                                  "Kabupaten/Kota", "Periode", "Tahun Dasar", "Mode Kerja",
                                  "Tanggal Ekspor"],
                         "Nilai": [KODE_PROV, NAMA_PROV, KODE_KAB, NAMA_KAB,
                                   st.session_state.periode, f"{BASE_YEAR}=100",
                                   MODE_LABEL[st.session_state.mode], str(date.today())]})
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        home.to_excel(xw, sheet_name="Home", index=False)
        R["total"].to_excel(xw, sheet_name="D0 Raw Data SKLNP", index=False)
        st.session_state.ihk.to_excel(xw, sheet_name="D4 Setting IHK")
        st.session_state.populasi.to_excel(xw, sheet_name="D2 Populasi", index=False)
        st.session_state.pop_rinci.to_excel(xw, sheet_name="D2 Populasi", index=False,
                                            startrow=len(st.session_state.populasi) + 3)
        R["agg_adhb"].to_excel(xw, sheet_name="D3 Agregat ADHB")
        R["agg_adhk"].to_excel(xw, sheet_name="D3 Agregat ADHK", startrow=len(R["agg_adhk"]) + 3)
        st.session_state.rilis_adhb.to_excel(xw, sheet_name="E0 Rilis ADHB 2010")
        st.session_state.rilis_adhk.to_excel(xw, sheet_name="E0 Rilis ADHK 2010",
                                             startrow=len(st.session_state.rilis_adhk) + 3)
        R["e1_adhb"].to_excel(xw, sheet_name="E1 Backcast ADHB")
        R["e1_adhk"].to_excel(xw, sheet_name="E1 Backcast ADHK", startrow=len(R["e1_adhk"]) + 3)
        R["theta"].to_excel(xw, sheet_name="E2 Theta SUT 2025", index=False)
        R["defl"].to_frame("Deflator_2025=100").to_excel(xw, sheet_name="E4 Deflator")
        R["nom_in"].to_excel(xw, sheet_name="E3 Nominal Inisial")
        R["real_in"].to_excel(xw, sheet_name="E5 Real Inisial")
        st.session_state.adj_kurban.to_excel(xw, sheet_name="Adj Kurban")
        st.session_state.adj_zakat.to_excel(xw, sheet_name="Adj Zakat")
        st.session_state.adj_bencana.to_excel(xw, sheet_name="Adj Bencana")
        st.session_state.adj_pilkada.to_excel(xw, sheet_name="Adj Pilkada")
        R["total_adj"].to_excel(xw, sheet_name="Adj Total")
        pd.DataFrame({"Beta": [st.session_state.beta]}).to_excel(xw, sheet_name="R8 Beta", index=False)
        R["adhb_f"].to_excel(xw, sheet_name="R9 ADHB Final")
        R["adhk_f"].to_excel(xw, sheet_name="R10 ADHK Final")
        R["copni"].to_excel(xw, sheet_name="A11 COPNI")
        st.session_state.indikator.to_excel(xw, sheet_name="I6 Indikator")
        pd.DataFrame({"Kode": list(st.session_state.fenomena.keys()),
                      "Fenomena": list(st.session_state.fenomena.values())}
                     ).to_excel(xw, sheet_name="F7 Fenomena", index=False)
        R["qc"].to_excel(xw, sheet_name="QC", index=False)
        DATA_BPS.to_excel(xw, sheet_name="Referensi Data BPS", index=False)
    buf.seek(0)
    return buf

# ---------------------------------------------------------------------
# 8. SIDEBAR (Simpan/Muat, MODE, parameter, reset)
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("📊 LK PKLNPRT Triwulanan")
    st.success(f"**{NAMA_KAB}** — {NAMA_PROV} (Kode {KODE_PROV}.{KODE_KAB})\n\n"
               f"Tahun Dasar {BASE_YEAR}=100")

    st.divider()
    st.markdown("#### 💾 Simpan / 📂 Muat Pekerjaan")
    st.download_button("💾 Unduh Hasil Pekerjaan (.pkl)", data=build_save_bytes(),
                       file_name=f"PKLNPRT_Cirebon_{st.session_state.periode}_{st.session_state.mode}.pkl",
                       use_container_width=True)
    up = st.file_uploader("📂 Muat file simpanan Anda", type=["pkl"])
    if up is not None:
        tag = f"{up.name}_{up.size}"
        if st.session_state.get("_last_loaded") != tag:
            try:
                meta = restore_save(up.read())
                st.session_state["_last_loaded"] = tag
                st.session_state.mode_radio = MODE_LABEL.get(st.session_state.mode, MODE_LABEL["simulasi"])
                st.session_state.periode_sel = st.session_state.periode
                st.session_state.beta_num = float(st.session_state.beta)
                st.success(f"✅ Pekerjaan dimuat (mode: {st.session_state.mode}, "
                           f"disimpan {meta.get('tanggal_simpan', '?')}).")
            except Exception as e:
                st.error(f"❌ File tidak valid: {e}")

    st.divider()
    st.markdown("#### ⚙️ Mode Kerja")
    pilihan = st.radio("Pilih mode", [MODE_LABEL["simulasi"], MODE_LABEL["kosong"]],
                       index=0 if st.session_state.mode == "simulasi" else 1,
                       key="mode_radio",
                       help="SIMULASI: tabel terisi data contoh untuk belajar. "
                            "TEMPLATE KOSONG: semua tabel nol/kosong, siap diisi data riil.")
    target = "simulasi" if pilihan == MODE_LABEL["simulasi"] else "kosong"
    if target != st.session_state.mode:
        st.warning("⚠️ Ganti mode akan MENGGANTI seluruh isi tabel. Simpan dulu (💾) bila perlu.")
        st.button("✅ Terapkan Perubahan Mode", on_click=apply_mode_cb, args=(target,),
                  use_container_width=True)

    st.divider()
    st.session_state.periode = st.selectbox("Triwulan Estimasi", QUARTERS,
                                            index=QUARTERS.index("2025Q4"), key="periode_sel")
    st.session_state.beta = st.number_input("Balancing Factor Beta (R8)", 0.80, 1.20,
                                            1.0000, 0.0001, key="beta_num")
    st.button("🔄 Reset & Muat Ulang Data (sesuai mode)", on_click=reset_cb,
              use_container_width=True)

# ---------------------------------------------------------------------
# 9. TAB UTAMA
# ---------------------------------------------------------------------
tab_panduan, tab_wb1, tab_wb2, tab_dash, tab_bps = st.tabs(
    ["📖 Panduan Pemula", "🗂️ Workbook 1: Raw Data SKLNP",
     "🧮 Workbook 2: LK Utama", "📈 Dashboard & QC", "📚 Data BPS & Referensi"])

# ---- TAB PANDUAN ----
with tab_panduan:
    st.header("Panduan Pemula")
    st.markdown(f"**Mode aktif saat ini: {MODE_LABEL[st.session_state.mode]}**")
    st.markdown("""
## 1️⃣ Pilih Mode Kerja (sidebar kiri)
| Mode | Kondisi Tabel | Kapan Dipakai |
|---|---|---|
| 🎮 **Simulasi** | Terisi data contoh berbasis rilis resmi BPS | Belajar alur, demo, uji kewajaran |
| 📄 **Template Kosong** | Semua nol/kosong | Pekerjaan estimasi sungguhan (input dari Dashboard LNPRT) |

> Mode bisa diganti kapan saja. Data lama akan tergantikan — **unduh dulu lewat 💾** bila ingin disimpan.

## 2️⃣ Alur Pengisian
| Langkah | Aktivitas | Tempat |
|---|---|---|
| 1 | Salin raw data SKLNPRT dari dashboard LNPRT | Tab 2 → D0 (pakai tombol ➕ untuk menambah baris) |
| 2 | Isi populasi lembaga (Podes/Kemenag/KPU/Bakesbangpol) | Tab 2 → D2 |
| 3 | Isi deflator IHK 2025=100 (bisa diketik langsung) | Tab 2 → D4 |
| 4 | Lihat rata-rata & agregat (otomatis, anti DIV/0!) | Tab 2 → D1/D3 |
| 5 | Isi rilis 2010=100 (untuk backcasting) | Tab 3 → E0 |
| 6 | Isi benchmark SUT 2025 (Theta) | Tab 3 → E2 |
| 7 | Isi 4 adjustment (Kurban, Zakat, Bencana, Pilkada) | Tab 3 → Adj |
| 8 | Isi indikator administratif & narasi fenomena | Tab 3 → I6/F7 |
| 9 | Baca hasil final, QC 15 poin, lalu ekspor Excel | Tab 4 |
    """)

# ---- TAB WORKBOOK 1 ----
with tab_wb1:
    st.header("Workbook 1 — Mapping Raw Data SKLNP")
    s1, s2, s3, s4 = st.tabs(["D0 · Raw Data 4.A", "D2 · Populasi",
                              "D4 · Setting IHK", "D1/D3 · Hasil"])
    with s1:
        q_pilih = st.selectbox("Pilih triwulan survei", Q_SURVEI,
                               index=len(Q_SURVEI) - 1, key="q_raw")
        with st.expander("➕ Tambah baris sampel kosong",
                         expanded=(st.session_state.mode == "kosong")):
            c1, c2, c3 = st.columns(3)
            q_baru = c1.selectbox("Triwulan", Q_SURVEI, key="q_baru")
            lem_baru = c2.selectbox("Lembaga", list(KODE_LEMBAGA.values()), key="lem_baru")
            n_baru = c3.number_input("Jumlah sampel", 1, 500, 10, key="n_baru")
            if st.button("➕ Tambahkan baris kosong"):
                kode_balik = {v: k for k, v in KODE_LEMBAGA.items()}
                base = len(st.session_state.raw)
                rows = []
                for i in range(int(n_baru)):
                    rec = {"triwulan": q_baru, "kode_lembaga": kode_balik[lem_baru],
                           "lembaga": lem_baru, "id_sample": f"CRB-{base + i + 1:05d}"}
                    for c in B4A_COMPONENTS:
                        rec[c] = 0.0
                    rows.append(rec)
                st.session_state.raw = pd.concat(
                    [st.session_state.raw, pd.DataFrame(rows)], ignore_index=True)
                st.rerun()
        mask = st.session_state.raw["triwulan"] == q_pilih if not st.session_state.raw.empty \
            else pd.Series(dtype=bool)
        view = st.session_state.raw.loc[mask, ["id_sample", "lembaga"] + B4A_COMPONENTS] \
            if not st.session_state.raw.empty else \
            pd.DataFrame(columns=["id_sample", "lembaga"] + B4A_COMPONENTS)
        edited = st.data_editor(view, num_rows="dynamic", use_container_width=True,
                                key=f"raw_{q_pilih}_ed")
        if st.button(f"💾 Simpan perubahan raw data {q_pilih}"):
            other = st.session_state.raw.loc[~mask] if not st.session_state.raw.empty \
                else st.session_state.raw
            upd = edited.copy()
            upd["triwulan"] = q_pilih
            upd["kode_lembaga"] = upd["lembaga"].map({v: k for k, v in KODE_LEMBAGA.items()})
            st.session_state.raw = pd.concat([other, upd], ignore_index=True)
            st.success("Raw data diperbarui — semua hitungan ikut berubah.")
    with s2:
        st.session_state.populasi = st.data_editor(
            st.session_state.populasi[["Kode", "Lembaga", "Jumlah", "Sumber"]],
            use_container_width=True, key="pop_main_ed",
            column_config={"Jumlah": st.column_config.NumberColumn(min_value=0)})
        st.markdown("**Rincian Lembaga Keagamaan** (totalnya = populasi kode 6)")
        st.session_state.pop_rinci = st.data_editor(
            st.session_state.pop_rinci, use_container_width=True, key="pop_rinci_ed",
            column_config={"Jumlah": st.column_config.NumberColumn(min_value=0)})
    with s3:
        st.caption("IHK 2025=100 — **bisa diketik langsung** (wajib diisi pada mode kosong).")
        st.session_state.ihk = st.data_editor(st.session_state.ihk,
                                              use_container_width=True, key="ihk_ed")
        with st.expander("Lihat pemetaan komponen 4.A → sub-komponen IHK"):
            st.dataframe(pd.DataFrame({"Komponen 4.A": [B4A_LABEL[c] for c in B4A_COMPONENTS],
                                       "Deflator": [IHK_MAP[c] for c in B4A_COMPONENTS]},
                                      index=B4A_COMPONENTS), use_container_width=True)
    with s4:
        R = compute_all()
        tab_r = R["rata"].copy()
        if not tab_r.empty:
            tab_r["lembaga"] = tab_r["kode_lembaga"].map(SHORT)
            st.dataframe(tab_r[["triwulan", "lembaga", "n_sampel",
                                "rata_adhb", "rata_adhk"]].round(0), use_container_width=True)
        else:
            st.info("Belum ada data survei. Tambahkan lewat tombol ➕ di D0.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Agregat ADHB (juta Rp)**")
            st.dataframe(R["agg_adhb"].round(2), use_container_width=True)
        with c2:
            st.markdown("**Agregat ADHK (juta Rp)**")
            st.dataframe(R["agg_adhk"].round(2), use_container_width=True)

# ---- TAB WORKBOOK 2 ----
with tab_wb2:
    R = compute_all()
    st.header("Workbook 2 — LK Utama PKLNPRT")
    t1, t2, t3, t4, t5, t6 = st.tabs(
        ["E0 · Rilis 2010=100", "E1 · Backcasting", "E2/E3 · Theta & Nominal",
         "E4/E5 · Deflator & Real", "Adj · 4 Matriks", "I6/F7/R8-R10"])
    with t1:
        st.caption("Rilis 2010=100 (juta Rp) — **bisa diketik langsung** "
                   "(mode kosong: salin dari BRS BPS daerah Anda).")
        st.markdown("**ADHB Rilis**")
        st.session_state.rilis_adhb = st.data_editor(st.session_state.rilis_adhb,
                                                     use_container_width=True, key="rilis_h_ed")
        st.markdown("**ADHK Rilis**")
        st.session_state.rilis_adhk = st.data_editor(st.session_state.rilis_adhk,
                                                     use_container_width=True, key="rilis_k_ed")
        st.markdown("**IPD = ADHB/ADHK × 100 (otomatis)**")
        st.dataframe(R["ipd"].round(2), use_container_width=True)
    with t2:
        st.caption("2023Q1–2025Q4 dari Workbook 1; 2019Q1–2022Q4 di-backcast "
                   "dengan rasio rilis: Nilai(t-1) = Nilai(t) × Rilis(t-1)/Rilis(t).")
        st.dataframe(R["e1_adhb"].round(2), use_container_width=True)
    with t3:
        st.session_state.sut = st.data_editor(st.session_state.sut,
                                              use_container_width=True, key="sut_ed")
        R = compute_all()
        st.dataframe(R["theta"], use_container_width=True)
        st.markdown("**E3 · PKLNPRT Nominal Inisial = Theta × ADHB (juta Rp)**")
        st.dataframe(R["nom_in"].round(2), use_container_width=True)
    with t4:
        st.line_chart(R["defl"])
        st.dataframe(R["defl"].round(3).to_frame("Deflator"), use_container_width=True)
        st.markdown("**E5 · PKLNPRT Real Inisial = Nominal/Deflator × 100 (juta Rp)**")
        st.dataframe(R["real_in"].round(2), use_container_width=True)
    with t5:
        with st.expander("🧮 Kalkulator Adj. Kurban (10% biaya pengelolaan)"):
            c1, c2, c3 = st.columns(3)
            n_sapi = c1.number_input("Jumlah Sapi", 0, 100000, 4200)
            n_kamb = c2.number_input("Jumlah Kambing", 0, 100000, 9800)
            h_sapi = c3.number_input("Harga Sapi (juta Rp)", 0.0, 100.0, 17.5, 0.5)
            c4, c5, _ = st.columns(3)
            h_kamb = c4.number_input("Harga Kambing (juta Rp)", 0.0, 50.0, 2.8, 0.1)
            rasio = c5.number_input("Rasio Operasional", 0.0, 1.0, 0.10, 0.01)
            nilai = (n_sapi * h_sapi + n_kamb * h_kamb) * rasio
            st.metric("Nilai Kurban (juta Rp)", f"{nilai:,.1f}")
            if st.button("Terapkan ke matriks Kurban (triwulan berjalan)"):
                st.session_state.adj_kurban.loc[st.session_state.periode,
                                                "Lemb. Keagamaan"] = round(nilai, 2)
                st.rerun()
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**Adj. Kurban**")
            st.session_state.adj_kurban = st.data_editor(
                st.session_state.adj_kurban, use_container_width=True, key="adj_k_ed")
            st.markdown("**Adj. Zakat (BAZNAS)**")
            st.session_state.adj_zakat = st.data_editor(
                st.session_state.adj_zakat, use_container_width=True, key="adj_z_ed")
        with a2:
            st.markdown("**Adj. Bencana (PMI/BAZNAS/NGO)**")
            st.session_state.adj_bencana = st.data_editor(
                st.session_state.adj_bencana, use_container_width=True, key="adj_b_ed")
            st.markdown("**Adj. Pilkada/Caleg**")
            st.session_state.adj_pilkada = st.data_editor(
                st.session_state.adj_pilkada, use_container_width=True, key="adj_p_ed")
    with t6:
        st.markdown("**I6 · Indikator Data Administratif (bisa diketik langsung)**")
        st.session_state.indikator = st.data_editor(st.session_state.indikator,
                                                    use_container_width=True, key="indikator_ed")
        st.markdown("**F7 · Fenomena Kualitatif Triwulan Berjalan**")
        for kode in ["1", "2", "3", "4", "5", "6", "0"]:
            st.session_state.fenomena[kode] = st.text_area(
                f"Fenomena {KODE_LEMBAGA.get(kode, 'Total')}",
                st.session_state.fenomena.get(kode, ""), height=70, key=f"fen_{kode}")
        R = compute_all()
        st.markdown(f"**R9 · ADHB Final (Beta = {st.session_state.beta:.4f})**")
        st.dataframe(R["adhb_f"].round(2), use_container_width=True)
        st.markdown("**R10 · ADHK Final**")
        st.dataframe(R["adhk_f"].round(2), use_container_width=True)

# ---- TAB DASHBOARD ----
with tab_dash:
    R = compute_all()
    st.header("Dashboard & Quality Control")
    st.caption(f"Mode aktif: **{MODE_LABEL[st.session_state.mode]}**")
    c1, c2, c3, c4 = st.columns(4)
    tot_h = float(R["adhb_f"].loc[st.session_state.periode].sum())
    tot_k = float(R["adhk_f"].loc[st.session_state.periode].sum())
    qtq = clean_pct(growth_qtq(R["adhb_f"].sum(axis=1)).loc[st.session_state.periode])
    yoyv = clean_pct(growth_yoy(R["adhb_f"].sum(axis=1)).loc[st.session_state.periode])
    c1.metric(f"Total ADHB {st.session_state.periode}", f"{tot_h:,.1f} jt Rp")
    c2.metric(f"Total ADHK {st.session_state.periode}", f"{tot_k:,.1f} jt Rp")
    c3.metric("Pertumbuhan Q-to-Q", f"{qtq:,.2f}%")
    c4.metric("Pertumbuhan Y-on-Y", f"{yoyv:,.2f}%")
    st.subheader("📈 Tren ADHB Final per Lembaga")
    st.line_chart(R["adhb_f"])
    st.subheader("🥧 Distribusi COPNI (triwulan berjalan)")
    st.bar_chart(R["copni"].loc[st.session_state.periode, list(COPNI_MAP.keys())])
    with st.expander("Tabel A11 · COPNI"):
        st.dataframe(R["copni"].round(2), use_container_width=True)
    st.subheader("✅ Quality Control (15 Poin)")
    st.dataframe(R["qc"], use_container_width=True, hide_index=True)
    st.subheader("⬇️ Ekspor Excel Multi-Sheet")
    st.download_button("📥 Download LK PKLNPRT Kab. Cirebon.xlsx",
                       data=export_excel(R),
                       file_name=f"LK_PKLNPRT_KabCirebon_{st.session_state.periode}_"
                                 f"{st.session_state.mode}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)

# ---- TAB DATA BPS ----
with tab_bps:
    st.header("📚 Data BPS & Referensi Resmi")
    st.info("Mode **Simulasi** menggunakan seri rilis resmi dari template LK BPS yang "
            "diskalakan ke Kab. Cirebon (proporsi penduduk ±4,7%). Mode **Template Kosong** "
            "menyerahkan seluruh angka kepada Anda — rujuk portal berikut:")
    for nama, url in PORTAL_LINKS.items():
        st.markdown(f"- [{nama}]({url})")
    st.markdown("### 📋 Indikator Kunci Kabupaten Cirebon (jangkar simulasi)")
    st.dataframe(DATA_BPS, use_container_width=True, hide_index=True)
    st.markdown("### 📈 Seri Rilis Agregat BPS (2010=100, juta Rp) — dari template resmi")
    rilis_df = pd.DataFrame({"Triwulan": QUARTERS, "ADHB": RILIS_JABAR_ADHB,
                             "ADHK": RILIS_JABAR_ADHK})
    rilis_df["IPD"] = (rilis_df["ADHB"] / rilis_df["ADHK"] * 100).round(2)
    st.dataframe(rilis_df, use_container_width=True, hide_index=True)
    st.line_chart(rilis_df.set_index("Triwulan")[["ADHB", "ADHK"]])

st.caption("© LK PKLNPRT Rebasing 2025=100 — struktur mengikuti template resmi BPS "
           "(00. Mapping Raw Data & 01. LK PKLNPRT Regional).")