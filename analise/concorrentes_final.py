"""Concorrentes da CONTA FINAL da sens (o jogo e o mesmo; muda so como o resultado e calculado).

Simula o desenho de 12 min (mesmos sorteios, ruido do dia incerto, cansaco) guardando tudo de
cada rodada, e calcula a sens final de varios jeitos:
  E0  atual: o centro depois da ultima rodada;
  E1  media dos centros a partir da rodada m (Polyak-Ruppert, classico para reduzir ruido);
  E1p media ponderada dos centros (peso crescendo com a rodada);
  E2  curva (parabola) ajustada com os 24 blocos, minimo dentro da faixa jogada;
  E3  reta das inclinacoes: cada rodada da a inclinacao no seu centro; onde ela zera;
  E4  meio a meio entre E0 e E2.
Perda media de desempenho e erro tipico, no modelo e nos cenarios de ataque.

Uso: python concorrentes_final.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def simular_registro(p, s, escala_ruido=1.0, cansaco=True):
    """Como oe.simular, mas guarda cada bloco (x, nota, duelos) e o centro antes/depois de cada rodada."""
    n, W, k, rho, gam = p["n"], p["W0"], p["k"], p["rho"], p["gam"]
    adapt, aquec, gl0 = p.get("adapt", 1), p.get("aquec", 0), p.get("gl0", 16)
    esc = escala_ruido * (s.escala if s.escala is not None else 1.0)
    N = len(s.x0)
    c = np.zeros(N); soma2 = np.zeros(N); gl_med = 0
    minuto = aquec * 1.05 / 60
    kb = 0
    X, Y, NB, C0, C1, G = [], [], [], [], [], []
    for r, nd in enumerate(n):
        a, b = c - W / 2, c + W / 2
        ordem = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            sdd = 0.38 * (1 + 0.10 * minuto / 10) if cansaco else 0.38
            sdb = 0.04 + 0.02 * minuto / 10 if cansaco else 0.04
            sd = esc * np.sqrt(sdd ** 2 / nd + sdb ** 2)
            y = oe.curva(x, s.x0, s.tipo) + sd * s.Z[:, kb]
            ys[lado].append(y)
            X.append(x.copy()); Y.append(y); NB.append(nd)
            kb += 1
            minuto += ((nd + adapt) * 1.05 + 6) / 60
        escala = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * escala
            soma2 += ((v - v.mean(axis=0)) ** 2).sum(axis=0)
            gl_med += v.shape[0] - 1
        gl = gl_med + gl0
        sig24 = np.sqrt((soma2 + gl0 * oe.SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"], axis=0) - np.mean(ys["A"], axis=0)
        w = np.clip(delta / (gam * oe.t975(gl) * se), -1, 1)
        C0.append(c.copy())
        G.append((delta / (b - a), (b - a) ** 2 / se ** 2))   # inclinacao e peso dela
        c = c - w * k * W
        C1.append(c.copy())
        W *= rho
    return {"X": np.array(X), "Y": np.array(Y), "NB": np.array(NB, float), "C0": np.array(C0), "C1": np.array(C1), "G": G}


def quad_wls(X, Y, Wt):
    """Parabola por minimos quadrados ponderados, por sessao (colunas). Devolve vertice e curvatura."""
    S0 = Wt.sum(0); S1 = (Wt * X).sum(0); S2 = (Wt * X ** 2).sum(0); S3 = (Wt * X ** 3).sum(0); S4 = (Wt * X ** 4).sum(0)
    T0 = (Wt * Y).sum(0); T1 = (Wt * X * Y).sum(0); T2 = (Wt * X ** 2 * Y).sum(0)
    A = np.stack([np.stack([S0, S1, S2], -1), np.stack([S1, S2, S3], -1), np.stack([S2, S3, S4], -1)], -2)
    B = np.stack([T0, T1, T2], -1)
    coef = np.linalg.solve(A + 1e-12 * np.eye(3), B[..., None])[..., 0]
    a2, a1 = coef[:, 2], coef[:, 1]
    return np.where(a2 > 1e-9, -a1 / (2 * np.maximum(a2, 1e-9)), np.nan), a2


def estimadores(reg):
    C1, X, Y, NB = reg["C1"], reg["X"], reg["Y"], reg["NB"]
    R = C1.shape[0]
    lo, hi = X.min(0), X.max(0)
    out = {"E0 atual (centro final)": C1[-1]}
    for m in range(1, R):
        out[f"E1 media dos centros das rodadas {m + 1}-{R}"] = C1[m:].mean(0)
    pesos = np.arange(1, R + 1, dtype=float)[:, None]
    out["E1p media ponderada dos centros"] = (C1 * pesos).sum(0) / pesos.sum()
    v, a2 = quad_wls(X, Y, NB[:, None] * np.ones_like(X))
    e2 = np.where(np.isfinite(v), np.clip(v, lo, hi), C1[-1])
    out["E2 parabola com os 24 blocos"] = e2
    gs = np.array([g for g, _ in reg["G"]]); ws = np.array([w for _, w in reg["G"]]); cs = reg["C0"]
    sw = ws.sum(0); mx = (ws * cs).sum(0) / sw; my = (ws * gs).sum(0) / sw
    beta = (ws * (cs - mx) * (gs - my)).sum(0) / np.maximum((ws * (cs - mx) ** 2).sum(0), 1e-12)
    e3 = np.where(beta > 1e-6, mx - my / np.maximum(beta, 1e-6), C1[-1])
    out["E3 reta das inclinacoes"] = np.clip(e3, lo, hi)
    out["E4 meio a meio E0 e E2"] = 0.5 * (C1[-1] + e2)
    return out


def main():
    p = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    cenarios = [("modelo (ruido incerto)", dict(ruido_incerto=True), {}, None),
                ("curvas que o otimizador nao viu", dict(ruido_incerto=True), {}, "novas"),
                ("ruido x2", dict(ruido_incerto=False), {"escala_ruido": 2.0}, None),
                ("melhor sens ate +-60%", dict(ruido_incerto=True), {}, "longe")]
    tabela = {}
    for nome_c, kw_s, kw_sim, mod in cenarios:
        s = oe.Sorteio(200000, 4711, **kw_s)
        if mod == "novas":
            s.tipo = 3 + (np.arange(len(s.x0)) % 2)
            s.f0 = oe.curva(s.x0, s.x0, s.tipo)
        if mod == "longe":
            s.x0 = np.random.default_rng(2).uniform(-0.6, 0.6, len(s.x0))
            s.f0 = oe.curva(s.x0, s.x0, s.tipo)
        reg = simular_registro(p, s, **kw_sim)
        est = estimadores(reg)
        base = np.exp(oe.curva(est["E0 atual (centro final)"], s.x0, s.tipo) - s.f0) - 1
        print(f"\n=== {nome_c} ===")
        for nome, xh in est.items():
            l = np.exp(oe.curva(xh, s.x0, s.tipo) - s.f0) - 1
            d = l - base
            e = xh - s.x0
            tabela.setdefault(nome, []).append(100 * l.mean())
            print(f"  {nome:44s} perda {100 * l.mean():.4f}%  (x atual {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f})  erro {100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1):5.1f}%", flush=True)
    print("\nmedia dos 4 cenarios:")
    for nome, v in sorted(tabela.items(), key=lambda kv: np.mean(kv[1])):
        print(f"  {nome:44s} {np.mean(v):.4f}%")


if __name__ == "__main__":
    main()
