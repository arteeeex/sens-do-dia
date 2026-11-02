"""Quantos alvos de adaptacao por bloco no desenho livre? (quarta revisao)

O alvo de adaptacao so serve se trocar de sens custa (os primeiros alvos depois da troca saem
mais lentos). Entao a conta e com os 25 cenarios de custo de troca e aquecimento. Para cada
numero de alvos de adaptacao (0 a 3), os alvos por rodada sao re-ajustados para caber no mesmo
tempo (descida coordenada so nos alvos), e a perda e medida em 300 mil dias novos.

Uso: python conferir_adapt_livre.py <otimo_livre_X.json> <minutos>
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
from otimizar_livre import otimizar  # noqa: E402


def main():
    arq, orc = sys.argv[1], float(sys.argv[2])
    p = json.load(open(arq, encoding="utf-8"))["desenho"]
    s = oe.Sorteio(60000, 4242, ruido_incerto=True)
    ad = sortear_adapt(60000)
    s2 = oe.Sorteio(300000, 99, ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    base = None
    for a in (0, 1, 2, 3):
        q = copy.deepcopy(p); q["adapt"] = a
        q, _ = otimizar(q, s, ad, orc, passes=6, passo_w=0.0, passo_k=0.0, passo_g=0.0, gama_fixo=True)
        l, m, _ = simular_v(q, s2, adapta=ad2)
        if base is None:
            base = (a, l)
        print(f"adaptacao {a}: alvos {q['n']} ({m:.2f} min) | perda com custo {100 * l.mean():.4f}%", flush=True)
        if a == p.get("adapt", 1):
            atual = l
    print("\n(a do desenho:", p.get("adapt", 1), ")")


if __name__ == "__main__":
    main()
