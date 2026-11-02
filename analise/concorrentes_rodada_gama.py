"""O livre (faixa e passo por rodada) ganha no modelo, mas com gama solto perde no ruido x2. Aqui:
  livre com gama fixo no atual: re-otimiza so faixas e passos, com o custo de troca e o aquecimento;
e confere ele, o livre sem custo e o livre com gama solto em dias novos e nos 9 cenarios de ataque,
todos com o custo de troca e o aquecimento.

Uso: python concorrentes_rodada_gama.py [duracao] [N]
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import andou, cenarios, otimizar, simular_v, sortear_adapt  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def ataques(p, atual):
    linha, piores = [], 0
    for i, (cn, scen, kw) in enumerate(cenarios()):
        ads = sortear_adapt(len(scen.x0), semente=500 + i)
        d = simular_v(p, scen, adapta=ads, **kw)[0] - simular_v(atual, scen, adapta=ads, **kw)[0]
        sig = d.mean() / (d.std() / np.sqrt(len(d)))
        linha.append(f"{cn}: {100 * d.mean():+.4f}{'*' if abs(sig) > 3 else ''}")
        piores += (d.mean() > 0) and sig > 3
    return piores, linha


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 120000
    atual = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    livre0 = json.load(open(os.path.join(BASE, "concorrentes_rodada.json"), encoding="utf-8"))["livre (faixa e passo por rodada)"]
    livre_c = json.load(open(os.path.join(BASE, "concorrentes_rodada_troca.json"), encoding="utf-8"))["livre"]
    R = len(atual["n"])
    s = oe.Sorteio(N, 4242, ruido_incerto=True)
    ad = sortear_adapt(N)
    p = copy.deepcopy(livre_c); p["gam"] = atual["gam"]
    chaves = [("Ws", r) for r in range(R)] + [("ks", r) for r in range(R)]
    fixo = otimizar(p, s, chaves, [0.04] * R + [0.015] * R, voltas=10, log="livre gama fixo", adapta=ad)[0]
    s2 = oe.Sorteio(300000, 99, ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    l0 = simular_v(atual, s2, adapta=ad2)[0]
    print(f"\nDIAS NOVOS com custo: atual {100 * l0.mean():.4f}%")
    for nome, q in (("livre otimizado sem custo (gama 1,9)", livre0), ("livre com custo, gama solto", livre_c), ("livre com custo, gama fixo 1,9", fixo)):
        l = simular_v(q, s2, adapta=ad2)[0]
        d = l - l0
        piores, linha = ataques(q, atual)
        print(f"  {nome:38s} {100 * l.mean():.4f}% | x atual {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f} | anda {andou(q):+.1f}% | "
              f"pior (com significancia) em {piores} de 9", flush=True)
        print("      faixas x" + ", ".join(f"{np.exp(w):.4f}" for w in q["Ws"]) + " | passos " + ", ".join(f"{k:.4f}" for k in q["ks"]) + f" | gama {q['gam']:.4f}")
        print("      " + " | ".join(linha), flush=True)
    json.dump({"livre_gama_fixo": fixo}, open(os.path.join(BASE, "concorrentes_rodada_gama.json"), "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main()
