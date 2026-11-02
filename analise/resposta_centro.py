"""Quanto o centro anda: com a melhor sens de verdade num lugar fixo, onde o PSA para?

Para cada duracao (os numeros exatos de otimo_orcamento_*_final.json), cada lugar da melhor
sens (de -40% a +40% da de partida), cada formato de curva e cada nivel de ruido, simula 20 mil
dias e mostra onde a sens do dia termina: a media (quanto do caminho andou) e a faixa de 80%
dos dias. "Andou 60%" = com a melhor sens a +20%, a do dia termina em media a +12%.

Uso: python resposta_centro.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DURACOES = ["8", "11.8", "16", "20", "25", "35"]
PCTS = [-40, -30, -20, -10, 0, 10, 20, 30, 40]
CURVAS = {0: "pico", 2: "torta", 1: "fundo chato"}


def onde_para(p, x0, tipo, escala_ruido, N=20000, semente=7):
    s = oe.Sorteio(N, semente)
    s.x0 = np.full(N, x0)
    s.tipo = np.full(N, tipo)
    s.f0 = oe.curva(s.x0, s.x0, s.tipo)
    perda, _, e = oe.simular(p, s, escala_ruido=escala_ruido)
    c = e + x0
    return c, perda


def main():
    pct = lambda v: 100 * (np.exp(v) - 1)
    for dur in DURACOES:
        p = json.load(open(os.path.join(BASE, f"otimo_orcamento_{dur}_final.json"), encoding="utf-8"))["desenho"]
        print(f"\n===== {dur} min: n {p['n']} | W0 x{np.exp(p['W0']):.4f} | k {p['k']} | rho {p['rho']} | gama {p['gam']} =====")
        for tipo, nome in CURVAS.items():
            for esc in (0.5, 1.0, 2.0):
                linha = []
                for pc in PCTS:
                    x0 = np.log(1 + pc / 100)
                    c, _ = onde_para(p, x0, tipo, esc)
                    m = pct(c.mean())
                    lo, hi = pct(np.quantile(c, 0.1)), pct(np.quantile(c, 0.9))
                    linha.append(f"{pc:+d}%->{m:+.0f}% [{lo:+.0f},{hi:+.0f}]")
                print(f"  {nome:11s} ruido x{esc:<3}: " + "  ".join(linha), flush=True)


if __name__ == "__main__":
    main()
