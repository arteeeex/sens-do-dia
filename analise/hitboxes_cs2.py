"""Separa as hitboxes do CS2 (malha physics_group_playerflesh) em pecas e mede cada uma.

Cada peca conexa da malha e uma forma de hit (capsula). Para cada uma: centro, eixo
principal (PCA), comprimento, raio (mediana da distancia ao eixo) e caixa.
Grava hitboxes.json com as capsulas (pontas a, b e raio) em unidades do CS2, z para cima.

Uso: python hitboxes_cs2.py <fisica.glb> <saida.json>
"""
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ler_glb import abrir, acessor  # noqa: E402


def componentes(ntri, idx, nvert):
    pai = np.arange(nvert)

    def acha(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for t in range(ntri):
        a, b, c = idx[3 * t: 3 * t + 3]
        ra, rb, rc = acha(a), acha(b), acha(c)
        pai[rb] = ra
        pai[acha(rc)] = ra
    raiz = np.array([acha(i) for i in range(nvert)])
    return raiz


def main():
    js, binario = abrir(sys.argv[1])
    p = js["meshes"][0]["primitives"][0]
    pos = acessor(js, binario, p["attributes"]["POSITION"]).astype(np.float64)
    idx = acessor(js, binario, p["indices"]).reshape(-1).astype(np.int64)
    # soldar vertices repetidos (mesma posicao) antes de separar as pecas
    chave = np.round(pos, 3)
    _, unico, inv = np.unique(chave, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    pos_u = pos[unico]
    idx_u = inv[idx]
    raiz = componentes(len(idx_u) // 3, idx_u, len(pos_u))
    pecas = []
    for r in np.unique(raiz):
        P = pos_u[raiz == r]
        if len(P) < 8:
            continue
        c = P.mean(0)
        u, s, vt = np.linalg.svd(P - c, full_matrices=False)
        eixo = vt[0]
        proj = (P - c) @ eixo
        perp = (P - c) - np.outer(proj, eixo)
        dist = np.linalg.norm(perp, axis=1)
        raio = float(np.median(dist[np.abs(proj) < 0.5 * np.abs(proj).max()])) if len(P) > 20 else float(dist.max())
        meio = proj.max() - raio, proj.min() + raio      # pontas do segmento da capsula
        a = c + eixo * min(meio[1], 0) if meio[1] < 0 else c
        b = c + eixo * max(meio[0], 0) if meio[0] > 0 else c
        pecas.append({"n": int(len(P)), "centro": c.round(2).tolist(), "eixo": eixo.round(3).tolist(),
                      "comprimento_total": round(float(proj.max() - proj.min()), 2), "raio": round(raio, 2),
                      "a": a.round(2).tolist(), "b": b.round(2).tolist(),
                      "min": P.min(0).round(1).tolist(), "max": P.max(0).round(1).tolist()})
    pecas.sort(key=lambda q: -q["centro"][2])
    print(f"{len(pecas)} pecas (de cima para baixo):")
    for i, q in enumerate(pecas):
        print(f"{i:2d} centro {q['centro']} raio {q['raio']:5.2f} comprimento {q['comprimento_total']:5.2f} "
              f"eixo {q['eixo']} caixa {q['min']}..{q['max']} ({q['n']} vert)")
    json.dump({"unidade": "CS2 (polegada), z para cima, pose de referencia", "pecas": pecas},
              open(sys.argv[2], "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
