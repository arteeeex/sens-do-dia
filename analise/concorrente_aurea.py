"""Concorrente: BUSCA PELA SECAO AUREA (classica para achar o minimo) contra o PSA atual.

Mesmos blocos, mesmo tempo, mesmos sorteios e mesmo ruido do concorrente_bayes.py.
Cada rodada joga os dois pontos de dentro da faixa [lo, hi] (a 38,2% e 61,8%), A B B A / B A A B.
  duro:  o lado pior sai (a faixa fica com 61,8%), como no livro;
  teste: so corta se a diferenca passar do teste (|w| = 1, a mesma regra do PSA com gama);
         senao encolhe as duas pontas por igual (o centro fica).
Sens final = meio da faixa. Faixa inicial +-B0 em volta da sens de hoje (o B0 que for melhor).

Uso: python concorrente_aurea.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
PHI = (np.sqrt(5) - 1) / 2


def aurea(p, s, B0, modo="duro", gam=1.0, escala_ruido=1.0):
    n, gl0, adapt = p["n"], p.get("gl0", 16), p.get("adapt", 1)
    x0, tipo, Z = s.x0, s.tipo, s.Z
    esc = escala_ruido * (s.escala if s.escala is not None else 1.0)
    N = len(x0)
    lo, hi = np.full(N, -B0), np.full(N, B0)
    soma2 = np.zeros(N); gl_med = 0
    minuto = 0.0
    kb = 0
    for r, nd in enumerate(n):
        L = hi - lo
        a, b = hi - PHI * L, lo + PHI * L
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
        se = sig24 / e24
        delta = np.mean(ys["B"], 0) - np.mean(ys["A"], 0)
        esq = delta > 0                       # B pior: o minimo fica a esquerda de b
        if modo == "duro":
            hi, lo = np.where(esq, b, hi), np.where(esq, lo, a)
        else:
            w = np.clip(delta / (gam * oe.t975(gl) * se), -1, 1)
            sig = np.abs(w) >= 1
            corte = (1 - PHI) / 2 * L
            hi2 = np.where(sig, np.where(esq, b, hi), hi - corte)
            lo2 = np.where(sig, np.where(esq, lo, a), lo + corte)
            hi, lo = hi2, lo2
    return (lo + hi) / 2


def perda(xh, s):
    return np.exp(oe.curva(xh, s.x0, s.tipo) - s.f0) - 1


def main():
    p = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    s = oe.Sorteio(10000, 8080, ruido_incerto=True)
    l_psa = np.exp(oe.curva(oe.simular(p, s)[2] + s.x0, s.x0, s.tipo) - s.f0) - 1
    print(f"PSA atual: perda {100 * l_psa.mean():.4f}%", flush=True)
    res = []
    for modo in ("duro", "teste"):
        for B0 in (0.4, 0.5, 0.65, 0.8, 1.0, 1.3):
            for gam in ((1.0,) if modo == "duro" else (0.5, 1.0, 2.0)):
                l = perda(aurea(p, s, B0, modo, gam), s)
                d = l - l_psa
                res.append((l.mean(), dict(B0=B0, modo=modo, gam=gam)))
                print(f"  aurea {modo:5s} B0 {B0:4.2f} gama {gam:3.1f}: perda {100 * l.mean():.4f}% (x PSA {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f})", flush=True)
    res.sort(key=lambda r: r[0])
    m = res[0][1]
    print(f"\nMELHOR aurea: {m} -> 20 mil dias novos e cenarios de ataque", flush=True)
    tot_p, tot_a = [], []
    for nome, kw_s, mod, kw in (("modelo", dict(ruido_incerto=True), None, {}), ("curvas novas", dict(ruido_incerto=True), "novas", {}),
                                ("ruido x2", dict(ruido_incerto=False), None, {"escala_ruido": 2.0}), ("melhor sens ate +-60%", dict(ruido_incerto=True), "longe", {})):
        s2 = oe.Sorteio(20000, 9191, **kw_s)
        if mod == "novas":
            s2.tipo = 3 + (np.arange(len(s2.x0)) % 2); s2.f0 = oe.curva(s2.x0, s2.x0, s2.tipo)
        if mod == "longe":
            s2.x0 = np.random.default_rng(4).uniform(-0.6, 0.6, len(s2.x0)); s2.f0 = oe.curva(s2.x0, s2.x0, s2.tipo)
        lp = np.exp(oe.curva(oe.simular(p, s2, **kw)[2] + s2.x0, s2.x0, s2.tipo) - s2.f0) - 1
        la = perda(aurea(p, s2, m["B0"], m["modo"], m["gam"], **kw), s2)
        d = la - lp
        tot_p.append(lp.mean()); tot_a.append(la.mean())
        print(f"  {nome:24s} PSA {100 * lp.mean():.4f}% | aurea {100 * la.mean():.4f}% | dif {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f}", flush=True)
    print(f"  media dos 4: PSA {100 * np.mean(tot_p):.4f}% | aurea {100 * np.mean(tot_a):.4f}%")


if __name__ == "__main__":
    main()
