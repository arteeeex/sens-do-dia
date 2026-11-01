"""Os pesos aguentam erro? Compara jeitos objetivos de calcular e mede o efeito na sens.

Pesos (todos das mesmas 702 situacoes das demos):
  A) atual: corrida pelo PRIMEIRO DANO, curva do inimigo (Kaplan-Meier) propria de cada
     situacao e tipo de duelo;
  B) corrida pela KILL: teu tempo ate matar contra o tempo dele ate te matar;
  C) curva do inimigo unica (a mesma para todas as situacoes, so separando frente/virada);
  D) so a frequencia (media simples, para comparar).
Efeito na sens: cada situacao tem o seu melhor ponto (desvio d_s, sorteado com 20% de
desvio-padrao) e curvatura c_s; a sens do dia e a media ponderada sum(w c d)/sum(w c).
Errar os pesos de w para w' muda a sens em x' - x e custa sum(w c) (x' - x)^2 de desempenho.
Tambem roda os 1000 sorteios (bootstrap) dos pesos atuais.

Uso: python pesos_robustez.py <duelos.json>
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
from perfil import ESTRATOS, JANELA, densidade, estrato, kaplan_meier  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IDS = [e["id"] for e in ESTRATOS]
CURV = {"fino": 0.30, "curto": 0.32, "flick": 0.28, "medio": 0.25, "virada": 0.15, "rapido": 0.25}


def preparar(caminho):
    bruto = json.load(open(caminho, encoding="utf-8"))
    df = pd.DataFrame(bruto["duelos"])
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    df["estrato"] = [estrato(r) for r in df.to_dict("records")]
    return df


def tempos(df, corrida):
    """(tempo do inimigo, evento) e teu tempo, para a corrida pelo primeiro dano ou pela kill."""
    t_ini, ev, t_eu = [], [], []
    for r in df.to_dict("records"):
        if corrida == "dano":
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
                if pd.notna(r["t_morte"]):
                    a, e = r["t_morte"], 1
                else:
                    a, e = (JANELA if pd.isna(r["t_kill"]) else min(JANELA, r["t_kill"])), 0
            meu = r["ttd_eu"] if pd.notna(r["ttd_eu"]) else (max(r["tiro_nele"], 1 / 64) if pd.notna(r["tiro_nele"]) else None)
        else:   # kill
            if pd.notna(r["t_morte"]):
                a, e = r["t_morte"], 1
            else:
                a, e = (JANELA if pd.isna(r["t_kill"]) else min(JANELA, r["t_kill"])), 0
            meu = r["t_kill"] if pd.notna(r["t_kill"]) else None
        t_ini.append(a)
        ev.append(e)
        t_eu.append(meu)
    return np.array(t_ini, float), np.array(ev, int), t_eu


def pesos(df, corrida="dano", agrupar=("estrato", "tipo")):
    t_ini, ev, t_eu = tempos(df, corrida)
    d = df.assign(t_ini=t_ini, ev_ini=ev)
    dens = {}
    # mesma regra do perfil.py: uma largura de Silverman por tipo de duelo
    bandas = {tp: 1.06 * np.std(g.loc[g["ev_ini"] == 1, "t_ini"]) * max(1, (g["ev_ini"] == 1).sum()) ** (-1 / 5)
              for tp, g in d.groupby("tipo")}
    for chave, g in d.groupby(list(agrupar)):
        st, sj, _ = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
        banda = bandas[g["tipo"].iloc[0]]
        dens[chave if isinstance(chave, tuple) else (chave,)] = densidade(st, sj, banda) if len(st) else (lambda x: np.zeros(1))
    v = []
    for i, r in enumerate(d.to_dict("records")):
        t = t_eu[i]
        if t is None or not np.isfinite(t):
            t = r["t_ini"]
        t = max(float(t), 1 / 64)
        v.append(float(dens[tuple(r[k] for k in agrupar)](t)[0]) * t)
    v = np.array(v)
    est = d["estrato"].to_numpy()
    return np.array([v[est == e].sum() for e in IDS]) / v.sum()


def main():
    df = preparar(sys.argv[1])
    W = {
        "A) atual (1o dano, curva por situacao)": pesos(df),
        "B) corrida pela kill": pesos(df, "kill"),
        "C) curva do inimigo unica": pesos(df, agrupar=("tipo",)),
        "D) so frequencia": np.array([(df["estrato"] == e).mean() for e in IDS]),
    }
    print(f"{'':42s}" + "".join(f"{e:>9s}" for e in IDS))
    for k, w in W.items():
        print(f"{k:42s}" + "".join(f"{100 * x:8.1f}%" for x in w))
    rng = np.random.default_rng(11)
    boot = []
    for _ in range(1000):
        s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        boot.append(pesos(s))
    boot = np.array(boot)
    print(f"{'bootstrap do atual: 2,5%':42s}" + "".join(f"{100 * x:8.1f}%" for x in np.quantile(boot, 0.025, axis=0)))
    print(f"{'bootstrap do atual: 97,5%':42s}" + "".join(f"{100 * x:8.1f}%" for x in np.quantile(boot, 0.975, axis=0)))
    bootB = []
    for _ in range(1000):
        s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        bootB.append(pesos(s, "kill"))
    bootB = np.array(bootB)
    print(f"{'bootstrap da kill: 2,5%':42s}" + "".join(f"{100 * x:8.1f}%" for x in np.quantile(bootB, 0.025, axis=0)))
    print(f"{'bootstrap da kill: 97,5%':42s}" + "".join(f"{100 * x:8.1f}%" for x in np.quantile(bootB, 0.975, axis=0)))
    print(f"{'largura media do IC (atual / kill)':42s} {100 * np.mean(np.quantile(boot, 0.975, 0) - np.quantile(boot, 0.025, 0)):.1f} / "
          f"{100 * np.mean(np.quantile(bootB, 0.975, 0) - np.quantile(bootB, 0.025, 0)):.1f} pontos")

    # efeito na sens: muitas "pessoas" com melhores pontos diferentes por situacao
    c = np.array([CURV[e] for e in IDS])
    wA = W["A) atual (1o dano, curva por situacao)"]
    M = 20000
    d = rng.normal(0, 0.20, (M, len(IDS)))
    xA = (d * wA * c).sum(1) / (wA * c).sum()

    def efeito(w):
        x = (d * w * c).sum(1) / (w * c).sum()
        dx = x - xA
        perda = (wA * c).sum() * dx ** 2
        return 100 * (np.exp(np.sqrt(np.mean(dx ** 2))) - 1), 100 * (np.exp(np.quantile(np.abs(dx), 0.95)) - 1), 100 * np.mean(perda)

    print("\nse a verdade for o peso atual e o app usasse outro (melhor ponto de cada situacao com 20% de desvio):")
    print(f"{'peso usado':42s} {'sens muda (tipico)':>19s} {'95% das pessoas':>16s} {'perda de desempenho':>20s}")
    for k, w in W.items():
        if k.startswith("A"):
            continue
        a, b, p = efeito(w)
        print(f"{k:42s} {a:18.2f}% {b:15.2f}% {p:19.4f}%")
    ef = np.array([efeito(boot[i]) for i in range(0, 1000, 5)])
    print(f"{'sorteios do bootstrap (incerteza do atual)':42s} {np.median(ef[:, 0]):18.2f}% {np.quantile(ef[:, 1], 0.5):15.2f}% {np.median(ef[:, 2]):19.4f}%")
    print(f"{'  pior sorteio entre 200':42s} {ef[:, 0].max():18.2f}% {ef[:, 1].max():15.2f}% {ef[:, 2].max():19.4f}%")
    # comparacao: errar a sens em si (o metodo do dia ja erra ~11%)
    print("\npara comparar: errar a sens do dia em 11% (ruido do proprio teste) custa "
          f"{100 * (wA * c).sum() * np.log(1.11) ** 2:.3f}% de desempenho")


if __name__ == "__main__":
    main()
