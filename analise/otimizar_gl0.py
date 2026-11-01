"""Quanto confiar no ruido de partida (graus de liberdade GL0 do prior) e no valor dele.

O PSA estima o ruido do dia juntando os pares medidos com um ruido de partida (SIGMA0 = 0,088
num bloco de 24, valendo GL0 graus de liberdade). Se o ruido verdadeiro fosse sempre 0,088,
confiar 100% na partida seria o melhor; por isso aqui o ruido verdadeiro de cada dia e
sorteado (x0,5 a x2, log-uniforme) e procura-se o GL0 (e o SIGMA0) com menor perda media.
Usa o desenho polido de 12 minutos.

Uso: python otimizar_gl0.py <desenho.json>
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402


def main():
    dado = json.load(open(sys.argv[1], encoding="utf-8"))
    p = dado["desenho"] if "desenho" in dado else next(iter(dado.values()))["desenho"]
    escalas = np.exp(np.linspace(np.log(0.5), np.log(2.0), 7))
    sorteios = [oe.Sorteio(40000, 900 + i) for i in range(len(escalas))]

    def perda(gl0, sigma0):
        oe.GL0, oe.SIGMA0 = gl0, sigma0
        return float(np.mean([oe.simular(p, s, escala_ruido=e)[0].mean() for s, e in zip(sorteios, escalas)]))

    print("GL0 (com SIGMA0 = 0,088):")
    melhor = None
    for gl0 in (1, 2, 3, 4, 6, 8, 10, 14, 20, 30, 50):
        v = perda(gl0, 0.088)
        melhor = (gl0, v) if melhor is None or v < melhor[1] else melhor
        print(f"  GL0 {gl0:3d}: perda media {100 * v:.4f}%", flush=True)
    print("SIGMA0 (com o melhor GL0):")
    melhor_s = None
    for s0 in (0.05, 0.065, 0.075, 0.088, 0.10, 0.12, 0.15):
        v = perda(melhor[0], s0)
        melhor_s = (s0, v) if melhor_s is None or v < melhor_s[1] else melhor_s
        print(f"  SIGMA0 {s0:.3f}: perda media {100 * v:.4f}%", flush=True)
    # refina GL0 inteiro em volta do melhor
    for gl0 in range(max(1, melhor[0] - 3), melhor[0] + 4):
        v = perda(gl0, melhor_s[0])
        if v < melhor[1]:
            melhor = (gl0, v)
    print(f"MELHOR: GL0 {melhor[0]}, SIGMA0 {melhor_s[0]} -> {100 * melhor[1]:.4f}% (atual GL0 6, SIGMA0 0,088: {100 * perda(6, 0.088):.4f}%)")


if __name__ == "__main__":
    main()
