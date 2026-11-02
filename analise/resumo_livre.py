"""Resumo dos desenhos finais da quarta revisao (o que vai para o app e para o COMO-FUNCIONA.md).

Para cada duracao: o desenho final (otimo_livre_<d>_semcusto_adapt0.json) e o anterior
(otimo_orcamento_<d>_final.json) nos mesmos 300 mil dias novos, com o ruido do dia incerto e o
custo de trocar de sens e o aquecimento: minutos, perda, erro tipico da sens, quanto o centro
anda com a melhor sens a +20%, e as faixas e passos de cada rodada.

Uso: python resumo_livre.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import andou, simular_v, sortear_adapt  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    ad = sortear_adapt(300000, semente=77)
    erro = lambda e: 100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1)
    num = lambda v: f"{v:.5f}".rstrip("0").rstrip(".").replace(".", ",")
    for dur in ("8", "11.8", "16", "20", "25", "35"):
        arq = os.path.join(BASE, f"otimo_livre_{dur}_semcusto_adapt0.json")
        if not os.path.exists(arq):
            continue
        p = json.load(open(arq, encoding="utf-8"))["desenho"]
        a = json.load(open(os.path.join(BASE, f"otimo_orcamento_{dur}_final.json"), encoding="utf-8"))["desenho"]
        s = oe.Sorteio(300000, 99, max_blocos=max(64, 4 * max(len(p["n"]), len(a["n"]))), ruido_incerto=True)
        l1, m1, e1 = simular_v(p, s, adapta=ad)
        l0, m0, e0 = simular_v(a, s, adapta=ad)
        d = l1 - l0
        print(f"{dur} min: {m1:.2f} min | {len(p['n'])} rodadas | perda {100 * l0.mean():.4f}% -> {100 * l1.mean():.4f}% "
              f"(dif {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f}) | erro {erro(e0):.1f}% -> {erro(e1):.1f}% | "
              f"anda (melhor a +20%): {andou(a):+.1f}% -> {andou(p):+.1f}%")
        print(f"   alvos {', '.join(map(str, p['n']))} | gama {num(p['gam'])} | GL0 {p['gl0']} | adaptacao {p['adapt']}")
        print(f"   faixas x{' · '.join(num(np.exp(w)) for w in p['Ws'])}")
        print(f"   passos {' · '.join(num(k) for k in p['ks'])}", flush=True)


if __name__ == "__main__":
    main()
