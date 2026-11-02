"""Concorrentes da CONTINUACAO do caminho do alvo, testados contra o futuro real escondido.

Pega os inimigos que ficaram vivos 2,5 s inteiros, corta o caminho em T (0,25 / 0,5 / 1,0 s),
esconde o resto e deixa cada metodo continuar por 0,75 s:
  emenda (atual, perfil.py): movimento real de outro inimigo vivo naquele instante, mesmo
          tipo, mesma faixa de distancia, cujo PROXIMO passo mais parece o ultimo passo real do
          alvo; quando o doador acaba, escolhe outro. Variantes: a antiga (velocidade media dos 2
          ultimos passos), casando os dois, e misturando o passo nas primeiras 2/4/8 amostras;
  emenda com doador sorteado: o mesmo, mas sem casar a velocidade (mostra se casar ajuda);
  parado: o alvo congela;
  velocidade morrendo: segue com a ultima velocidade, caindo pela metade a cada X s (o X
          que mais se parece com o real, escolhido no proprio teste: e o melhor caso dele);
  aleatorio (OU): velocidade em unidades do jogo que volta para zero com ruido, ajustado aos
          caminhos reais e convertido pela distancia de cada alvo.
O que importa e o JEITO do movimento (a dificuldade), nao acertar o ponto. Compara com o futuro
real (distancia de Kolmogorov-Smirnov: 0 = igual, 1 = nada a ver):
  velocidade na tela, deslocamento em 0,5 s, tranco (mudanca de velocidade de uma amostra para
  a outra: zigue-zague) e o salto de velocidade na hora da emenda (se a costura aparece).
O erro de posicao em 0,5 s vai so como referencia (quem fica parado "acerta" mais o ponto).

Uso: python concorrentes_caminho.py <duelos.json>
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from perfil import HZ, N_TRAJ, passo_linear, velocidade_linear  # noqa: E402

FUT = int(0.75 * HZ)


def ks(a, b):
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    v = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, v, side="right") / len(a) - np.searchsorted(b, v, side="right") / len(b))))


def emenda(i, k, trs, dss, tipos, nreal, d_min, rng=None, casar="media2", mistura=0, radial="unidades", com_ds=False):
    """Continuacao do caminho i a partir da amostra k, com a mesma regra do perfil.py.
    casar: "media2" (antiga: velocidade media dos 2 ultimos passos), "proximo" (o proximo passo
    do doador parecido com o ultimo passo real) ou "ambos" (soma das duas diferencas).
    mistura: nas primeiras B amostras depois de cada costura, o passo vai do ultimo passo real
    para o do doador aos poucos (0 = atual, sem mistura).
    radial: "unidades" (atual: o alvo chega mais perto o mesmo tanto de unidades que o doador)
    ou "proporcao" (a distancia muda na mesma proporcao que a do doador)."""
    tr = [list(p) for p in trs[i][:k + 1]]
    ds = list(dss[i][:k + 1])
    alvo = k + 1 + FUT
    while len(tr) < alvo:
        kk = len(tr) - 1
        v = velocidade_linear(tr, ds, kk)
        vivos = [j for j in range(len(trs)) if j != i and nreal[j] > kk + 1]
        cands = []
        for faixa in (1.3, 1.6, 2.2, None):
            for mesmo_tipo in (True, False):
                cands = [j for j in vivos
                         if (not mesmo_tipo or tipos[j] == tipos[i])
                         and (faixa is None or 1 / faixa <= dss[j][kk] / max(1.0, ds[-1]) <= faixa)]
                if len(cands) >= 10:
                    break
            if len(cands) >= 10:
                break
        if not cands:
            cands = vivos
        ultimo = passo_linear(tr, ds, kk)                 # a mesma conta do perfil.py

        def prox(j):
            return passo_linear(trs[j], dss[j], kk + 1)
        if rng is not None:
            j = cands[int(rng.integers(len(cands)))]
        elif casar == "media2":
            j = cands[int(np.argmin([np.hypot(*(velocidade_linear(trs[j], dss[j], kk) - v)) for j in cands]))]
        elif casar == "proximo":
            j = cands[int(np.argmin([np.hypot(*(prox(j) - ultimo)) for j in cands]))]
        else:
            j = cands[int(np.argmin([np.hypot(*(velocidade_linear(trs[j], dss[j], kk) - v)) + np.hypot(*(prox(j) - ultimo)) for j in cands]))]
        passo_real = np.asarray(tr[kk]) - np.asarray(tr[kk - 1]) if kk >= 1 else np.zeros(2)
        for b, m in enumerate(range(kk + 1, min(N_TRAJ, nreal[j]))):
            passo = (np.asarray(trs[j][m]) - np.asarray(trs[j][m - 1])) * (dss[j][m - 1] / max(1.0, ds[-1]))
            if mistura and b < mistura:
                a = (b + 1) / (mistura + 1)
                passo = (1 - a) * passo_real + a * passo
            if radial == "unidades":
                d_novo = max(d_min, ds[-1] + (dss[j][m] - dss[j][m - 1]))
            else:
                d_novo = max(d_min, ds[-1] * dss[j][m] / max(1.0, dss[j][m - 1]))
            tr.append([tr[-1][0] + passo[0], tr[-1][1] + passo[1]])
            ds.append(d_novo)
            if len(tr) >= alvo:
                break
    if com_ds:
        return np.array(tr[k:alvo]), np.array(ds[k:alvo])
    return np.array(tr[k:alvo])


def medidas(c, v_antes):
    """c: continuacao (FUT+1 pontos, em graus). v_antes: velocidade da ultima amostra real (graus/s, 2 eixos)."""
    vv = np.diff(c, axis=0) * HZ
    return {"vel": np.hypot(*vv.T), "desl": [np.hypot(*(c[16] - c[0]))],
            "tranco": np.hypot(*np.diff(vv, axis=0).T), "salto": [np.hypot(*(vv[0] - v_antes))]}


def main():
    d = pd.DataFrame(json.load(open(sys.argv[1], encoding="utf-8"))["duelos"])
    d = d[~d["sem_mira"] & ~d["luneta"] & ~d["franco"]].reset_index(drop=True)
    trs = [[list(p) for p in t] for t in d["traj"]]
    dss = [list(map(float, x)) for x in d["dists"]]
    tipos = d["tipo"].tolist()
    nreal = [len(t) for t in trs]
    d_min = min(min(x) for x in dss if len(x))
    completos = [i for i, n in enumerate(nreal) if n >= N_TRAJ]
    # OU em unidades do jogo: v(k+1) = phi v(k) + ruido, por eixo (u/s); convertido por distancia
    vl = []
    for t, ds in zip(trs, dss):
        if len(t) > 3:
            a = np.asarray(t)
            vl.append(np.diff(a, axis=0) * HZ * math.pi / 180 * np.asarray(ds[1:])[:, None])
    v0 = np.concatenate([x[:-1] for x in vl]); v1 = np.concatenate([x[1:] for x in vl])
    phi = float((v0 * v1).sum() / (v0 * v0).sum())
    sig = float(np.std(v1 - phi * v0))
    meias = [0.05, 0.1, 0.2, 0.35, 0.5, 1.0, 2.0, 1e9]
    rng = np.random.default_rng(7)
    rng_doador = np.random.default_rng(8)
    variantes = {"emenda antiga (velocidade media)": {}, "emenda casando o proximo passo (atual)": {"casar": "proximo"}, "emenda casando os dois": {"casar": "ambos"},
                 "emenda + mistura 2": {"mistura": 2}, "emenda + mistura 4": {"mistura": 4}, "emenda + mistura 8": {"mistura": 8},
                 "emenda casando os dois + mistura 2": {"casar": "ambos", "mistura": 2}}
    metodos = list(variantes) + ["emenda com doador sorteado", "parado", "aleatorio (OU)"] + [f"velocidade morrendo {m:g} s" for m in meias]
    res = {m: {"vel": [], "desl": [], "tranco": [], "salto": [], "erro": []} for m in metodos}
    real = {"vel": [], "desl": [], "tranco": [], "salto": []}
    porcaso = {m: [] for m in metodos}            # (caminho, medidas) para o bootstrap
    porcaso_real = []
    for T in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5):
        k = int(T * HZ)
        for i in completos:
            tr = np.asarray(trs[i]); ds = np.asarray(dss[i])
            futuro = tr[k:k + FUT + 1]
            v_antes = (tr[k] - tr[k - 1]) * HZ
            mr = medidas(futuro, v_antes)
            porcaso_real.append((i, mr))
            for kk, vals in mr.items():
                real[kk].extend(vals)
            cont = {nome: emenda(i, k, trs, dss, tipos, nreal, d_min, **kw) for nome, kw in variantes.items()}
            cont["emenda com doador sorteado"] = emenda(i, k, trs, dss, tipos, nreal, d_min, rng_doador)
            cont["parado"] = np.repeat(tr[k][None, :], FUT + 1, 0)
            v_ang = (tr[k] - tr[max(0, k - 2)]) / ((k - max(0, k - 2)) / HZ)
            tt = np.arange(FUT + 1) / HZ
            for m in meias:
                tau = m / math.log(2)
                cont[f"velocidade morrendo {m:g} s"] = tr[k] + v_ang[None, :] * (tau * (1 - np.exp(-tt / tau)))[:, None]
            p = [tr[k].copy()]
            vv = velocidade_linear(trs[i], dss[i], k)
            for _ in range(FUT):
                vv = phi * vv + sig * rng.standard_normal(2)
                p.append(p[-1] + vv / HZ / ds[k] * 180 / math.pi)
            cont["aleatorio (OU)"] = np.array(p)
            for m in metodos:
                c = cont[m]
                mc = medidas(c, v_antes)
                porcaso[m].append((i, mc))
                for kk, vals in mc.items():
                    res[m][kk].extend(vals)
                res[m]["erro"].append(np.hypot(*(c[16] - futuro[16])))
    print(f"caminhos completos: {len(completos)} (x 6 cortes) | OU em unidades: phi {phi:.3f} por amostra, ruido {sig:.1f} u/s")
    print(f"{'metodo':40s} | {'velocidade':>10s} | {'desloc 0,5 s':>12s} | {'tranco':>7s} | {'salto na emenda':>15s} | media dos 4 | erro de posicao 0,5 s")
    linhas = []
    for m in metodos:
        k4 = [ks(res[m][x], real[x]) for x in ("vel", "desl", "tranco", "salto")]
        linhas.append((np.mean(k4), m, k4, np.median(res[m]["erro"])))
    for media, m, k4, erro in sorted(linhas):
        md = [np.median(res[m][x]) for x in ("vel", "desl", "tranco", "salto")]
        print(f"{m:40s} | {k4[0]:10.3f} | {k4[1]:12.3f} | {k4[2]:7.3f} | {k4[3]:15.3f} | {media:11.3f} | {erro:.2f} graus | medianas {md[0]:.1f} {md[1]:.2f} {md[2]:.1f} {md[3]:.1f}")
    # bootstrap por caminho: sorteia caminhos com reposicao e refaz as 4 distancias
    rngb = np.random.default_rng(99)
    ids = np.array(sorted(set(i for i, _ in porcaso_real)))
    pos = {i: [n for n, (ii, _) in enumerate(porcaso_real) if ii == i] for i in ids}
    top = [m for _, m, _, _ in sorted(linhas)[:6]]
    for obrig in ("emenda casando o proximo passo (atual)", "emenda antiga (velocidade media)"):
        if obrig not in top:
            top.append(obrig)
    B = 300
    medias = {m: [] for m in top}
    for _ in range(B):
        esc = rngb.choice(ids, len(ids))
        idx = [n for i in esc for n in pos[i]]
        cat = lambda lst, x: np.concatenate([np.atleast_1d(lst[n][1][x]) for n in idx])
        for m in top:
            medias[m].append(np.mean([ks(cat(porcaso[m], x), cat(porcaso_real, x)) for x in ("vel", "desl", "tranco", "salto")]))
    base = np.array(medias["emenda casando o proximo passo (atual)"])
    print("\nbootstrap por caminho (300 sorteios): media das 4 distancias, diferenca para o atual (negativo = melhor que o atual)")
    for m in top:
        dd = np.array(medias[m]) - base
        print(f"  {m:40s} {np.mean(medias[m]):.3f} | dif {dd.mean():+.3f} (IC 95% {np.quantile(dd, 0.025):+.3f} a {np.quantile(dd, 0.975):+.3f}) | melhor que o atual em {100 * (dd < 0).mean():.0f}% dos sorteios")
    print(f"{'(real)':40s} | mediana: velocidade {np.median(real['vel']):.1f} graus/s, deslocamento {np.median(real['desl']):.2f} graus, "
          f"tranco {np.median(real['tranco']):.1f} graus/s, salto {np.median(real['salto']):.1f} graus/s")


if __name__ == "__main__":
    main()
