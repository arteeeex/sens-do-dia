"""Numero exato de alvos de adaptacao (por bloco) e de aquecimento, duelo a duelo.

Usa um desenho otimo (padrao: otimo_orcamento_11.8_final.json; duelos por rodada, W0, k, rho, gama) e simula cada
duelo:  nota = curva(x) + aq_amp*exp(-n/aq_tau) + troca_amp*|dx|/ln3*exp(-m/troca_k)
                + sd_bloco*z + sd_duelo*z,  com cansaco (sd cresce com os minutos).
n = duelos desde o inicio, m = posicao no bloco, dx = troca de sens. Os primeiros `adapt`
duelos do bloco nao contam. Media sobre 25 cenarios: aquecimento 0 / 10% / 25% (sumindo em
15 ou 50 alvos) x troca de sens 0 / 10% / 25% (sumindo em 2 ou 6 alvos). Mesmos sorteios
para todas as opcoes. Tempo: 1,05 s por duelo, 6 s por bloco.

Uso: python otimizar_adapt.py [N]
"""
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from otimizar_exato import GL0, LN3, SIGMA0, curva, t975  # noqa: E402

AQ = [(0.0, 15)] + [(a, t) for a in (0.10, 0.25) for t in (15, 50)]
TR = [(0.0, 2)] + [(a, k) for a in (0.10, 0.25) for k in (2, 6)]


def sim(p, adapt, aquec, cen, S, t_duelo=1.05, t_pausa=6.0):
    aq_amp, aq_tau, tr_amp, tr_k = cen
    x0, tipo, Zb, Zd, f0 = S
    N = len(x0)
    c = np.zeros(N)
    W = p["W0"]
    soma2 = np.zeros(N)
    gl_med = 0
    n_jog = aquec
    minuto = aquec * t_duelo / 60
    x_ant = np.zeros(N)
    kb = 0
    for r, nd in enumerate(p["n"]):
        a, b = c - W / 2, c + W / 2
        ordem = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            sdd = 0.38 * (1 + 0.10 * minuto / 10)
            sdb = 0.04 + 0.02 * minuto / 10
            m = np.arange(adapt, adapt + nd)              # so os duelos que contam
            n = n_jog + m
            dx = np.abs(x - x_ant)
            efeito = (aq_amp * np.exp(-n[None, :] / aq_tau)
                      + tr_amp * (dx / LN3)[:, None] * np.exp(-m[None, :] / tr_k))
            y = curva(x, x0, tipo)[:, None] + efeito + sdb * Zb[:, kb][:, None] + sdd * Zd[:, kb, :nd]
            ys[lado].append(y.mean(axis=1))
            n_jog += adapt + nd
            minuto += ((nd + adapt) * t_duelo + t_pausa) / 60
            x_ant = x
            kb += 1
        escala = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * escala
            soma2 += ((v - v.mean(axis=0)) ** 2).sum(axis=0)
            gl_med += v.shape[0] - 1
        gl = gl_med + GL0
        sig24 = np.sqrt((soma2 + GL0 * SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"], axis=0) - np.mean(ys["A"], axis=0)
        w = np.clip(delta / (p["gam"] * t975(gl) * se), -1, 1)
        c = c - w * p["k"] * W
        W *= p["rho"]
    return np.exp(curva(c, x0, tipo) - f0) - 1, minuto


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    base = os.path.dirname(os.path.abspath(__file__))
    arq = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base, "otimo_orcamento_11.8_final.json")
    dado = json.load(open(arq, encoding="utf-8"))
    p = dado["otimo"] if "otimo" in dado else dado["desenho"] if "desenho" in dado else next(iter(dado.values()))["desenho"]
    r = np.random.default_rng(99)
    x0 = r.uniform(-0.4, 0.4, N)
    tipo = np.arange(N) % 3
    nb = 4 * len(p["n"])
    Zb = r.standard_normal((N, nb))
    Zd = r.standard_normal((N, nb, max(p["n"])))
    S = (x0, tipo, Zb, Zd, curva(x0, x0, tipo))
    cens = [(a, t, ta, tk) for (a, t) in AQ for (ta, tk) in TR]

    cache = {}
    def f(adapt, aquec):
        if (adapt, aquec) not in cache:
            ls = [sim(p, adapt, aquec, c, S)[0].mean() for c in cens]
            cache[(adapt, aquec)] = (float(np.mean(ls)), float(np.max(ls)), sim(p, adapt, aquec, cens[0], S)[1])
        return cache[(adapt, aquec)]

    print(f"desenho: n={p['n']} | {len(cens)} cenarios x {N} dias", flush=True)
    melhor = (3, 20)
    for _ in range(4):
        for a in range(0, 11):
            if f(a, melhor[1])[0] < f(*melhor)[0]:
                melhor = (a, melhor[1])
        for q in list(range(0, 61, 5)):
            if f(melhor[0], q)[0] < f(*melhor)[0]:
                melhor = (melhor[0], q)
        for q in range(max(0, melhor[1] - 6), melhor[1] + 7):
            if f(melhor[0], q)[0] < f(*melhor)[0]:
                melhor = (melhor[0], q)
    print("\nadaptacao (com o aquecimento otimo):")
    for a in range(0, 11):
        m, pior, mins = f(a, melhor[1])
        print(f"  adapt {a:2d}: perda media {100 * m:.4f}% | pior cenario {100 * pior:.4f}% | {mins:.2f} min")
    print("\naquecimento (com a adaptacao otima):")
    for q in sorted(set(list(range(0, 61, 5)) + list(range(max(0, melhor[1] - 6), melhor[1] + 7)))):
        m, pior, mins = f(melhor[0], q)
        print(f"  aquec {q:2d}: perda media {100 * m:.4f}% | pior cenario {100 * pior:.4f}% | {mins:.2f} min")
    print(f"\nMELHOR: adapt {melhor[0]}, aquecimento {melhor[1]} -> perda media {100 * f(*melhor)[0]:.4f}%")
    sufixo = os.path.basename(arq).replace("otimo_", "").replace(".json", "")
    json.dump({"desenho": p, "adapt": melhor[0], "aquec": melhor[1], "perda_media": f(*melhor)[0],
               "tabela": {f"{k[0]},{k[1]}": v for k, v in cache.items()}},
              open(os.path.join(base, f"otimo_adapt_{sufixo}.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
