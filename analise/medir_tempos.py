"""Dois tempos do teste medidos nas demos.

1) LIMITE POR ALVO. Reextrai os duelos com janela de 4 s e mede, com a mesma conta dos pesos
   (curva do inimigo por situacao e tipo, valor = f(t) x t), quanto do valor total dos duelos
   acontece depois de 1,5 / 2 / 2,5 / 3 s. O limite certo e o ponto a partir do qual o resto
   do valor e desprezivel: depois dele, ser mais rapido nao muda duelo.
2) ESPERA ENTRE ALVOS. Para cada duelo, o tempo desde a tua kill anterior. Compara o teu
   tempo ate o primeiro dano quando o inimigo aparece logo depois de uma kill (refratario:
   o cerebro ainda esta fechando a acao anterior) com os duelos isolados, dentro da mesma
   situacao (razao das medianas).

Uso: python medir_tempos.py <pasta_das_demos> <saida.json>
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import extrair_duelos as ed  # noqa: E402
from perfil import densidade, estrato, kaplan_meier  # noqa: E402
from demoparser2 import DemoParser  # noqa: E402


def valores(df, janela):
    def evento(r):
        if r["tipo"] == "frente":
            if pd.notna(r["ttd_ele"]):
                return r["ttd_ele"], 1
            fim = janela
            if pd.notna(r["t_kill"]):
                fim = min(fim, r["t_kill"])
            if pd.notna(r["visao_s"]):
                fim = min(fim, r["visao_s"] + 0.25)
            return fim, 0
        if pd.notna(r["t_morte"]):
            return r["t_morte"], 1
        return (janela if pd.isna(r["t_kill"]) else min(janela, r["t_kill"])), 0
    ev = [evento(r) for r in df.to_dict("records")]
    d = df.assign(t_ini=[e[0] for e in ev], ev_ini=[e[1] for e in ev])
    dens = {}
    for chave, g in d.groupby(["estrato", "tipo"]):
        st, sj, _ = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
        tt = g.loc[g["ev_ini"] == 1, "t_ini"].to_numpy(float)
        banda = max(0.03, 1.06 * np.std(tt) * len(tt) ** (-1 / 5)) if len(tt) > 5 else 0.15
        dens[chave] = densidade(st, sj, banda) if len(st) else (lambda x: np.zeros(1))
    v, t_meu = [], []
    for r in d.to_dict("records"):
        t = r["ttd_eu"] if pd.notna(r["ttd_eu"]) else (r["tiro_nele"] if pd.notna(r["tiro_nele"]) else r["t_ini"])
        t = max(float(t), 1 / 64)
        v.append(float(dens[(r["estrato"], r["tipo"])](t)[0]) * t)
        t_meu.append(t)
    return np.array(v), np.array(t_meu)


def main():
    pasta, saida = sys.argv[1:3]
    out = {}
    # ---- 1) limite por alvo: duelos com janela de 4 s ----
    ed.JANELA = int(4.0 * ed.TICK)
    ed.TRAJ_TICKS = 2           # caminho nao interessa aqui
    import glob
    demos = sorted(glob.glob(os.path.join(pasta, "match730_*.dem")), key=os.path.getmtime)
    todos = []
    for i, dm in enumerate(demos):
        todos.extend(ed.processar(dm, i))
    df = pd.DataFrame(todos)
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    df["estrato"] = [estrato(r) for r in df.to_dict("records")]
    v, tm = valores(df, 4.0)
    tot = v.sum()
    print(f"duelos com janela de 4 s: {len(df)}")
    lin = {}
    for L in (1.0, 1.5, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5):
        frac = float(v[tm > L].sum() / tot)
        lin[str(L)] = frac
        print(f"  valor dos duelos depois de {L:4.2f} s: {100 * frac:5.2f}%")
    out["valor_depois_de"] = lin
    # tempo em que o valor que sobra cai abaixo de 1% e 0,5%
    ts = np.linspace(0.5, 4.0, 701)
    resto = np.array([v[tm > L].sum() / tot for L in ts])
    for alvo in (0.02, 0.01, 0.005):
        L = float(ts[np.argmax(resto <= alvo)]) if (resto <= alvo).any() else None
        out[f"limite_resto_{alvo}"] = L
        print(f"  valor que sobra cai abaixo de {100 * alvo:.1f}% em {L} s")
    # ---- 2) espera entre alvos: tempo desde a tua kill anterior ----
    ed.JANELA = int(2.5 * ed.TICK)
    dd = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "duelos.json"), encoding="utf-8"))
    du = pd.DataFrame(dd["duelos"])
    du = du[~du["sem_mira"] & ~du["luneta"] & ~du["franco"]].reset_index(drop=True)
    du["estrato"] = [estrato(r) for r in du.to_dict("records")]
    arq = {f["id"]: f["arquivo"] for f in dd["demos"]}
    gap = np.full(len(du), np.nan)
    for i_demo, g in du.groupby("demo"):
        p = DemoParser(os.path.join(pasta, arq[i_demo]))
        mo = p.parse_event("player_death")
        mo["attacker_steamid"] = mo["attacker_steamid"].map(ed.sid)
        kills = np.sort(mo.loc[mo["attacker_steamid"] == ed.EU, "tick"].to_numpy(int))
        for idx, r in g.iterrows():
            ant = kills[kills < r["t0"]]
            if len(ant):
                gap[idx] = (r["t0"] - ant[-1]) / ed.TICK
    du["gap"] = gap
    du["t"] = du["ttd_eu"]
    base = du[(du["gap"].isna() | (du["gap"] > 3)) & du["t"].notna()]
    med_base = base.groupby("estrato")["t"].median()
    linhas = {}
    print("\nteu tempo ate o 1o dano logo depois de uma kill / duelos isolados (mesma situacao):")
    for lo, hi in ((0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 3.0)):
        s = du[(du["gap"] >= lo) & (du["gap"] < hi) & du["t"].notna()]
        if len(s) < 3:
            continue
        razao = (s["t"] / s["estrato"].map(med_base)).median()
        linhas[f"{lo}-{hi}"] = {"n": int(len(s)), "razao_mediana": round(float(razao), 3)}
        print(f"  inimigo aparecendo {lo:.1f}-{hi:.1f} s depois da kill: n={len(s):3d}  tempo x{razao:.2f} do isolado")
    out["espera"] = linhas
    out["gap_quantis_s"] = np.round(np.nanquantile(gap, [0.05, 0.1, 0.25, 0.5]), 2).tolist()
    print("tempo desde a kill anterior (quantis 5/10/25/50%):", out["gap_quantis_s"])
    json.dump(out, open(saida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
