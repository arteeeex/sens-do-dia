"""O desenho livre de cada duracao ganha do atual tambem fora do modelo? (quarta revisao)

Para cada duracao com otimo_livre_<d>[_gfixo].json: perda em 300 mil dias novos e nos 9 cenarios
de ataque (ruido x0,5/x1,5/x2, curva x0,5/x2, curvas que o otimizador nao viu, melhor sens ate
+-60%, sem cansaco), todos com o custo de trocar de sens e o aquecimento. Conta em quantos o livre
fica pior que o atual com significancia (|t| > 3).

Uso: python robustez_livre.py [sufixo] [duracoes]   (sufixo: "", "_gfixo", "_semcusto", "_semcusto_adapt0"; duracoes: 8,11.8,...)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import andou, cenarios, simular_v, sortear_adapt  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    suf = sys.argv[1] if len(sys.argv) > 1 else ""
    so = sys.argv[2].split(",") if len(sys.argv) > 2 else None      # so estas duracoes (ex.: 11.8,16)
    ad2 = sortear_adapt(300000, semente=77)
    for dur in ("8", "11.8", "16", "20", "25", "35"):
        arq = os.path.join(BASE, f"otimo_livre_{dur}{suf}.json")
        if not os.path.exists(arq) or (so and dur not in so):
            continue
        atual = json.load(open(os.path.join(BASE, f"otimo_orcamento_{dur}_final.json"), encoding="utf-8"))["desenho"]
        p = json.load(open(arq, encoding="utf-8"))["desenho"]
        mb = max(64, 4 * max(len(p["n"]), len(atual["n"])))   # ate 16 rodadas: os sorteios de sempre
        sc = cenarios(mb)
        s2 = oe.Sorteio(300000, 99, max_blocos=mb, ruido_incerto=True)
        l0 = simular_v(atual, s2, adapta=ad2)[0]; l1 = simular_v(p, s2, adapta=ad2)[0]
        d = l1 - l0
        linha, piores = [], 0
        for i, (cn, scen, kw) in enumerate(sc):
            ads = sortear_adapt(len(scen.x0), semente=500 + i)
            dd = simular_v(p, scen, adapta=ads, **kw)[0] - simular_v(atual, scen, adapta=ads, **kw)[0]
            t = dd.mean() / (dd.std() / np.sqrt(len(dd)))
            linha.append(f"{cn}: {100 * dd.mean():+.4f}{'*' if abs(t) > 3 else ''}")
            piores += (dd.mean() > 0) and t > 3
        print(f"{dur:>5s} min: dias novos {100 * l1.mean():.4f}% contra {100 * l0.mean():.4f}% (dif {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f}) | "
              f"anda {andou(p):+.1f}% (atual {andou(atual):+.1f}%) | pior em {piores} de 9", flush=True)
        print("      " + " | ".join(linha), flush=True)


if __name__ == "__main__":
    main()
