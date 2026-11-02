"""Concorrentes da NOTA DO BLOCO: media (atual) x media aparada x mediana, duelo a duelo.

Cada duelo: ln(tempo) = curva(sens) + dificuldade da situacao + ruido, limitado em ln(2,5) (alvo
perdido). As mesmas situacoes nas pontas A e B da rodada (como no app). Cenarios de ruido:
  normal (0,38); cauda pesada (t de Student com 3 graus); alvo perdido por azar (5% e 15% dos
  duelos estouram 2,5 s ao acaso); alvo perdido POR CAUSA da sens (a chance de estourar cresce
  longe da melhor sens: e informacao, nao ruido).
A nota de cada bloco e a media de ln(tempo) (atual), a media aparada 10% / 20% ou a mediana,
ou ainda sem o log: a media do tempo em segundos ou a media da velocidade (1/tempo).
Roda o PSA de 12 min inteiro com cada nota e mede a perda de desempenho.

Uso: python concorrentes_nota.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
TETO = np.log(2.5)


def nota(y, como):
    if como == "media":
        return y.mean(1)
    if como == "mediana":
        return np.median(y, 1)
    if como == "tempo sem log":           # media do tempo em segundos (na escala de log so para comparar)
        return np.log(np.exp(y).mean(1))
    if como == "velocidade (1/tempo)":    # media de 1/tempo
        return -np.log(np.exp(-y).mean(1))
    corte = {"aparada 10%": 0.10, "aparada 20%": 0.20}[como]
    ys = np.sort(y, 1)
    k = int(np.floor(corte * y.shape[1]))
    return ys[:, k:y.shape[1] - k].mean(1) if k > 0 else ys.mean(1)


def sessao(p, x0, tipo, rng, como, ruido, N):
    n, W, k, rho, gam, gl0, adapt = p["n"], p["W0"], p["k"], p["rho"], p["gam"], p.get("gl0", 16), p.get("adapt", 1)
    c = np.zeros(N); soma2 = np.zeros(N); gl_med = 0
    base_t = np.log(0.55)
    for r, nd in enumerate(n):
        a, b = c - W / 2, c + W / 2
        dific = rng.normal(0, 0.5, (N, nd))           # as mesmas situacoes nas 4 rodadas do bloco
        seq = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in seq:
            x = a if lado == "A" else b
            f = oe.curva(x, x0, tipo)[:, None]
            if ruido == "t3":
                e = 0.38 * rng.standard_t(3, (N, nd)) / np.sqrt(3)
            else:
                e = 0.38 * rng.standard_normal((N, nd))
            y = base_t + f + dific + e + 0.04 * rng.standard_normal((N, 1))
            if ruido == "perde 5%":
                y = np.where(rng.random((N, nd)) < 0.05, TETO, y)
            elif ruido == "perde 15%":
                y = np.where(rng.random((N, nd)) < 0.15, TETO, y)
            elif ruido == "perde pela sens":
                pr = np.clip(0.03 + 0.6 * f, 0, 0.6)
                y = np.where(rng.random((N, nd)) < pr, TETO, y)
            y = np.minimum(y, TETO)
            ys[lado].append(nota(y, como))
        e24 = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * e24
            soma2 += ((v - v.mean(0)) ** 2).sum(0)
            gl_med += v.shape[0] - 1
        gl = gl_med + gl0
        sig24 = np.sqrt((soma2 + gl0 * oe.SIGMA0 ** 2) / gl)
        se = sig24 / e24
        delta = np.mean(ys["B"], 0) - np.mean(ys["A"], 0)
        w = np.clip(delta / (gam * oe.t975(gl) * se), -1, 1)
        c = c - w * k * W
        W *= rho
    return c


def main():
    p = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    N = 8000
    comos = ["media", "aparada 10%", "aparada 20%", "mediana", "tempo sem log", "velocidade (1/tempo)"]
    ruidos = ["normal", "t3", "perde 5%", "perde 15%", "perde pela sens"]
    tab, difs = {}, {}
    for ruido in ruidos:
        linha = []
        base = None
        for como in comos:
            rng = np.random.default_rng(123)                 # mesmos sorteios para todas as notas
            x0 = rng.uniform(-0.4, 0.4, N); tipo = np.arange(N) % 3
            c = sessao(p, x0, tipo, rng, como, ruido, N)
            l = np.exp(oe.curva(c, x0, tipo) - oe.curva(x0, x0, tipo)) - 1
            if base is None:
                base = l
            tab.setdefault(como, []).append(100 * l.mean())
            difs.setdefault(como, []).append(100 * (l - base))
            linha.append(f"{como}: {100 * l.mean():.4f}%")
        print(f"{ruido:18s} | " + " | ".join(linha), flush=True)
    print("\nmedia dos 5 cenarios (diferenca para a media de ln(tempo), mesmos sorteios):")
    for como, v in sorted(tab.items(), key=lambda kv: np.mean(kv[1])):
        dd = np.array(difs[como])                          # cenarios x sessoes
        se = np.sqrt((dd.var(1, ddof=1) / dd.shape[1]).sum()) / dd.shape[0]
        print(f"  {como:22s} {np.mean(v):.4f}%  | dif {dd.mean():+.4f} +- {se:.4f}")


if __name__ == "__main__":
    main()
