"""Mede o tamanho da hitbox da cabeca no CS2 pelos tiros que acertaram a cabeca nas demos.

Para cada bala que deu dano (bullet_damage), pega a linha do tiro (origem do olho do
atirador em fire_bullets + direcao da bala em damage_dir) e mede a que distancia ela
passou do ponto do olho da vitima, no plano perpendicular ao tiro.

O servidor registra o acerto numa posicao de alguns milissegundos antes (lag
compensation), entao so entram vitimas que estavam paradas (< 10 u/s) e em pe
(duck = 0) durante os 16 ticks (250 ms) anteriores: assim a posicao da demo e a mesma
que o servidor usou.

Uso: python medir_cabeca.py <pasta_das_demos> <saida.json>
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OLHO_PE = 63.6
HIST = 16


def sid(v):
    """SteamID64 sem passar por float (float perde os ultimos digitos)."""
    if v is None:
        return 0
    s = str(v).strip().split(".")[0]
    return int(s) if s.isdigit() else 0


def main():
    pasta, saida = sys.argv[1], sys.argv[2]
    demos = sorted(glob.glob(os.path.join(pasta, "match730_*.dem")))
    linhas = []
    for d in demos:
        p = DemoParser(d)
        tk = p.parse_ticks(["X", "Y", "Z", "yaw", "duck_amount", "velocity_X", "velocity_Y", "velocity_Z"])
        tk["steamid"] = tk["steamid"].astype("int64")
        tk["vh"] = np.hypot(tk["velocity_X"], tk["velocity_Y"])
        tk = tk.sort_values(["steamid", "tick"])
        # max de velocidade e de duck nos HIST ticks anteriores (inclusive o atual)
        tk["vh_max"] = tk.groupby("steamid")["vh"].transform(lambda s: s.rolling(HIST + 1, min_periods=1).max())
        tk["vz_max"] = tk.groupby("steamid")["velocity_Z"].transform(lambda s: s.abs().rolling(HIST + 1, min_periods=1).max())
        tk["duck_max"] = tk.groupby("steamid")["duck_amount"].transform(lambda s: s.rolling(HIST + 1, min_periods=1).max())
        tk["duck_min"] = tk.groupby("steamid")["duck_amount"].transform(lambda s: s.rolling(HIST + 1, min_periods=1).min())
        tk = tk.set_index(["tick", "steamid"])
        bd = p.parse_event("bullet_damage")
        hu = p.parse_event("player_hurt")
        fb = p.parse_event("fire_bullets")
        for e in (bd, hu, fb):
            for c in ("attacker_steamid", "user_steamid", "victim_steamid"):
                if c in e.columns:
                    e[c] = e[c].map(sid).astype("int64")
        hu = hu.drop_duplicates(["tick", "attacker_steamid", "user_steamid"])
        hg = hu.set_index(["tick", "attacker_steamid", "user_steamid"])["hitgroup"]
        fbo = fb.drop_duplicates(["tick", "user_steamid"]).set_index(["tick", "user_steamid"])
        n0 = len(linhas)
        for _, r in bd.iterrows():
            t, a, v = int(r["tick"]), int(r["attacker_steamid"]), int(r["victim_steamid"])
            if (t, a, v) not in hg.index or (t, a) not in fbo.index or (t, v) not in tk.index:
                continue
            q = tk.loc[(t, v)]
            if q["vh_max"] > 10 or q["vz_max"] > 5:
                continue
            if q["duck_max"] == 0.0:
                altura = OLHO_PE
            elif q["duck_min"] >= 1.0:
                altura = OLHO_PE - 18.0   # agachado o tempo todo
            else:
                continue
            o = fbo.loc[(t, a)]
            origem = np.array([o["origin_x"], o["origin_y"], o["origin_z"]], dtype=float)
            u = np.array([r["damage_dir_x"], r["damage_dir_y"], r["damage_dir_z"]], dtype=float)
            nu = np.linalg.norm(u)
            if nu < 0.5:
                continue
            u /= nu
            olho = np.array([q["X"], q["Y"], q["Z"] + altura], dtype=float)
            w = olho - origem
            s = float(np.dot(w, u))
            if s < 32:
                continue
            perp = w - s * u
            lado = np.cross(u, [0.0, 0.0, 1.0])
            nl = np.linalg.norm(lado)
            if nl < 1e-3:
                continue
            lado /= nl
            cima = np.cross(lado, u)
            yb = np.arctan2(u[1], u[0])
            yv = np.radians(q["yaw"])
            linhas.append({"grupo": str(hg.loc[(t, a, v)]),
                           "lateral": float(np.dot(perp, lado)),
                           "vertical": -float(np.dot(perp, cima)),  # + = bala acima do olho
                           "sen_rel": float(np.sin(yb - yv)),        # olho fica a frente do centro
                           "cos_rel": float(np.cos(yb - yv)),
                           "dist": s})
        print(f"{os.path.basename(d)}: +{len(linhas) - n0} balas")
    df = pd.DataFrame(linhas)
    q = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975, 0.99]
    res = {"filtro": "vitima parada (<10 u/s) e em pe nos 250 ms anteriores"}
    for g in ["head", "neck", "chest"]:
        s = df[df["grupo"] == g]
        res[g] = {"n": int(len(s)),
                  "lateral": dict(zip(map(str, q), s["lateral"].quantile(q).round(2).tolist())),
                  "vertical_rel_olho": dict(zip(map(str, q), s["vertical"].quantile(q).round(2).tolist()))}
    # Tamanho efetivo: se os acertos cobrissem a cabeca por igual (disco uniforme), 95% deles
    # ficariam dentro de 0,80 do raio. Como a mira concentra os acertos no centro, isso e um
    # limite de baixo para o raio; o ruido de posicao que sobrou (<2 u) puxa para cima.
    cab = df[df["grupo"] == "head"].copy()
    # lateral = f * sen(angulo entre a bala e pra onde a vitima olha) + posicao do acerto na cabeca
    A = np.column_stack([np.ones(len(cab)), cab["sen_rel"].to_numpy()])
    coef, *_ = np.linalg.lstsq(A, cab["lateral"].to_numpy(), rcond=None)
    cab["lat_corr"] = cab["lateral"] - A @ coef
    c_ver = float(cab["vertical"].median())
    lat_q = cab["lat_corr"].abs().quantile([0.5, 0.75, 0.9, 0.95]).round(2).tolist()
    ver_q = (cab["vertical"] - c_ver).abs().quantile([0.5, 0.75, 0.9, 0.95]).round(2).tolist()
    r_lat = float(cab["lat_corr"].abs().quantile(0.95) / 0.80)
    r_ver = float((cab["vertical"] - c_ver).abs().quantile(0.95) / 0.80)
    res["modelo"] = {"olho_a_frente_do_centro": round(float(coef[1]), 2),
                     "centro_abaixo_do_olho": round(-c_ver, 2),
                     "lateral_abs_quantis_50_75_90_95": lat_q,
                     "vertical_abs_quantis_50_75_90_95": ver_q,
                     "meia_largura": round(r_lat, 2), "meia_altura": round(r_ver, 2), "n": int(len(cab))}
    print(json.dumps(res["modelo"], indent=1))
    print("head lateral:", res["head"]["lateral"])
    print("head vertical:", res["head"]["vertical_rel_olho"])
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
