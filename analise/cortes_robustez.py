"""Os cortes das situacoes (1,5 / 4 / 10 / 35 graus e 20 graus/s) importam?

As situacoes so servem para agrupar duelos parecidos: o peso de cada duelo no teste e o peso
da situacao dividido pelo numero de duelos dela. Aqui troco os cortes e vejo quanto a sens
final mudaria:
  - base (1,5 / 4 / 10 / 35 e 20 graus/s);
  - todos os cortes 25% menores e 33% maiores;
  - cortes em TAMANHOS DE CABECA (lei de Fitts: dificuldade = distancia / tamanho do alvo):
    mira dentro de 1 raio da cabeca, 1-3, 3-9, 9-27 raios, virada >= 35 graus; rapido =
    alvo andando 3 raios de cabeca por 100 ms ou mais.
Cada "pessoa" simulada tem o melhor ponto de cada duelo variando suave com o angulo, a
velocidade e o tipo (desvio de 10% em cada efeito) mais 10% so do duelo. Sens do dia =
media dos melhores pontos com o peso de cada duelo. Compara com a base.

Uso: python cortes_robustez.py <duelos.json>
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from perfil import JANELA, densidade, kaplan_meier  # noqa: E402


def classificador(c_fino, c_curto, c_flick, c_virada, c_vel):
    def f(r):
        if r["theta"] >= c_virada:
            return "virada"
        if r["vel"] is not None and r["vel"] >= c_vel:
            return "rapido"
        if r["theta"] < c_fino:
            return "fino"
        if r["theta"] < c_curto:
            return "curto"
        if r["theta"] < c_flick:
            return "flick"
        return "medio"
    return f


def fitts(r):
    raio = np.degrees(np.arctan(5.0 / max(r["dist"], 16)))
    if r["theta"] >= 35:
        return "virada"
    if r["vel"] is not None and r["vel"] * 0.1 >= 3 * raio:
        return "rapido"
    q = r["theta"] / raio
    return "fino" if q < 1 else "curto" if q < 3 else "flick" if q < 9 else "medio"


def tempos(df):
    t_ini, ev, t_eu = [], [], []
    for r in df.to_dict("records"):
        if r["tipo"] == "frente":
            if pd.notna(r["ttd_ele"]):
                a, e = r["ttd_ele"], 1
            else:
                a = JANELA
                if pd.notna(r["t_kill"]):
                    a = min(a, r["t_kill"])
                if pd.notna(r["visao_s"]):
                    a = min(a, r["visao_s"] + 0.25)
                e = 0
        else:
            a, e = (r["t_morte"], 1) if pd.notna(r["t_morte"]) else ((JANELA if pd.isna(r["t_kill"]) else min(JANELA, r["t_kill"])), 0)
        meu = r["ttd_eu"] if pd.notna(r["ttd_eu"]) else (max(r["tiro_nele"], 1 / 64) if pd.notna(r["tiro_nele"]) else a)
        t_ini.append(a)
        ev.append(e)
        t_eu.append(max(float(meu), 1 / 64))
    return np.array(t_ini), np.array(ev), np.array(t_eu)


def peso_por_duelo(df, fn):
    d = df.copy()
    d["estrato"] = [fn(r) for r in d.to_dict("records")]
    t_ini, ev, t_eu = tempos(d)
    d["t_ini"], d["ev_ini"] = t_ini, ev
    bandas = {tp: 1.06 * np.std(g.loc[g["ev_ini"] == 1, "t_ini"]) * (g["ev_ini"] == 1).sum() ** (-1 / 5)
              for tp, g in d.groupby("tipo")}
    dens = {}
    for chave, g in d.groupby(["estrato", "tipo"]):
        st, sj, _ = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
        dens[chave] = densidade(st, sj, bandas[chave[1]]) if len(st) else None
    v = np.array([(float(dens[(r["estrato"], r["tipo"])](t)[0]) * t) if dens[(r["estrato"], r["tipo"])] else 0.0
                  for r, t in zip(d.to_dict("records"), t_eu)])
    W = {e: v[d["estrato"] == e].sum() / v.sum() for e in d["estrato"].unique()}
    n = d["estrato"].value_counts().to_dict()
    e_i = np.array([W[s] / n[s] for s in d["estrato"]])
    return e_i / e_i.sum(), W


def main():
    bruto = json.load(open(sys.argv[1], encoding="utf-8"))
    df = pd.DataFrame(bruto["duelos"])
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    variantes = {
        "base (1,5/4/10/35, 20 graus/s)": classificador(1.5, 4, 10, 35, 20),
        "cortes 25% menores": classificador(1.125, 3, 7.5, 26.25, 15),
        "cortes 33% maiores": classificador(2.0, 5.33, 13.3, 46.7, 26.7),
        "cortes em tamanhos de cabeca (Fitts)": fitts,
    }
    pesos = {k: peso_por_duelo(df, f) for k, f in variantes.items()}
    rng = np.random.default_rng(5)
    M = 20000
    lt = np.log(np.maximum(df["theta"].to_numpy(float), 0.05))
    lv = np.log(np.maximum(pd.to_numeric(df["vel"], errors="coerce").fillna(1).to_numpy(float), 0.5))
    vir = (df["tipo"] == "virada").to_numpy(float)
    z = lambda a: (a - a.mean()) / a.std()
    X = np.stack([z(lt), z(lv), z(vir)], axis=1)
    B = rng.normal(0, 0.10, (M, 3))
    U = B @ X.T + rng.normal(0, 0.10, (M, len(df)))          # melhor ponto de cada duelo (log)
    base = U @ pesos["base (1,5/4/10/35, 20 graus/s)"][0]
    print(f"{'cortes':40s} {'sens muda (tipico)':>19s} {'95% das pessoas':>16s}")
    for k, (e, W) in pesos.items():
        if k.startswith("base"):
            continue
        dx = U @ e - base
        print(f"{k:40s} {100 * (np.exp(np.sqrt(np.mean(dx ** 2))) - 1):18.2f}% {100 * (np.exp(np.quantile(np.abs(dx), 0.95)) - 1):15.2f}%")
    print("\npesos de cada jeito de cortar:")
    for k, (e, W) in pesos.items():
        print(f"  {k:40s} " + "  ".join(f"{s} {100 * w:.1f}%" for s, w in sorted(W.items())))


if __name__ == "__main__":
    main()
