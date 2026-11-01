"""Dano real da AK-47 por parte do corpo, com e sem colete, medido nas demos.

Usa todo player_hurt de AK-47 (de qualquer jogador) para conferir a conta do CS2:
    dano = 36 x multiplicador da parte x 0,98^(distancia/500)
    com colete na parte protegida: vida perde dano x 0,775 (arredondado para baixo)
e, so dos teus duelos de rifle, quantos acertos e quanto tempo a kill levou depois do
primeiro acerto (para comparar com o teste, onde nao tem recuo).

Uso: python medir_dano.py <pasta_das_demos> <duelos.json> <saida.json>
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
BASE_AK = 36.0
FALLOFF = 0.98
RIFLES = ("ak47", "m4a1", "m4a1_silencer", "m4a1_silencer_off", "galilar", "famas", "sg556", "aug")


def sid(v):
    if v is None:
        return 0
    s = str(v).strip().split(".")[0]
    return int(s) if s.isdigit() else 0


def main():
    pasta, duelos_p, saida = sys.argv[1:4]
    dd = json.load(open(duelos_p, encoding="utf-8"))
    arquivos = {f["id"]: f["arquivo"] for f in dd["demos"]}
    duelos = pd.DataFrame(dd["duelos"])
    duelos = duelos[~duelos["sem_mira"] & ~duelos["luneta"] & ~duelos["franco"]]

    todos = []          # todo acerto de AK de qualquer jogador
    meus = []           # teus duelos de rifle: sequencia de acertos ate a kill
    for id_demo, arq in arquivos.items():
        p = DemoParser(os.path.join(pasta, arq))
        h = p.parse_event("player_hurt", player=["X", "Y", "Z", "armor_value", "has_helmet"])
        for c in ("attacker_steamid", "user_steamid"):
            h[c] = h[c].map(sid)
        mo = p.parse_event("player_death")
        for c in ("attacker_steamid", "user_steamid"):
            mo[c] = mo[c].map(sid)
        d = np.sqrt((h["attacker_X"] - h["user_X"]) ** 2 + (h["attacker_Y"] - h["user_Y"]) ** 2
                    + ((h["attacker_Z"] + 64) - (h["user_Z"] + 40)) ** 2)
        h["dist"] = d
        h["armor_antes"] = h["armor"] + h["dmg_armor"]
        h["vida_antes"] = h["health"] + h["dmg_health"]
        ak = h[h["weapon"] == "ak47"]
        todos.append(ak[["hitgroup", "dist", "armor_antes", "user_has_helmet", "dmg_health", "dmg_armor",
                         "health", "vida_antes", "attacker_steamid"]])
        # teus duelos de rifle
        g = duelos[duelos["demo"] == id_demo]
        for r in g.to_dict("records"):
            t0, t1, e = r["t0"], r["t0"] + JANELA, int(r["inimigo"])
            ac = h[(h["attacker_steamid"] == EU) & (h["user_steamid"] == e) & (h["tick"] >= t0) & (h["tick"] <= t1)].sort_values("tick")
            if not len(ac) or not any(w in str(ac["weapon"].iloc[0]) for w in RIFLES):
                continue
            k = mo[(mo["attacker_steamid"] == EU) & (mo["user_steamid"] == e) & (mo["tick"] >= t0) & (mo["tick"] <= t1)]
            t_kill = int(k["tick"].min()) if len(k) else None
            ate = ac if t_kill is None else ac[ac["tick"] <= t_kill]
            meus.append({
                "arma": str(ac["weapon"].iloc[0]), "dist": float(ac["dist"].iloc[0]),
                "colete": bool(ac["armor_antes"].iloc[0] > 0), "capacete": bool(ac["user_has_helmet"].iloc[0]),
                "vida_antes": int(ac["vida_antes"].iloc[0]),
                "grupos": ate["hitgroup"].tolist(),
                "primeiro": str(ac["hitgroup"].iloc[0]),
                "matou": t_kill is not None,
                "kill_hs": bool(k["headshot"].iloc[0]) if len(k) else None,
                "ms_1o_acerto_ate_kill": None if t_kill is None else 1000 * (t_kill - int(ac["tick"].iloc[0])) / TICK,
                "acertos_ate_kill": int(len(ate)) if t_kill is not None else None,
            })
        print(f"demo {id_demo}: {len(ak)} acertos de AK, {len(g)} duelos teus")

    A = pd.concat(todos, ignore_index=True)
    A = A[(A["dist"] > 16) & (A["vida_antes"] == 100)]        # vida cheia: o dano nao e cortado
    A["queda"] = FALLOFF ** (A["dist"] / 500)
    A["bruto"] = BASE_AK * A["queda"]
    out = {"acertos_ak_usados": int(len(A))}
    linhas = []
    print("\nAK-47, vida cheia antes do tiro (dano na vida / (36 x 0,98^(d/500))):")
    for (grupo, colete), g in A.groupby(["hitgroup", A["armor_antes"] > 0]):
        if len(g) < 5:
            continue
        mult = (g["dmg_health"] / g["bruto"]).median()
        # conta exata do CS2 com o multiplicador oficial: confere quantos batem no inteiro
        linhas.append({"grupo": grupo, "colete": bool(colete), "n": int(len(g)),
                       "multiplicador_efetivo": round(float(mult), 3),
                       "dano_mediano": float(g["dmg_health"].median()),
                       "dist_mediana": round(float(g["dist"].median()))})
        print(f"  {grupo:10s} colete={'sim' if colete else 'nao':3s} n={len(g):4d}  mult efetivo {mult:5.3f}  "
              f"dano mediano {g['dmg_health'].median():5.1f} a {g['dist'].median():5.0f} u")
    out["por_grupo"] = linhas

    # modelo exato: 36 x M x 0,98^(d/500), colete 0,775 nas partes protegidas, depois para baixo
    M = {"head": 4.0, "neck": 4.0, "chest": 1.0, "stomach": 1.25, "left_arm": 1.0, "right_arm": 1.0,
         "left_leg": 0.75, "right_leg": 0.75, "generic": 1.0}
    protegido = {"head": "capacete", "neck": "capacete", "chest": "colete", "stomach": "colete",
                 "left_arm": "colete", "right_arm": "colete", "generic": "colete"}

    def prever(r, arred):
        dano = BASE_AK * M.get(r["hitgroup"], 1.0) * r["queda"]
        tem = r["armor_antes"] > 0 and (protegido.get(r["hitgroup"]) == "colete" or
                                        (protegido.get(r["hitgroup"]) == "capacete" and r["user_has_helmet"]))
        if tem:
            dano *= 0.775
        return arred(dano)

    for nome, arred in (("para baixo", np.floor), ("arredonda", np.round)):
        pv = np.array([prever(r, arred) for r in A.to_dict("records")])
        bate = np.abs(pv - A["dmg_health"].to_numpy()) <= 1
        exato = pv == A["dmg_health"].to_numpy()
        print(f"  modelo ({nome}): exato {100 * exato.mean():.1f}%, ate 1 de diferenca {100 * bate.mean():.1f}%")
        out[f"modelo_{nome}"] = {"exato": float(exato.mean()), "ate_1": float(bate.mean())}
    # onde o modelo erra, por grupo
    pv = np.array([prever(r, np.floor) for r in A.to_dict("records")])
    A["erro_modelo"] = A["dmg_health"].to_numpy() - pv
    err = A.groupby("hitgroup")["erro_modelo"].agg(["count", "median", lambda s: float((s.abs() <= 1).mean())])
    print(err)

    m = pd.DataFrame(meus)
    out["teus_duelos_de_rifle_com_acerto"] = int(len(m))
    out["inimigo_de_colete"] = float(m["colete"].mean())
    out["inimigo_de_capacete"] = float(m["capacete"].mean())
    out["primeiro_acerto"] = m["primeiro"].value_counts(normalize=True).round(3).to_dict()
    todos_grupos = pd.Series([x for gs in m["grupos"] for x in gs])
    out["todos_teus_acertos"] = todos_grupos.value_counts(normalize=True).round(3).to_dict()
    k = m[m["matou"]]
    out["kills"] = int(len(k))
    out["kill_hs"] = float(k["kill_hs"].mean())
    corpo = k[(k["primeiro"] != "head") & (k["vida_antes"] == 100) & (k["colete"])]
    out["kill_depois_de_1o_acerto_no_corpo_ms"] = corpo["ms_1o_acerto_ate_kill"].quantile([0.25, 0.5, 0.75]).round(0).tolist()
    out["acertos_ate_kill_1o_no_corpo"] = corpo["acertos_ate_kill"].value_counts().sort_index().to_dict()
    out["n_kill_1o_no_corpo"] = int(len(corpo))
    out["primeiro_no_corpo_virou_kill"] = float(m[(m["primeiro"] != "head")]["matou"].mean())
    out["kill_hs_depois_de_1o_no_corpo"] = float(corpo["kill_hs"].mean()) if len(corpo) else None
    print(json.dumps({k2: v for k2, v in out.items() if k2 != "por_grupo"}, indent=1, ensure_ascii=False))
    json.dump(out, open(saida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
