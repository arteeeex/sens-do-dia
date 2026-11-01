"""Com o PSA de sondas nas pontas, qual conta final usa melhor TODAS as rodadas?

Desenho fixo: r rodadas; em cada uma, A e B nas pontas da faixa (A B B A / B A A B),
o centro anda w*W/4 (w = diferenca / MDE, entre -1 e 1) e a faixa cai pela metade.

Contas finais testadas:
  passo        : o centro depois da ultima rodada (so o caminho)
  diferencas   : cada rodada da a diferenca B - A ~ 4*a*h*(c - x*); ajusta a e x* com
                 todas as rodadas, peso = 1/erro^2 (so diferencas da mesma rodada: imune a
                 aquecimento e cansaco)
  parabola     : parabola com todos os blocos (mistura horarios)
  parabola_t   : parabola com todos os blocos + tendencia de horario
  lados        : duas meias-parabolas (curvatura diferente de cada lado) + tendencia de
                 horario, todos os blocos
Erro = distancia ate a sens ideal, em %.
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LN3 = np.log(3)
RUIDO = np.sqrt((0.38 / np.sqrt(24)) ** 2 + 0.04 ** 2)


def tendencia(tau):
    return -0.06 * tau + 0.05 * np.maximum(0, tau - 0.75) ** 2 * 4


def rodar(curva, rng, rodadas, W0=LN3):
    c, W = 0.0, W0
    blocos = []   # (x, tau, nota, rodada)
    difs = []     # (c, h, delta)
    n = 4 * rodadas
    k = 0
    for r in range(rodadas):
        h = W / 2
        a, b = c - h, c + h
        ordem = [a, b, b, a] if r % 2 == 0 else [b, a, a, b]
        ys = []
        for x in ordem:
            tau = k / (n - 1)
            y = curva(x) + tendencia(tau) + RUIDO * rng.standard_normal()
            blocos.append((x, tau, y, r))
            ys.append(y)
            k += 1
        ya = np.mean([y for x, y in zip(ordem, ys) if x == a])
        yb = np.mean([y for x, y in zip(ordem, ys) if x == b])
        d = yb - ya
        difs.append((c, h, d))
        w = np.clip(d / (1.96 * RUIDO), -1, 1)
        c = c - w * W / 4
        W /= 2
    return c, np.array(blocos), np.array(difs)


def melhor_quad(b, lo, hi):
    f = lambda x: b[0] + b[1] * x + b[2] * x * x
    m = lo if f(lo) <= f(hi) else hi
    if b[2] > 1e-9:
        xv = -b[1] / (2 * b[2])
        if lo < xv < hi and f(xv) < f(m):
            m = xv
    return m


def est_diferencas(difs, lo, hi, fallback):
    c, h, d = difs[:, 0], difs[:, 1], difs[:, 2]
    # d = a*(4 h c) - B*(4 h) com B = a*x*; erro de cada d e o mesmo (RUIDO)
    X = np.column_stack([4 * h * c, -4 * h])
    coef, *_ = np.linalg.lstsq(X, d, rcond=None)
    a, B = coef
    if a <= 1e-6:
        return fallback
    return float(np.clip(B / a, lo, hi))


def est_parabola(bl, lo, hi, tempo):
    x, tau, y = bl[:, 0], bl[:, 1], bl[:, 2]
    cols = [np.ones_like(x), x, x * x]
    if tempo:
        cols += [tau, tau * tau]
    X = np.column_stack(cols)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return melhor_quad(b[:3], lo, hi)


def est_lados(bl, lo, hi):
    x, tau, y = bl[:, 0], bl[:, 1], bl[:, 2]
    melhor, menor = None, np.inf
    for xs in np.linspace(lo, hi, 61):          # procura o x* que melhor explica
        L = np.minimum(x - xs, 0) ** 2
        R = np.maximum(x - xs, 0) ** 2
        X = np.column_stack([np.ones_like(x), L, R, tau, tau * tau])
        b, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        if b[1] < 0 or b[2] < 0:
            continue
        sse = np.sum((X @ b - y) ** 2)
        if sse < menor:
            menor, melhor = sse, xs
    return melhor if melhor is not None else 0.0


def main():
    rng = np.random.default_rng(9)
    N = 3000
    meia = np.log(2) / 2
    curvas = {
        "pico moderado": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato": lambda x0: (lambda x: 0.9 * max(0.0, abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2),
        "torta (4x mais rapido na alta)": lambda x0: (lambda x: (0.5 if x > x0 else 0.125) * (x - x0) ** 2),
    }
    for rod in (4, 5):
        print(f"\n################ {rod} rodadas ({4 * rod} blocos) ################")
        for nome, fab in curvas.items():
            res = {k: [] for k in ["passo", "diferencas", "parabola", "parabola_t", "lados", "media(passo,lados)"]}
            for _ in range(N):
                x0 = rng.uniform(-0.4, 0.4)
                c, bl, difs = rodar(fab(x0), rng, rod)
                lo, hi = bl[:, 0].min(), bl[:, 0].max()
                e_l = est_lados(bl, lo, hi)
                res["passo"].append(c - x0)
                res["diferencas"].append(est_diferencas(difs, lo, hi, c) - x0)
                res["parabola"].append(est_parabola(bl, lo, hi, False) - x0)
                res["parabola_t"].append(est_parabola(bl, lo, hi, True) - x0)
                res["lados"].append(e_l - x0)
                res["media(passo,lados)"].append((c + e_l) / 2 - x0)
            print(f"\n=== {nome} ===")
            for k, v in res.items():
                v = np.array(v)
                print(f"{k:20s} erro tipico {100 * (np.exp(np.sqrt(np.mean(v ** 2))) - 1):5.1f}% | vies {100 * (np.exp(np.mean(v)) - 1):+5.1f}% | 90% dentro de ±{100 * (np.exp(np.quantile(np.abs(v), 0.9)) - 1):5.1f}%")


if __name__ == "__main__":
    main()
