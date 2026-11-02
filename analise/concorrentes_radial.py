"""Concorrentes da APROXIMACAO do alvo na continuacao do caminho (a distancia, nao a tela).

Mesma emenda do perfil.py (doador vivo, mesmo tipo e faixa de distancia, proximo passo casado),
mudando so como a distancia anda depois da costura:
  unidades (atual):  o alvo chega mais perto o mesmo tanto de unidades que o doador chegou;
  proporcao:         a distancia muda na mesma proporcao que a do doador.
Teste contra o futuro real escondido de TODOS os caminhos que tem 0,75 s de futuro depois do
corte (nao so os que ficaram vivos 2,5 s: assim entram os alvos de perto), cortes de 0,25 a 1,5 s.
Mede (KS: 0 = igual): mudanca da distancia em 0,5 s (log da razao), velocidade de aproximacao
por amostra, as duas por faixa de distancia (perto < 500 u, longe), quantas amostras batem no
piso de distancia, e a nota da tela (media dos 4 do concorrentes_caminho.py).

Uso: python concorrentes_radial.py <duelos.json>
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from concorrentes_caminho import FUT, emenda, ks, medidas  # noqa: E402
from perfil import HZ  # noqa: E402

PERTO = 500.0


def main():
    d = pd.DataFrame(json.load(open(sys.argv[1], encoding="utf-8"))["duelos"])
    d = d[~d["sem_mira"] & ~d["luneta"] & ~d["franco"]].reset_index(drop=True)
    trs = [[list(p) for p in t] for t in d["traj"]]
    dss = [list(map(float, x)) for x in d["dists"]]
    tipos = d["tipo"].tolist()
    nreal = [len(t) for t in trs]
    d_min = min(min(x) for x in dss if len(x))
    metodos = ["unidades", "proporcao"]
    casos = [(i, int(T * HZ)) for T in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5) for i in range(len(trs)) if nreal[i] >= int(T * HZ) + FUT + 1 and int(T * HZ) >= 2]
    print(f"casos: {len(casos)} (caminhos com 0,75 s de futuro real depois do corte); piso de distancia {d_min:.0f} u", flush=True)
    R = {m: [] for m in metodos + ["real"]}
    for i, k in casos:
        tr, ds = np.asarray(trs[i]), np.asarray(dss[i])
        fut_t, fut_d = tr[k:k + FUT + 1], ds[k:k + FUT + 1]
        v_antes = (tr[k] - tr[k - 1]) * HZ
        perto = ds[k] < PERTO
        R["real"].append((i, perto, fut_d, medidas(fut_t, v_antes)))
        for m in metodos:
            ct, cd = emenda(i, k, trs, dss, tipos, nreal, d_min, casar="proximo", radial=m, com_ds=True)
            R[m].append((i, perto, cd, medidas(ct, v_antes)))

    def notas(lista_m, lista_r, filtro=None):
        sel = [n for n, c in enumerate(lista_r) if filtro is None or c[1] == filtro]
        lr = lambda L: np.array([np.log(L[n][2][16] / L[n][2][0]) for n in sel])
        vr = lambda L: np.concatenate([np.diff(L[n][2]) * HZ for n in sel])
        return ks(lr(lista_m), lr(lista_r)), ks(vr(lista_m), vr(lista_r)), len(sel)

    print(f"{'aproximacao':12s} | {'faixa':6s} | {'casos':>5s} | KS mudanca da distancia 0,5 s | KS velocidade de aproximacao")
    for m in metodos:
        for faixa, filtro in (("todas", None), ("perto", True), ("longe", False)):
            a, b, n = notas(R[m], R["real"], filtro)
            print(f"{m:12s} | {faixa:6s} | {n:5d} | {a:29.3f} | {b:.3f}")
    for m in metodos + ["real"]:
        todas = np.concatenate([c[2][1:] for c in R[m]])
        print(f"{m:12s} amostras no piso ({d_min:.0f} u): {100 * np.mean(todas <= d_min + 0.5):.2f}% | menor distancia p1 {np.quantile(todas, 0.01):.0f} u")
    tela = {}
    for m in metodos:
        k4 = [ks(np.concatenate([np.atleast_1d(c[3][x]) for c in R[m]]), np.concatenate([np.atleast_1d(c[3][x]) for c in R["real"]])) for x in ("vel", "desl", "tranco", "salto")]
        tela[m] = np.mean(k4)
        print(f"{m:12s} nota da tela (media dos 4 KS): {tela[m]:.3f}  [velocidade {k4[0]:.3f}, deslocamento {k4[1]:.3f}, tranco {k4[2]:.3f}, salto {k4[3]:.3f}]")
    # bootstrap por caminho da diferenca (proporcao - unidades) nas duas notas da distancia
    rng = np.random.default_rng(5)
    ids = np.array(sorted(set(c[0] for c in R["real"])))
    pos = {}
    for n, c in enumerate(R["real"]):
        pos.setdefault(c[0], []).append(n)
    difs = []
    for _ in range(300):
        idx = [n for i in rng.choice(ids, len(ids)) for n in pos[i]]
        sub = lambda L: [L[n] for n in idx]
        a0, b0, _ = notas(sub(R["unidades"]), sub(R["real"]))
        a1, b1, _ = notas(sub(R["proporcao"]), sub(R["real"]))
        difs.append(((a1 + b1) - (a0 + b0)) / 2)
    difs = np.array(difs)
    print(f"\nproporcao - unidades (media das 2 notas da distancia): {difs.mean():+.3f} (IC 95% {np.quantile(difs, 0.025):+.3f} a {np.quantile(difs, 0.975):+.3f}); proporcao melhor em {100 * (difs < 0).mean():.0f}% dos sorteios")


if __name__ == "__main__":
    main()
