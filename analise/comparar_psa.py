"""PSA dentro do dia (afunilando a faixa) contra a grade com parabola.

Cada bloco = 24 duelos; nota do bloco = curva verdadeira + tendencia de horario + ruido
(0,38 por duelo / raiz de 24, mais 0,04 do bloco). A tendencia imita aquecer ao longo do
teste (-6% de tempo do primeiro ao ultimo bloco) e cansar no fim.

Desenhos (16 blocos cada, mais os extras quando indicado):
  grade_pontas : 5 sens x2 + pontas e centro x2, parabola com tudo (versao de agora)
  psa_r        : r rodadas; cada rodada compara A e B (A B B A) em volta do centro,
                 o centro anda w*W/4 (w = diferenca / MDE, entre -1 e 1) e a faixa cai
                 pela metade. Igual a calibracao da bancada PSA v3, so que com duelos.
Erro = distancia da sens final ate a sens ideal, em %.

Uso: python comparar_psa.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LN3 = np.log(3)
RUIDO = np.sqrt((0.38 / np.sqrt(24)) ** 2 + 0.04 ** 2)


def tendencia(tau):
    # tau de 0 a 1 ao longo do teste: aquece (fica 6% mais rapido) e cansa um pouco no fim
    return -0.06 * tau + 0.05 * np.maximum(0, tau - 0.75) ** 2 * 16 * 0.25


def ajusta_quad(xs, ys):
    X = np.column_stack([np.ones_like(xs), xs, xs * xs])
    b = np.linalg.lstsq(X, ys, rcond=None)[0]
    lo, hi = xs.min(), xs.max()
    f = lambda x: b[0] + b[1] * x + b[2] * x * x
    m = lo if f(lo) <= f(hi) else hi
    if b[2] > 1e-9:
        xv = -b[1] / (2 * b[2])
        if lo < xv < hi and f(xv) < f(m):
            m = xv
    return m


def grade(curva, rng, com_tempo):
    f1 = np.array([-LN3 / 2, -LN3 / 4, 0, LN3 / 4, LN3 / 2])
    perm = rng.permutation(f1)
    ordem = list(perm) + list(perm[::-1]) + [f1[0], 0.0, f1[-1], f1[-1], 0.0, f1[0]]
    xs = np.array(ordem)
    tau = np.linspace(0, 1, len(xs))
    ys = curva(xs) + (tendencia(tau) if com_tempo else 0) + RUIDO * rng.standard_normal(len(xs))
    return ajusta_quad(xs, ys), xs


def psa(curva, rng, rodadas, com_tempo, largura0=LN3, sep="quarto"):
    centro, W = 0.0, largura0
    n_blocos = 4 * rodadas
    k = 0
    jogadas = []
    for r in range(rodadas):
        meia = W / 4 if sep == "quarto" else W / 2
        a, b = centro - meia, centro + meia
        ordem = [a, b, b, a] if r % 2 == 0 else [b, a, a, b]
        ys = []
        for x in ordem:
            tau = k / max(1, n_blocos - 1)
            ys.append(curva(np.array([x]))[0] + (tendencia(tau) if com_tempo else 0) + RUIDO * rng.standard_normal())
            k += 1
            jogadas.append(x)
        ya = np.mean([y for x, y in zip(ordem, ys) if x == a])
        yb = np.mean([y for x, y in zip(ordem, ys) if x == b])
        delta = yb - ya                 # > 0: A (a menor) foi mais rapida
        mde = 1.96 * RUIDO              # erro da diferenca de 2x2 blocos = RUIDO
        w = np.clip(delta / mde, -1, 1)
        centro = centro - w * W / 4
        W = W / 2
    return centro, np.array(jogadas)


def main_pontas():
    """Versao com sondas nas pontas: quantas rodadas, faixa inicial e curva torta."""
    rng = np.random.default_rng(5)
    N = 5000
    meia_zona = np.log(2) / 2
    curvas = {
        "pico moderado": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato com paredes": lambda x0: (lambda x: 0.9 * np.maximum(0, np.abs(x - x0) - meia_zona) ** 2 + 0.02 * (x - x0) ** 2),
        "torta (perde 4x mais rapido na sens alta)": lambda x0: (lambda x: np.where(x > x0, 0.5, 0.125) * (x - x0) ** 2),
    }
    for nome_c, fabrica in curvas.items():
        print(f"\n=== {nome_c} (sondas nas pontas, com aquecimento/cansaco) ===")
        for rod in (3, 4, 5, 6):
            for larg, nome_l in ((LN3, "x3"), (np.log(4), "x4")):
                erros, perto = [], []
                for _ in range(N):
                    x0 = rng.uniform(-0.4, 0.4)
                    final, jogadas = psa(fabrica(x0), rng, rod, True, largura0=larg, sep="metade")
                    erros.append(final - x0)
                    perto.append(np.min(np.abs(jogadas - final)))
                e = np.abs(np.array(erros))
                print(f"{rod} rodadas ({4 * rod:2d} blocos), faixa inicial {nome_l}: erro tipico {100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1):5.1f}% | vies {100 * (np.exp(np.mean(erros)) - 1):+5.1f}% | 90% dentro de ±{100 * (np.exp(np.quantile(e, 0.9)) - 1):5.1f}% | jogada mais perto: {100 * (np.exp(np.median(perto)) - 1):4.1f}%")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "pontas":
        return main_pontas()
    rng = np.random.default_rng(3)
    N = 5000
    meia_zona = np.log(2) / 2
    curvas = {
        "pico moderado": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato com paredes": lambda x0: (lambda x: 0.9 * np.maximum(0, np.abs(x - x0) - meia_zona) ** 2 + 0.02 * (x - x0) ** 2),
    }
    desenhos = {
        "grade_pontas (agora)": lambda c, t: grade(c, rng, t),
        "PSA 3 rodadas (12 blocos)": lambda c, t: psa(c, rng, 3, t),
        "PSA 4 rodadas (16 blocos)": lambda c, t: psa(c, rng, 4, t),
        "PSA 5 rodadas (20 blocos)": lambda c, t: psa(c, rng, 5, t),
        "PSA 4 rod., sondas nas pontas": lambda c, t: psa(c, rng, 4, t, sep="metade"),
        "PSA 4 rod., faixa inicial x4": lambda c, t: psa(c, rng, 4, t, largura0=np.log(4)),
    }
    for com_tempo in (False, True):
        print(f"\n######## {'COM' if com_tempo else 'SEM'} aquecimento/cansaco ao longo do teste ########")
        for nome_c, fabrica in curvas.items():
            print(f"\n=== {nome_c} ===")
            for nome_d, fazer in desenhos.items():
                erros, perto = [], []
                for _ in range(N):
                    x0 = rng.uniform(-0.4, 0.4)
                    final, jogadas = fazer(fabrica(x0), com_tempo)
                    erros.append(final - x0)
                    perto.append(np.min(np.abs(jogadas - final)))
                e = np.abs(np.array(erros))
                print(f"{nome_d:32s} erro tipico {100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1):5.1f}% | 90% dentro de ±{100 * (np.exp(np.quantile(e, 0.9)) - 1):5.1f}% | sens jogada mais perto da final: {100 * (np.exp(np.median(perto)) - 1):4.1f}%")


if __name__ == "__main__":
    main()
