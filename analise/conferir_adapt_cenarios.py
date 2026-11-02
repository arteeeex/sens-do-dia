"""0 ou 1 alvo de adaptacao por bloco no desenho livre, cenario a cenario (quarta revisao).

Mesmo caminho do desenho robusto: com 0 alvos de adaptacao sobra tempo, e os alvos de cada rodada
sao re-ajustados no modelo sem custo (como o desenho foi otimizado). Depois os dois sao medidos em
300 mil dias novos: sem custo, com a mistura dos 25 cenarios, e em cada custo de troca de sens
sozinho (do nenhum ao mais forte: 25% mais lento sumindo em 6 alvos), mais o pior caso junto
(aquecimento forte e troca forte).

Uso: python conferir_adapt_cenarios.py <otimo_livre_X.json> <minutos>
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import TR, simular_v, sortear_adapt  # noqa: E402
from otimizar_livre import otimizar  # noqa: E402


def fixo(N, aq, tr):
    return {"aq_amp": np.full(N, aq[0]), "aq_tau": np.full(N, float(aq[1])), "tr_amp": np.full(N, tr[0]), "tr_k": np.full(N, float(tr[1]))}


def main():
    arq, orc = sys.argv[1], float(sys.argv[2])
    p1 = json.load(open(arq, encoding="utf-8"))["desenho"]
    s = oe.Sorteio(120000, 4242, ruido_incerto=True)
    p0 = copy.deepcopy(p1); p0["adapt"] = 0
    p0, _ = otimizar(p0, s, None, orc, passes=6, passo_w=0.0, passo_k=0.0, passo_g=0.0, gama_fixo=True)
    N = 300000
    s2 = oe.Sorteio(N, 99, ruido_incerto=True)
    print(f"adaptacao 1: alvos {p1['n']} ({simular_v(p1, s2)[1]:.2f} min) | adaptacao 0: alvos {p0['n']} ({simular_v(p0, s2)[1]:.2f} min), gl0 {p0.get('gl0')}")
    casos = [("sem custo", None), ("mistura dos 25 cenarios", sortear_adapt(N, semente=77))]
    for tr in TR:
        casos.append((f"troca {int(100 * tr[0])}% sumindo em {tr[1]} alvos (sem aquecimento)", fixo(N, (0.0, 15), tr)))
    casos.append(("pior caso: aquecimento 25%/50 alvos + troca 25%/6 alvos", fixo(N, (0.25, 50), (0.25, 6))))
    for nome, ad in casos:
        l1 = simular_v(p1, s2, adapta=ad)[0]; l0 = simular_v(p0, s2, adapta=ad)[0]
        d = l0 - l1
        print(f"  {nome:58s} adapt 1: {100 * l1.mean():.4f}% | adapt 0: {100 * l0.mean():.4f}% | 0 - 1: {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(N):.4f}", flush=True)
    json.dump({"desenho": p0}, open(arq.replace(".json", "_adapt0.json"), "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main()
