"""Certificado de otimo local do desenho livre de uma duracao (quarta revisao).

Mexe cada numero um passo para cima e para baixo em 400 mil dias NOVOS (com o ruido do dia
incerto e os 25 cenarios de custo de troca de sens e aquecimento, um por dia): faixa de cada
rodada (+-0,01 e +-0,03 em ln), passo de cada rodada (+-0,005 e +-0,015), gama (+-0,05 e
+-0,15), GL0 (+-1 e +-2) e alvos (passa 1 alvo de uma rodada para outra, e +-1 numa rodada so
quando cabe no tempo). Se nenhum vizinho fica melhor alem do erro da simulacao, e otimo local.

Uso: python certificado_livre.py <otimo_livre_X.json> <minutos> [--sem-custo]
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import simular_v, sortear_adapt  # noqa: E402


def main():
    arq, orc = sys.argv[1], float(sys.argv[2])
    p = json.load(open(arq, encoding="utf-8"))["desenho"]
    N = 400000
    s = oe.Sorteio(N, 20261102, max_blocos=max(64, 4 * len(p["n"])), ruido_incerto=True)
    sem_custo = "--sem-custo" in sys.argv          # o mesmo modelo em que o desenho foi otimizado
    ad = None if sem_custo else sortear_adapt(N, semente=4040)
    print("modelo:", "sem custo de troca (o da otimizacao)" if sem_custo else "com custo de troca e aquecimento", flush=True)
    l0, m0, _ = simular_v(p, s, adapta=ad)
    print(f"desenho: n {p['n']} | {m0:.2f} min | perda {100 * l0.mean():.4f}% em {N} dias novos", flush=True)
    viz = []
    R = len(p["n"])
    for r in range(R):
        for d in (-0.03, -0.01, 0.01, 0.03):
            q = copy.deepcopy(p); q["Ws"][r] += d; q["W0"] = q["Ws"][0]; viz.append((f"faixa {r + 1} {d:+.2f}", q))
        for d in (-0.015, -0.005, 0.005, 0.015):
            q = copy.deepcopy(p); q["ks"][r] = max(0.005, q["ks"][r] + d); viz.append((f"passo {r + 1} {d:+.3f}", q))
        for d in (-1, 1):
            q = copy.deepcopy(p); q["n"][r] += d
            if q["n"][r] >= 2:
                viz.append((f"alvos {r + 1} {d:+d}", q))
        for r2 in range(R):
            if r2 != r:
                q = copy.deepcopy(p); q["n"][r] += 1; q["n"][r2] -= 1
                if q["n"][r2] >= 2:
                    viz.append((f"alvo da rodada {r2 + 1} para a {r + 1}", q))
    for d in (-0.15, -0.05, 0.05, 0.15):
        q = copy.deepcopy(p); q["gam"] += d; viz.append((f"gama {d:+.2f}", q))
    for d in (-2, -1, 1, 2):
        q = copy.deepcopy(p); q["gl0"] = max(1, q.get("gl0", 16) + d); viz.append((f"gl0 {d:+d}", q))
    melhor, piores_t = None, []
    cabem = 0
    for nome, q in viz:
        l, m, _ = simular_v(q, s, adapta=ad)
        if m > orc + 1e-9:
            continue
        cabem += 1
        dd = l - l0
        t = dd.mean() / (dd.std() / np.sqrt(N))
        piores_t.append((dd.mean(), t, nome))
        if melhor is None or dd.mean() < melhor[0]:
            melhor = (dd.mean(), t, nome)
    piores_t.sort()
    print(f"vizinhos que cabem no tempo: {cabem} de {len(viz)}")
    print("os 8 vizinhos que mais chegam perto (diferenca de perda, negativo = melhor que o desenho):")
    for dmean, t, nome in piores_t[:8]:
        print(f"  {nome:34s} {100 * dmean:+.5f} ponto (t = {t:+.1f})")
    ok = melhor[0] >= 0 or melhor[1] > -3
    print(f"\n{'OTIMO LOCAL' if ok else 'NAO E OTIMO LOCAL'}: melhor vizinho {melhor[2]} com {100 * melhor[0]:+.5f} ponto (t = {melhor[1]:+.1f})")


if __name__ == "__main__":
    main()
