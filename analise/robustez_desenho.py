"""O desenho otimo continua melhor que o atual se o mundo for diferente do modelo?

Compara, com os mesmos sorteios, o desenho atual e os otimos de cada tempo (otimo_orcamento_*_final.json)
com ruido x0,5 / x1 / x1,5 / x2, curva x0,5 / x1 / x2, com e sem cansaco, e a melhor sens
espalhada mais (entre -60% e +60%). Mostra a perda de cada um e a melhora sobre o atual.

Uso: python robustez_desenho.py
"""
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from otimizar_exato import LN3, Sorteio, simular  # noqa: E402


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    desenhos = {"atual (36,36,24,12,12; x3; 1/4; 1/2; gama 1)":
                {"n": [36, 36, 24, 12, 12], "W0": float(LN3), "k": 0.25, "rho": 0.5, "gam": 1.0, "adapt": 3, "aquec": 20}}
    arqs = glob.glob(os.path.join(base, "otimo_orcamento_*_final.json"))
    for f in sorted(arqs, key=lambda x: float(os.path.basename(x).split("_")[2])):
        orc = float(os.path.basename(f).split("_")[2])
        desenhos[f"otimo {orc:g} min"] = json.load(open(f, encoding="utf-8"))["desenho"]
    s = Sorteio(100000, 4242)
    larga = Sorteio(100000, 4243)
    larga.x0 = np.random.default_rng(1).uniform(-0.6, 0.6, len(larga.x0))
    from otimizar_exato import curva
    larga.f0 = curva(larga.x0, larga.x0, larga.tipo)
    outras = Sorteio(100000, 4244)
    outras.tipo = 3 + (np.arange(len(outras.x0)) % 2)          # curvas que o otimizador nao viu
    outras.f0 = curva(outras.x0, outras.x0, outras.tipo)
    cenarios = [("modelo (com cansaco)", s, dict()), ("sem cansaco", s, dict(cansaco=False)),
                ("curvas novas (reta/ingreme)", outras, dict()),
                ("ruido x0,5", s, dict(escala_ruido=0.5)), ("ruido x1,5", s, dict(escala_ruido=1.5)),
                ("ruido x2", s, dict(escala_ruido=2.0)), ("curva x0,5 (mais plana)", s, dict(escala_curva=0.5)),
                ("curva x2 (mais funda)", s, dict(escala_curva=2.0)), ("melhor sens ate +-60%", larga, dict())]
    nomes = list(desenhos)
    print(f"{'cenario':26s} | " + " | ".join(f"{n[:16]:>16s}" for n in nomes))
    for rot, ss, kw in cenarios:
        ls = []
        for n in nomes:
            l, m, _ = simular(desenhos[n], ss, **kw)
            ls.append(100 * l.mean())
        print(f"{rot:26s} | " + " | ".join(f"{v:15.4f}%" for v in ls))
    print("\nminutos: " + " | ".join(f"{n[:16]}: {simular(desenhos[n], s)[1]:.2f}" for n in nomes))


if __name__ == "__main__":
    main()
