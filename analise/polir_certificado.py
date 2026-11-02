"""Desce pelo certificado ate nenhum vizinho ganhar (quarta revisao).

A cada volta: 400 mil dias NOVOS (semente nova a cada volta, nunca usados antes), mede todos os
vizinhos do desenho (os mesmos do certificado_livre.py). Se o melhor vizinho ganha com t abaixo do
limite de Bonferroni (5% somando todos os vizinhos), o desenho vai para ele e a volta se repete
com dias novos. Para quando nenhum vizinho ganha alem do acaso: ai e otimo local certificado em
dias que a escolha nao viu.

Uso: python polir_certificado.py <otimo_livre_X.json> <minutos> [--sem-custo] [voltas] [--semente N] [--lote]
     --lote: junta na mesma volta todos os vizinhos que ganham com significancia e mexem em numeros diferentes
"""
import copy
import json
import os
import sys
from statistics import NormalDist

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import simular_v, sortear_adapt  # noqa: E402


def vizinhos(p):
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
    # movimentos do desenho inteiro (andam ao longo da crista gama x passo, que um numero so nao atravessa)
    for f in (0.95, 1.05):
        q = copy.deepcopy(p); q["gam"] *= f; q["ks"] = [k * f for k in q["ks"]]; viz.append((f"gama e todos os passos x{f}", q))
        q = copy.deepcopy(p); q["ks"] = [k * f for k in q["ks"]]; viz.append((f"todos os passos x{f}", q))
    for d in (-0.01, 0.01):
        q = copy.deepcopy(p); q["Ws"] = [w + d for w in q["Ws"]]; q["W0"] = q["Ws"][0]; viz.append((f"todas as faixas {d:+.2f}", q))
    # uma rodada a mais (repete a ultima e tira alvos das maiores para caber no mesmo tempo) ou a menos
    # (os alvos dela vao para as maiores); cada rodada custa 4 blocos x (alvos x 1,05 s + 6 s)
    q = copy.deepcopy(p)
    q["n"].append(q["n"][-1]); q["Ws"].append(q["Ws"][-1]); q["ks"].append(q["ks"][-1])
    a = p.get("adapt", 0)
    tirar = int(np.ceil(((q["n"][-1] + a) * 1.05 + 6) / 1.05))
    for _ in range(tirar):
        q["n"][int(np.argmax(q["n"][:-1]))] -= 1
    viz.append(("uma rodada a mais", q))
    if R > 2:
        q = copy.deepcopy(p)
        sobra = q["n"].pop(); q["Ws"].pop(); q["ks"].pop()
        dar = int(((sobra + p.get("adapt", 0)) * 1.05 + 6) // 1.05)
        for _ in range(dar):
            q["n"][int(np.argmin(q["n"]))] += 1
        viz.append(("uma rodada a menos", q))
    return viz


def main():
    arq, orc = sys.argv[1], float(sys.argv[2])
    sem_custo = "--sem-custo" in sys.argv
    voltas = next((int(a) for a in sys.argv[3:] if a.isdigit()), 6)
    # semente de partida: cada descida usa dias que nenhuma decisao anterior viu
    base = int(sys.argv[sys.argv.index("--semente") + 1]) if "--semente" in sys.argv else 7_000_000
    dado = json.load(open(arq, encoding="utf-8"))
    p = dado["desenho"]
    N = 400000
    for v in range(voltas):
        s = oe.Sorteio(N, base + 101 * v, max_blocos=max(64, 4 * (len(p["n"]) + 1)), ruido_incerto=True)   # +1: o vizinho com uma rodada a mais
        ad = None if sem_custo else sortear_adapt(N, semente=base + 1_000_000 + 101 * v)
        l0, m0, _ = simular_v(p, s, adapta=ad)
        res = []
        for nome, q in vizinhos(p):
            l, m, _ = simular_v(q, s, adapta=ad)
            if m > orc + 1e-9:
                continue
            d = l - l0
            res.append((d.mean(), d.mean() / (d.std() / np.sqrt(N)), nome, q))
        res.sort(key=lambda x: x[1])
        lim = NormalDist().inv_cdf(1 - 0.05 / len(res))      # Bonferroni: 5% somando todos os vizinhos (positivo)
        melhor = res[0]
        if "--lote" in sys.argv and melhor[1] < -lim:
            # junta todos os vizinhos que ganham com significancia e mexem em numeros diferentes
            usados, junto, nomes = set(), copy.deepcopy(p), []
            for dm, t, nome, q in res:
                if t >= -lim:
                    break
                if len(q["n"]) != len(p["n"]):      # rodada a mais / a menos: so sozinha, nunca junto
                    continue
                mex = {(c, i) for c in ("Ws", "ks", "n") for i in range(len(p[c])) if q[c][i] != p[c][i]}
                mex |= {(c, 0) for c in ("gam", "gl0") if q.get(c) != p.get(c)}
                if mex & usados:
                    continue
                usados |= mex
                nomes.append(nome)
                for c, i in mex:
                    if c in ("gam", "gl0"):
                        junto[c] = q[c]
                    else:
                        junto[c][i] = q[c][i]
            junto["W0"] = junto["Ws"][0]
            lj, mj, _ = simular_v(junto, s, adapta=ad)
            dj = lj - l0
            if len(nomes) > 1 and mj <= orc + 1e-9 and dj.mean() < melhor[0]:
                melhor = (dj.mean(), dj.mean() / (dj.std() / np.sqrt(N)), " + ".join(nomes), junto)
        print(f"volta {v + 1}: perda {100 * l0.mean():.4f}% | {len(res)} vizinhos | so mexe se t < {-lim:.2f} | melhor: {melhor[2]} "
              f"{100 * melhor[0]:+.5f} ponto (t = {melhor[1]:+.1f})", flush=True)
        if melhor[1] < -lim:
            p = melhor[3]
            print(f"  -> mexe: {melhor[2]} | alvos {p['n']} | faixas x" + ", ".join(f"{np.exp(w):.4f}" for w in p["Ws"])
                  + " | passos " + ", ".join(f"{k:.4f}" for k in p["ks"]) + f" | gama {p['gam']:.4f} | gl0 {p.get('gl0')}", flush=True)
        else:
            print("OTIMO LOCAL CERTIFICADO: nenhum vizinho ganha alem do acaso em dias novos", flush=True)
            break
    else:
        print("parou pelo numero de voltas (ainda mexendo)", flush=True)
    dado["desenho"] = p
    dado["certificado"] = {"voltas": v + 1, "fechou": bool(melhor[1] >= -lim)}
    json.dump(dado, open(arq, "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main()
