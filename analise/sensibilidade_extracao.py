"""Os numeros que definem um duelo na extracao mudam os pesos?

  MIRA_NA_DIRECAO = 4 graus: um tiro teu conta como "atirou nele" se passou a menos disso da
                    cabeca dele (exigencia de acao para o duelo de frente contar);
  JUNTA_BURACO    = 4 ticks: piscadas do "visto" menores que isso continuam o mesmo duelo.
Reextrai com 2/8 graus e 2/8 ticks, refaz os pesos (mesma conta do app) e mede quanto a sens
final mudaria (melhor ponto de cada situacao com 20% de desvio, como em pesos_robustez.py).

Uso: python sensibilidade_extracao.py <pasta_das_demos>
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import extrair_duelos as ed  # noqa: E402
from perfil import estrato  # noqa: E402
from pesos_robustez import CURV, IDS, pesos  # noqa: E402


def extrair(pasta, mira, junta):
    # caminho so ate 0,5 s: e o que a velocidade do alvo (situacao "rapido") usa
    ed.MIRA_NA_DIRECAO, ed.JUNTA_BURACO, ed.TRAJ_TICKS = mira, junta, int(0.5 * ed.TICK)
    demos = sorted(glob.glob(os.path.join(pasta, "match730_*.dem")), key=os.path.getmtime)
    todos = []
    for i, d in enumerate(demos):
        todos.extend(ed.processar(d, i))
    df = pd.DataFrame(todos)
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    df["estrato"] = [estrato(r) for r in df.to_dict("records")]
    return df


def main():
    pasta = sys.argv[1]
    variantes = [("base (4 graus, 4 ticks)", 4.0, 4), ("mira 2 graus", 2.0, 4), ("mira 8 graus", 8.0, 4),
                 ("junta 2 ticks", 4.0, 2), ("junta 8 ticks", 4.0, 8)]
    W, N = {}, {}
    for nome, mira, junta in variantes:
        df = extrair(pasta, mira, junta)
        W[nome] = pesos(df)
        N[nome] = len(df)
        print(f"{nome:26s} {len(df):4d} duelos | " + " ".join(f"{e} {100 * w:4.1f}%" for e, w in zip(IDS, W[nome])), flush=True)
    c = np.array([CURV[e] for e in IDS])
    rng = np.random.default_rng(3)
    d = rng.normal(0, 0.20, (20000, len(IDS)))
    wb = W["base (4 graus, 4 ticks)"]
    xb = (d * wb * c).sum(1) / (wb * c).sum()
    print("\nquanto a sens mudaria (tipico / 95% das pessoas):")
    for nome in W:
        if nome.startswith("base"):
            continue
        x = (d * W[nome] * c).sum(1) / (W[nome] * c).sum()
        dx = x - xb
        print(f"  {nome:24s} {100 * (np.exp(np.sqrt(np.mean(dx ** 2))) - 1):5.2f}% / {100 * (np.exp(np.quantile(np.abs(dx), 0.95)) - 1):5.2f}%")


if __name__ == "__main__":
    main()
