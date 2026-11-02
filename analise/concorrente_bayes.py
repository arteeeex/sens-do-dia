"""Concorrente: PSA BAYESIANO contra o PSA atual (mesmos blocos, mesmo tempo, mesmos sorteios).

Guarda a chance de cada combinacao (melhor sens x*, curvatura de cada lado kE, kD) ser a
verdadeira, num grid. Cada rodada joga as duas pontas m-h e m+h em A B B A / B A A B, com m =
mediana da chance de x* (o centro vai onde a evidencia aponta) e h por um cronograma (como o
PSA) ou proporcional a incerteza de x*. A diferenca B - A atualiza o grid (verossimilhanca normal,
com o ruido medido no dia como no app). No fim, a sens e a que tem o MENOR PREJUIZO ESPERADO
segundo o grid (decisao de Bayes para o objetivo de verdade).

Uso: python concorrente_bayes.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
XS = np.arange(-1.2, 1.2001, 0.03)
KS = np.array([0.06, 0.12, 0.2, 0.3, 0.45, 0.7])
GX, GE, GD = [a.ravel() for a in np.meshgrid(XS, KS, KS, indexing="ij")]
LOGPRIOR = -0.5 * (GX / 0.5) ** 2


def f_grid(x):
    """f_theta(x) para cada sessao (linhas) e cada ponto do grid (colunas)."""
    d = x[:, None] - GX[None, :]
    return np.where(d < 0, GE[None, :], GD[None, :]) * d * d


def bayes(p, s, idx, h0, rho, modo="cronograma", c_sd=2.0, hmin=0.15, escala_ruido=1.0):
    n, gl0 = p["n"], p.get("gl0", 16)
    adapt = p.get("adapt", 1)
    x0, tipo, Z = s.x0[idx], s.tipo[idx], s.Z[idx]
    esc = escala_ruido * (s.escala[idx] if s.escala is not None else 1.0)
    N = len(idx)
    logp = np.tile(LOGPRIOR, (N, 1))
    soma2 = np.zeros(N); gl_med = 0
    minuto = 0.0
    kb = 0
    h = np.full(N, h0)
    lo, hi = np.full(N, np.inf), np.full(N, -np.inf)
    for r, nd in enumerate(n):
        post = np.exp(logp - logp.max(1, keepdims=True)); post /= post.sum(1, keepdims=True)
        # mediana e desvio de x* (marginal)
        cdf = np.cumsum(post, axis=1)
        ordem = np.argsort(GX)
        cdf_o = np.cumsum(post[:, ordem], axis=1)
        m = GX[ordem][np.argmax(cdf_o >= 0.5, axis=1)]
        sd_x = np.sqrt((post * GX[None, :] ** 2).sum(1) - (post * GX[None, :]).sum(1) ** 2)
        if modo == "cronograma":
            h = np.full(N, h0 * rho ** r)
        else:
            h = np.clip(c_sd * sd_x, hmin, h0)
        a, b = m - h, m + h
        lo, hi = np.minimum(lo, a), np.maximum(hi, b)
        seq = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in seq:
            x = a if lado == "A" else b
            sdd = 0.38 * (1 + 0.10 * minuto / 10)
            sdb = 0.04 + 0.02 * minuto / 10
            sd = esc * np.sqrt(sdd ** 2 / nd + sdb ** 2)
            ys[lado].append(oe.curva(x, x0, tipo) + sd * Z[:, kb])
            kb += 1
            minuto += ((nd + adapt) * 1.05 + 6) / 60
        e24 = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * e24
            soma2 += ((v - v.mean(0)) ** 2).sum(0)
            gl_med += v.shape[0] - 1
        gl = gl_med + gl0
        sig24 = np.sqrt((soma2 + gl0 * oe.SIGMA0 ** 2) / gl)
        se = sig24 / e24 * np.sqrt(0.5 + 0.5)
        delta = np.mean(ys["B"], 0) - np.mean(ys["A"], 0)
        mu = f_grid(b) - f_grid(a)
        logp += -0.5 * ((delta[:, None] - mu) / se[:, None]) ** 2
    post = np.exp(logp - logp.max(1, keepdims=True)); post /= post.sum(1, keepdims=True)
    # decisao de Bayes: menor prejuizo esperado entre 61 candidatos dentro da faixa jogada
    melhor_v = np.full(N, np.inf); melhor_x = np.zeros(N)
    for t in np.linspace(0, 1, 61):
        cand = lo + t * (hi - lo)
        v = (post * f_grid(cand)).sum(1)
        troca = v < melhor_v
        melhor_v = np.where(troca, v, melhor_v); melhor_x = np.where(troca, cand, melhor_x)
    return melhor_x


def avaliar(p, s, cfg, N, bloco=2000, **kw):
    xs = []
    for i in range(0, N, bloco):
        idx = np.arange(i, min(N, i + bloco))
        xs.append(bayes(p, s, idx, **cfg, **kw))
    xh = np.concatenate(xs)
    l = np.exp(oe.curva(xh, s.x0[:N], s.tipo[:N]) - s.f0[:N]) - 1
    return xh, l


def main():
    p = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    N = 10000
    s = oe.Sorteio(N, 8080, ruido_incerto=True)
    l_psa = np.exp(oe.curva(oe.simular(p, s)[2] + s.x0, s.x0, s.tipo) - s.f0) - 1
    print(f"PSA atual: perda {100 * l_psa.mean():.4f}%", flush=True)
    W0 = p["W0"]
    cfgs = []
    for h0 in (W0 / 2 * 0.8, W0 / 2, W0 / 2 * 1.2):
        for rho in (0.8, 0.9, 0.95, 1.0):
            cfgs.append(dict(h0=h0, rho=rho, modo="cronograma"))
    for c_sd in (1.5, 2.5, 4.0):
        for hmin in (0.12, 0.25):
            cfgs.append(dict(h0=W0 / 2, rho=1.0, modo="adaptativo", c_sd=c_sd, hmin=hmin))
    resultados = []
    for cfg in cfgs:
        _, l = avaliar(p, s, cfg, N)
        d = l - l_psa
        resultados.append((l.mean(), cfg, d.mean(), d.std() / np.sqrt(N)))
        print(f"  bayes {cfg}: perda {100 * l.mean():.4f}% (x PSA {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(N):.4f})", flush=True)
    resultados.sort(key=lambda r: r[0])
    melhor = resultados[0][1]
    print(f"\nMELHOR bayes: {melhor} -> conferindo com 20 mil dias novos e nos cenarios de ataque", flush=True)
    for nome, kw_s, mod, kw in (("modelo", dict(ruido_incerto=True), None, {}), ("curvas novas", dict(ruido_incerto=True), "novas", {}),
                                ("ruido x2", dict(ruido_incerto=False), None, {"escala_ruido": 2.0}), ("melhor sens ate +-60%", dict(ruido_incerto=True), "longe", {})):
        s2 = oe.Sorteio(20000, 9191, **kw_s)
        if mod == "novas":
            s2.tipo = 3 + (np.arange(len(s2.x0)) % 2); s2.f0 = oe.curva(s2.x0, s2.x0, s2.tipo)
        if mod == "longe":
            s2.x0 = np.random.default_rng(4).uniform(-0.6, 0.6, len(s2.x0)); s2.f0 = oe.curva(s2.x0, s2.x0, s2.tipo)
        lp = np.exp(oe.curva(oe.simular(p, s2, **kw)[2] + s2.x0, s2.x0, s2.tipo) - s2.f0) - 1
        _, lb = avaliar(p, s2, melhor, 20000, **kw)
        d = lb - lp
        print(f"  {nome:24s} PSA {100 * lp.mean():.4f}% | bayes {100 * lb.mean():.4f}% | dif {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f}", flush=True)


if __name__ == "__main__":
    main()
