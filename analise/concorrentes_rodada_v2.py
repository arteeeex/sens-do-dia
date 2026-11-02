"""Proxima passada (quarta revisao): alguem ganha do desenho livre novo?

Parte do desenho escolhido (otimo_livre_<d>...json) e tenta:
  momento: o centro anda w * k_r * faixa_r + beta * (o que andou antes), beta otimizado;
  todas as sondas mais perto / mais longe: todas as faixas x0,8 / x0,9 / x1,1 / x1,2, com os passos
          e o gama re-otimizados para cada uma (o certificado so mexe uma faixa de cada vez);
  todos os passos maiores / menores: todos os passos x0,8 / x1,25, com o gama re-otimizado.
Mesmo modelo da otimizacao (sem custo de troca), conferido em 300 mil dias novos com o custo de
troca e nos 9 cenarios de ataque. Se nada ganhar, a regra da rodada fecha.

Uso: python concorrentes_rodada_v2.py <otimo_livre_X.json>
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import cenarios, otimizar, simular_v, sortear_adapt  # noqa: E402


def main():
    p = json.load(open(sys.argv[1], encoding="utf-8"))["desenho"]
    R = len(p["n"])
    s = oe.Sorteio(120000, 4242, ruido_incerto=True)
    cands = {}
    q = copy.deepcopy(p); q["momento"] = 0.1
    cands["momento"] = otimizar(q, s, ["momento"], [0.1], voltas=6, log="momento")[0]
    for f in (0.8, 0.9, 1.1, 1.2):
        q = copy.deepcopy(p); q["Ws"] = [w * f for w in p["Ws"]]; q["W0"] = q["Ws"][0]
        chaves = [("ks", r) for r in range(R)] + ["gam"]
        cands[f"todas as faixas x{f}"] = otimizar(q, s, chaves, [0.015] * R + [0.15], voltas=6, log=f"faixas x{f}")[0]
    for f in (0.8, 1.25):
        q = copy.deepcopy(p); q["ks"] = [k * f for k in p["ks"]]
        cands[f"todos os passos x{f}"] = otimizar(q, s, ["gam"], [0.15], voltas=6, log=f"passos x{f}")[0]
    s2 = oe.Sorteio(300000, 99, ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    l0 = simular_v(p, s2)[0]; l0c = simular_v(p, s2, adapta=ad2)[0]
    print(f"\ndesenho escolhido: {100 * l0.mean():.4f}% sem custo | {100 * l0c.mean():.4f}% com custo (300 mil dias novos)")
    sc = cenarios()
    for nome, q in cands.items():
        d = simular_v(q, s2)[0] - l0
        dc = simular_v(q, s2, adapta=ad2)[0] - l0c
        piores = 0
        linha = []
        for i, (cn, scen, kw) in enumerate(sc):
            ads = sortear_adapt(len(scen.x0), semente=500 + i)
            dd = simular_v(q, scen, adapta=ads, **kw)[0] - simular_v(p, scen, adapta=ads, **kw)[0]
            t = dd.mean() / (dd.std() / np.sqrt(len(dd)))
            linha.append(f"{cn}: {100 * dd.mean():+.4f}{'*' if abs(t) > 3 else ''}")
            piores += (dd.mean() > 0) and t > 3
        print(f"  {nome:26s} sem custo {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f} | com custo {100 * dc.mean():+.4f} | "
              f"pior que o escolhido em {piores} de 9 ataques", flush=True)
        print("      " + " | ".join(linha), flush=True)


if __name__ == "__main__":
    main()
