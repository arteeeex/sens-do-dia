"""Compara onde gastar os 16 blocos do dia para achar o melhor ponto da curva.

Simula milhares de dias: a nota de cada bloco = curva verdadeira + ruido de bloco
(0,38 de ruido por duelo / raiz de 24 duelos, mais 0,04 de ruido do bloco inteiro).
Ajusta a parabola como o app e mede o erro da sens do dia em %.

Curvas testadas: parabola (pico moderado) e "fundo chato com paredes" (plana numa zona
de 2x e subindo fora), que e o formato que o estudo da NVIDIA achou.

Uso: python comparar_desenhos.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LN3 = np.log(3)
F1 = np.array([-LN3 / 2, -LN3 / 4, 0, LN3 / 4, LN3 / 2])
P2 = LN3 / 8
LIM = 5 * LN3 / 8
RUIDO = np.sqrt((0.38 / np.sqrt(24)) ** 2 + 0.04 ** 2)


def ajusta(xs, ys, ns):
    X = np.column_stack([np.ones_like(xs), xs, xs * xs])
    W = np.diag(ns)
    b = np.linalg.solve(X.T @ W @ X, X.T @ W @ ys)
    lo, hi = xs.min(), xs.max()
    f = lambda x: b[0] + b[1] * x + b[2] * x * x
    melhor = lo if f(lo) <= f(hi) else hi
    if b[2] > 1e-9:
        xv = -b[1] / (2 * b[2])
        if lo < xv < hi and f(xv) < f(melhor):
            melhor = xv
    return melhor


def medir(curva, xs_blocos, rng):
    xs_blocos = np.asarray(xs_blocos)
    ys = curva(xs_blocos) + RUIDO * rng.standard_normal(len(xs_blocos))
    u, inv = np.unique(np.round(xs_blocos, 4), return_inverse=True)
    m = np.array([ys[inv == i].mean() for i in range(len(u))])
    n = np.array([(inv == i).sum() for i in range(len(u))], dtype=float)
    return u, m, n


def dia(curva, desenho, rng):
    x1 = np.repeat(F1, 2)
    u, m, n = medir(curva, x1, rng)
    c = ajusta(u, m, n)
    if desenho == "atual":            # 3 sens em volta do melhor ponto da fase 1
        x2 = np.clip([c - P2, c, c + P2], -LIM, LIM)
    elif desenho == "pontas":         # mais 2 blocos em cada ponta e no centro
        x2 = np.array([F1[0], 0.0, F1[-1]])
    elif desenho == "pontas_moveis":  # faixa recentrada no melhor ponto, mesma largura
        x2 = np.clip([c - LN3 / 2, c, c + LN3 / 2], -LIM, LIM)
    elif desenho == "uniforme":       # 5 sens com 3 blocos (+1 no centro)
        x2 = np.array([F1[0], F1[1], 0.0, F1[3], F1[4], 0.0]) [:6]
        x2 = x2
    xs = np.concatenate([x1, np.repeat(x2, 2) if desenho != "uniforme" else x2])
    u, m, n = medir(curva, xs, rng)
    return ajusta(u, m, n)


def main():
    rng = np.random.default_rng(11)
    N = 6000
    for nome_curva in ["parabola", "fundo_chato"]:
        print(f"\n=== curva: {nome_curva} ===")
        for desenho in ["atual", "pontas", "pontas_moveis", "uniforme"]:
            erros = []
            for _ in range(N):
                x0 = rng.uniform(-0.4, 0.4)
                if nome_curva == "parabola":
                    curva = lambda x, x0=x0: 0.28 * (x - x0) ** 2
                else:
                    meia = np.log(2) / 2   # zona plana de 2x
                    curva = lambda x, x0=x0, meia=meia: 0.9 * np.maximum(0, np.abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2
                erros.append(dia(curva, desenho, rng) - x0)
            e = np.array(erros)
            rms = np.sqrt(np.mean(e ** 2))
            print(f"{desenho:14s} erro tipico {100 * (np.exp(rms) - 1):5.1f}%  | vies {100 * (np.exp(np.mean(e)) - 1):+5.1f}%  | 90% dos dias dentro de ±{100 * (np.exp(np.quantile(np.abs(e), 0.9)) - 1):5.1f}%")


if __name__ == "__main__":
    main()
