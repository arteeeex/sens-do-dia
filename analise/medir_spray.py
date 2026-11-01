"""Quanto spray e tracking existe de fato nos teus duelos, e se da para medir o recuo das armas.

Para cada duelo de duelos.json: teus tiros nos 2,5 s (fire_bullets), rajadas (tiros a
menos de 0,2 s um do outro), acertos nele, se a kill foi de cabeca e com quantos tiros.
Tambem mede o recuo efetivo (direcao do tiro menos direcao da mira no mesmo tick) por
indice de recuo, por arma, para ver se o padrao do CS2 pode ser copiado das demos.

Uso: python medir_spray.py <pasta_das_demos> <duelos.json> <saida.json>
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I tira a pasta do script do caminho
from meu_id import meu_steamid  # noqa: E402

EU = meu_steamid()      # teu SteamID64, de analise/meu_steamid.txt (fora do git)
TICK = 64
JANELA = int(2.5 * TICK)


def sid(v):
    if v is None:
        return 0
    s = str(v).strip().split(".")[0]
    return int(s) if s.isdigit() else 0


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def main():
    pasta, duelos_p, saida = sys.argv[1:4]
    dd = json.load(open(duelos_p, encoding="utf-8"))
    duelos = pd.DataFrame(dd["duelos"])
    duelos = duelos[~duelos["sem_mira"] & ~duelos["luneta"] & ~duelos["franco"]]
    arquivos = {f["id"]: f["arquivo"] for f in dd["demos"]}
    linhas = []
    recuo = []
    for id_demo, grupo in duelos.groupby("demo"):
        p = DemoParser(os.path.join(pasta, arquivos[id_demo]))
        fb = p.parse_event("fire_bullets")
        fb["user_steamid"] = fb["user_steamid"].map(sid)
        hu = p.parse_event("player_hurt")
        for c in ("attacker_steamid", "user_steamid"):
            hu[c] = hu[c].map(sid)
        mo = p.parse_event("player_death")
        for c in ("attacker_steamid", "user_steamid"):
            mo[c] = mo[c].map(sid)
        meus = fb[fb["user_steamid"] == EU].sort_values("tick")
        tk = p.parse_ticks(["pitch", "yaw"], players=[EU]) if False else p.parse_ticks(["pitch", "yaw"])
        tk["steamid"] = tk["steamid"].astype("int64")
        eu_tk = tk[tk["steamid"] == EU].set_index("tick")
        # recuo efetivo por indice, so dos teus tiros
        for _, r in meus.iterrows():
            t = int(r["tick"])
            if t not in eu_tk.index:
                continue
            q = eu_tk.loc[t]
            recuo.append({"arma": int(r["item_def_index"]), "idx": float(r["recoil_index"]),
                          "dp": float(r["angles_x"] - q["pitch"]), "dy": float(wrap180(r["angles_y"] - q["yaw"])),
                          "inac": float(r["inaccuracy"]), "spread": float(r["spread"])})
        for d in grupo.to_dict("records"):
            t0 = d["t0"]
            t1 = t0 + JANELA
            e = int(d["inimigo"])
            k = mo[(mo["attacker_steamid"] == EU) & (mo["user_steamid"] == e) & (mo["tick"] >= t0) & (mo["tick"] <= t1)]
            fim = int(k["tick"].min()) if len(k) else t1
            tiros = meus[(meus["tick"] >= t0) & (meus["tick"] <= fim)]["tick"].to_numpy()
            acertos = hu[(hu["attacker_steamid"] == EU) & (hu["user_steamid"] == e) & (hu["tick"] >= t0) & (hu["tick"] <= fim)]
            rajada = 0
            if len(tiros):
                gaps = np.diff(tiros) / TICK
                corrida, melhor = 1, 1
                for g in gaps:
                    corrida = corrida + 1 if g <= 0.2 else 1
                    melhor = max(melhor, corrida)
                rajada = melhor
            linhas.append({
                "estrato": None, "arma": d["arma"], "theta": d["theta"], "vel": d["vel"], "tipo": d["tipo"],
                "tiros": int(len(tiros)), "maior_rajada": int(rajada), "acertos": int(len(acertos)),
                "matou": bool(len(k)), "kill_hs": bool(k["headshot"].iloc[0]) if len(k) else None,
                "tiros_ate_kill": int(len(tiros)) if len(k) else None,
                "duracao_tiros": float((tiros[-1] - tiros[0]) / TICK) if len(tiros) > 1 else 0.0,
            })
        print(f"demo {id_demo}: {len(grupo)} duelos")
    df = pd.DataFrame(linhas)
    rc = pd.DataFrame(recuo)
    out = {}
    k = df[df["matou"]]
    out["duelos"] = int(len(df))
    out["kills"] = int(len(k))
    out["kill_de_cabeca"] = float(k["kill_hs"].mean())
    out["tiros_ate_kill_quantis"] = k["tiros_ate_kill"].quantile([0.25, 0.5, 0.75, 0.9]).tolist()
    out["kills_com_1_tiro"] = float((k["tiros_ate_kill"] == 1).mean())
    out["kills_com_ate_2_tiros"] = float((k["tiros_ate_kill"] <= 2).mean())
    out["kills_com_3+_tiros"] = float((k["tiros_ate_kill"] >= 3).mean())
    out["kills_com_rajada_5+"] = float((k["maior_rajada"] >= 5).mean())
    out["duelos_com_rajada_5+"] = float((df["maior_rajada"] >= 5).mean())
    out["duelos_com_rajada_3+"] = float((df["maior_rajada"] >= 3).mean())
    rifles = df[df["arma"].isin(["AK-47", "M4A4", "M4A1-S", "Galil AR", "FAMAS", "SG 553", "AUG"])]
    kr = rifles[rifles["matou"]]
    out["rifle"] = {"duelos": int(len(rifles)), "kills": int(len(kr)),
                    "kill_de_cabeca": float(kr["kill_hs"].mean()),
                    "kills_com_3+_tiros": float((kr["tiros_ate_kill"] >= 3).mean()),
                    "duelos_com_rajada_5+": float((rifles["maior_rajada"] >= 5).mean())}
    rapido = df[pd.to_numeric(df["vel"], errors="coerce") >= 20]
    out["alvo_rapido"] = {"duelos": int(len(rapido)), "rajada_5+": float((rapido["maior_rajada"] >= 5).mean())}
    # padrao de recuo da AK-47 (item_def_index 7) por indice inteiro
    ak = rc[rc["arma"] == 7].copy()
    ak["i"] = ak["idx"].round().astype(int)
    tab = ak.groupby("i").agg(n=("dp", "size"), dp=("dp", "median"), dy=("dy", "median"),
                              dp_dp=("dp", lambda s: float(s.quantile(0.75) - s.quantile(0.25))),
                              inac=("inac", "median")).reset_index()
    out["ak_recuo_por_indice"] = tab[tab["n"] >= 5].round(3).to_dict("records")
    print(json.dumps({k2: v for k2, v in out.items() if k2 != "ak_recuo_por_indice"}, indent=1, ensure_ascii=False))
    print("AK-47 recuo (indice, n, dpitch, dyaw, inacuracia):")
    for r in out["ak_recuo_por_indice"][:16]:
        print(f"  {r['i']:2d} n={r['n']:4d} dp={r['dp']:+.2f} dy={r['dy']:+.2f} iqr={r['dp_dp']:.2f} inac={r['inac']:.4f}")
    json.dump(out, open(saida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
