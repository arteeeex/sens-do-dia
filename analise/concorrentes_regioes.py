"""Concorrentes da MEDIDA DAS FRONTEIRAS do corpo (pernas|barriga, barriga|peito, peito|cabeca).

A altura do acerto medida na demo tem erro (a posicao do alvo nao e a da compensacao de lag).
O erro borra a fronteira; o ponto de 50% (probit) escorrega para o lado com menos tiros.
Metodos:
  probit:      ponto de 50% de P(parte de cima | altura medida), sem correcao;
  EM atual:    maxima verossimilhanca com densidade livre (o codigo do medir_regioes.py);
  meio:        meio a meio entre probit e EM atual (o que o boneco.py usa na barriga|peito);
  EM justo:    a mesma ideia do EM, mas todo candidato com as mesmas iteracoes e grade fina;
  probit corrigido (Tweedie): se a densidade dos tiros sobe com a altura (inclinacao b do log
               da densidade), o ponto de 50% cai b*s^2 abaixo da fronteira (s = borrao, que o
               proprio probit mede pela largura). Fronteira = ponto de 50% + b*s^2.
Teste: simulacoes com a fronteira verdadeira conhecida, densidade de tiros realista (a das
demos, alisada ou desborrada), o mesmo numero de balas e varios tipos de borrao. Mede vies e
erro tipico de cada metodo. Depois aplica todos nos dados reais.

Uso: python concorrentes_regioes.py <pasta_das_demos> <cache.pkl> [replicas] [cenario 0-7 | todos] [saida.json]
     python concorrentes_regioes.py resumo <saida_0.json> ... <saida_7.json>   (junta os cenarios)
     python concorrentes_regioes.py janela <pasta> <cache.pkl> [replicas]       (escolhe o w do Tweedie)
     python concorrentes_regioes.py validar <pasta> <cache.pkl> <w ou w1,w2,w3>  (confere o w nos sorteios da comparacao)
"""
import json
import math
import os
import sys
import time
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import medir_regioes as mr  # noqa: E402

JAN = ((0, (15, 45)), (1, (35, 56)), (2, (50, 68)))
NOMES = ["pernas|barriga", "barriga|peito", "peito|cabeca"]


def dados(pasta, cache):
    if os.path.exists(cache):
        B = pd.read_pickle(cache)
    else:
        B = mr.ler(pasta)
        B.to_pickle(cache)
    E = B[B["hitgroup"].isin(list(mr.ROTULO)) & (B["lado"].abs() < 3.5)]
    return E["altura"].to_numpy(float), E["hitgroup"].map(mr.ROTULO).to_numpy(int)


def probit(z, y, c0):
    """Igual ao probit_simples do medir_regioes.py, devolvendo tambem a largura (borrao)."""
    cs = np.arange(c0 - 8, c0 + 8, 0.05)
    melhor, arg, arg_s = -np.inf, c0, 4.0
    for sg in np.exp(np.linspace(np.log(0.3), np.log(8), 40)):
        q = np.clip(1 / (1 + np.exp(-1.702 * (z[None, :] - cs[:, None]) / sg)), 1e-9, 1 - 1e-9)
        ll = (y[None, :] * np.log(q) + (1 - y[None, :]) * np.log(1 - q)).sum(axis=1)
        i = int(np.argmax(ll))
        if ll[i] > melhor:
            melhor, arg, arg_s = ll[i], float(cs[i]), float(sg)
    return arg, arg_s


def inclinacao_log(z_todos, centro, w=6.0):
    """b = derivada do log da densidade perto do centro: exponencial truncada em [centro-w, centro+w]
    por maxima verossimilhanca (media observada = media do modelo)."""
    x = z_todos[(z_todos > centro - w) & (z_todos < centro + w)] - centro
    if len(x) < 20:
        return 0.0
    m = x.mean()

    def media(b):
        if abs(b) < 1e-6:
            return b * w * w / 3
        return w / math.tanh(b * w) - 1 / b
    lo, hi = -2.0, 2.0
    for _ in range(80):
        b = (lo + hi) / 2
        lo, hi = (b, hi) if media(b) < m else (lo, b)
    return (lo + hi) / 2


def probits(z, lab):
    out = []
    for k, jan in JAN:
        m = ((lab == k) | (lab == k + 1)) & (z > jan[0]) & (z < jan[1])
        out.append(probit(z[m], (lab[m] == k + 1).astype(float), float(np.median(z[m]))))
    return out


def tweedie(z, lab, pr=None):
    pr = pr or probits(z, lab)
    return [c + inclinacao_log(z, c) * s * s for c, s in pr]


# ---------- EM justo: separa por parte (cada parte so usa as alturas verdadeiras da sua faixa) ----------
H = 0.25


def ll_parte(zc, wz, lo, hi, sg, iters=300):
    """Log-verossimilhanca dos tiros de uma parte (histograma zc, pesos wz) com densidade livre
    da altura verdadeira dentro de [lo, hi) e borrao normal sg."""
    tb = np.arange(math.ceil(lo / H) * H + H / 2, hi, H)
    if len(tb) == 0:
        return -1e18
    K = np.exp(-0.5 * ((zc[:, None] - tb[None, :]) / sg) ** 2) / sg
    g = np.full(len(tb), 1 / len(tb))
    for _ in range(iters):
        den = K @ g + 1e-300
        g = g * (K.T @ (wz / den)) / wz.sum()
    return float((wz * np.log(K @ g + 1e-300)).sum())


def em_justo(z, lab, c0, sg0=4.0):
    hist = []
    for L in range(4):
        zz = z[lab == L]
        edges = np.arange(np.floor(zz.min()) - H, zz.max() + 2 * H, H)
        cnt, e = np.histogram(zz, edges)
        ok = cnt > 0
        hist.append(((e[:-1] + H / 2)[ok], cnt[ok].astype(float)))
    lims = lambda c: [(-5.0, c[0]), (c[0], c[1]), (c[1], c[2]), (c[2], 85.0)]

    def total(c, sg):
        return sum(ll_parte(hist[L][0], hist[L][1], *lims(c)[L], sg) for L in range(4))
    c, sg = list(c0), sg0
    for passo in (0.5, 0.25):
        for k in range(3):
            melhor = (-np.inf, c[k])
            for v in np.arange(c[k] - 4, c[k] + 4.001, passo):
                cc = c.copy(); cc[k] = float(v)
                if not (cc[0] < cc[1] < cc[2]):
                    continue
                # so as duas partes vizinhas da fronteira k mudam
                l = sum(ll_parte(hist[L][0], hist[L][1], *lims(cc)[L], sg) for L in (k, k + 1))
                if l > melhor[0]:
                    melhor = (l, float(v))
            c[k] = melhor[1]
        melhor = (-np.inf, sg)
        for v in np.arange(1.5, 7.01, 0.25):
            l = total(c, v)
            if l > melhor[0]:
                melhor = (l, float(v))
        sg = melhor[1]
    return c, sg


def todos(z, lab, com_em_atual=True):
    pr = probits(z, lab)
    out = {"probit": [c for c, _ in pr], "probit corrigido (Tweedie)": tweedie(z, lab, pr)}
    if com_em_atual:
        c_em, _ = mr.ajustar(z, lab, [c for c, _ in pr])
        out["EM atual"] = list(c_em)
        out["meio (probit + EM atual)"] = [0.5 * (a + b) for a, b in zip(out["probit"], c_em)]
    out["EM justo"], _ = em_justo(z, lab, out["probit"])
    out["largura do probit (borrao)"] = [s for _, s in pr]
    return out


def sorteio_densidade(z, rng, modo):
    """Densidade verdadeira da altura para a simulacao: 'alisada' (KDE das alturas medidas, mais
    lisa que a real) ou 'desborrada' (alturas medidas encolhidas para tirar parte do borrao)."""
    if modo == "alisada":
        return lambda n: rng.choice(z, n) + rng.normal(0, 1.0, n)
    # desborrada: encolhe os desvios locais (media movel) para a variancia cair ~ s^2
    zs = np.sort(z)
    loc = pd.Series(zs).rolling(201, center=True, min_periods=1).mean().to_numpy()
    enc = loc + (zs - loc) * 0.55
    return lambda n: rng.choice(enc, n) + rng.normal(0, 0.3, n)


def main():
    pasta, cache = sys.argv[1:3]
    R = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    z, lab = dados(pasta, cache)
    print(f"balas perto do eixo do corpo: {len(z)} (pernas {np.sum(lab == 0)}, barriga {np.sum(lab == 1)}, peito {np.sum(lab == 2)}, cabeca {np.sum(lab == 3)})", flush=True)
    t = time.time()
    real = todos(z, lab)
    print(f"\nDADOS REAIS ({time.time() - t:.0f} s):")
    for nome, v in real.items():
        print(f"  {nome:30s} " + "  ".join(f"{NOMES[k]} {v[k]:6.2f}" for k in range(3)), flush=True)
    if R == 0:
        return
    # ---------- simulacao ----------
    verdade_base = [real["probit corrigido (Tweedie)"][k] for k in range(3)]
    so = sys.argv[4] if len(sys.argv) > 4 else "todos"
    saida = sys.argv[5] if len(sys.argv) > 5 else None
    tabela = {}
    for ci in (range(len(CENARIOS)) if so == "todos" else [int(so)]):
        dens, borrao = CENARIOS[ci]
        erros = rodar_cenario(z, verdade_base, dens, borrao, R)
        imprimir(dens, borrao, R, erros, tabela)
        if saida:
            json.dump({"dens": dens, "borrao": borrao, "R": R, "erros": erros}, open(saida, "w", encoding="utf-8"))
    if so == "todos":
        resumo(tabela)


CENARIOS = [(dens, borrao) for dens in ("alisada", "desborrada")
            for borrao in ("normal 4,5", "normal 3", "cauda pesada (t4)", "borrao variando 2 a 7")]


def um_sorteio(rng, gera, n, verdade_base, borrao):
    """Um dia simulado: fronteira verdadeira sorteada, alturas verdadeiras, parte e borrao."""
    verdade = [v + rng.uniform(-2, 2) for v in verdade_base]
    h = gera(n)
    lb = np.searchsorted(np.asarray(verdade), h, side="right")
    if borrao == "normal 4,5":
        e = rng.normal(0, 4.5, n)
    elif borrao == "normal 3":
        e = rng.normal(0, 3.0, n)
    elif borrao.startswith("cauda"):
        e = 4.5 * rng.standard_t(4, n) / math.sqrt(2)
    else:
        e = rng.normal(0, 1, n) * rng.uniform(2, 7, n)
    return verdade, h + e, lb


def rodar_cenario(z, verdade_base, dens, borrao, R):
    rng = np.random.default_rng(zlib.crc32(f"{dens}|{borrao}".encode()))          # semente fixa por cenario
    gera = sorteio_densidade(z, rng, dens)
    erros = {}
    for rep in range(R):
        verdade, zz, lb = um_sorteio(rng, gera, len(z), verdade_base, borrao)
        est = todos(zz, lb, com_em_atual=True)
        for nome, v in est.items():
            if not nome.startswith("largura"):
                erros.setdefault(nome, []).append([float(v[k] - verdade[k]) for k in range(3)])
    return erros


def main_validar(pasta, cache, ws_txt, R=40):
    """Refaz os MESMOS sorteios da comparacao (que nao foram usados para escolher o w) e mede o
    Tweedie com o w escolhido contra o w = 6. Com w = 6 tem de dar o mesmo numero da comparacao."""
    ws = [float(x) for x in ws_txt.split(",")]
    ws = ws * 3 if len(ws) == 1 else ws
    z, lab = dados(pasta, cache)
    base = tweedie(z, lab)
    rm6, rmw = [], []
    for dens, borrao in CENARIOS:
        rng = np.random.default_rng(zlib.crc32(f"{dens}|{borrao}".encode()))
        gera = sorteio_densidade(z, rng, dens)
        e6, ew = [], []
        for rep in range(R):
            verdade, zz, lb = um_sorteio(rng, gera, len(z), base, borrao)
            pr = probits(zz, lb)
            e6.append([c + inclinacao_log(zz, c, 6.0) * s * s - verdade[k] for k, (c, s) in enumerate(pr)])
            ew.append([c + inclinacao_log(zz, c, ws[k]) * s * s - verdade[k] for k, (c, s) in enumerate(pr)])
        rm6.append(np.sqrt((np.array(e6) ** 2).mean(0)))
        rmw.append(np.sqrt((np.array(ew) ** 2).mean(0)))
        print(f"{dens:10s} {borrao:22s} w=6: " + " ".join(f"{v:.2f}" for v in rm6[-1]) + " | w escolhido: " + " ".join(f"{v:.2f}" for v in rmw[-1]), flush=True)
    a, b = np.mean(rm6, 0), np.mean(rmw, 0)
    print(f"\nmedia dos 8: w=6 " + " ".join(f"{v:.3f}" for v in a) + f" (media {a.mean():.3f}) | w {ws}: " + " ".join(f"{v:.3f}" for v in b) + f" (media {b.mean():.3f})")


def main_janela(pasta, cache, R):
    """Largura da janela da inclinacao (o w do Tweedie): o erro tipico de cada w nos 8 cenarios,
    com sorteios proprios (diferentes dos da comparacao entre metodos)."""
    z, lab = dados(pasta, cache)
    base = tweedie(z, lab)
    ws = np.round(np.arange(2.0, 30.001, 0.25), 2)
    rm = np.zeros((len(CENARIOS), len(ws), 3))
    for ci, (dens, borrao) in enumerate(CENARIOS):
        rng = np.random.default_rng(zlib.crc32(f"janela|{dens}|{borrao}".encode()))
        gera = sorteio_densidade(z, rng, dens)
        err = np.zeros((R, len(ws), 3))
        for rep in range(R):
            verdade, zz, lb = um_sorteio(rng, gera, len(z), base, borrao)
            pr = probits(zz, lb)
            for a, w in enumerate(ws):
                for k, (c, s) in enumerate(pr):
                    err[rep, a, k] = c + inclinacao_log(zz, c, w) * s * s - verdade[k]
        rm[ci] = np.sqrt((err ** 2).mean(0))
        print(f"cenario {ci} ({dens}, {borrao}) pronto", flush=True)
    media = rm.mean(0)
    print(f"\n{'w':>6s} | " + " | ".join(f"{n:>14s}" for n in NOMES) + " |  media")
    for a, w in enumerate(ws):
        print(f"{w:6.2f} | " + " | ".join(f"{media[a, k]:14.3f}" for k in range(3)) + f" | {media[a].mean():6.3f}")
    a = int(np.argmin(media.mean(1)))
    print(f"\nmelhor w unico: {ws[a]:.2f} (erro medio {media[a].mean():.3f}; com w = 6: {media[list(ws).index(6.0)].mean():.3f})")
    for k in range(3):
        b = int(np.argmin(media[:, k]))
        empate = ws[media[:, k] <= media[b, k] * 1.01]
        print(f"melhor w para {NOMES[k]}: {ws[b]:.2f} (erro {media[b, k]:.3f}; com w = 6: {media[list(ws).index(6.0), k]:.3f}; "
              f"a menos de 1% do melhor: w de {empate.min():.2f} a {empate.max():.2f})")


def imprimir(dens, borrao, R, erros, tabela):
    print(f"\n=== verdade {dens}, borrao {borrao} ({R} sorteios) ===", flush=True)
    for nome, ee in erros.items():
        ee = np.array(ee)
        vies, rmse = ee.mean(0), np.sqrt((ee ** 2).mean(0))
        tabela.setdefault(nome, []).append(rmse)
        print(f"  {nome:30s} " + "  ".join(f"{NOMES[k]}: vies {vies[k]:+5.2f} erro {rmse[k]:4.2f}" for k in range(3)), flush=True)


def resumo(tabela):
    print(f"\nERRO TIPICO MEDIO ({len(next(iter(tabela.values())))} cenarios):")
    for nome, v in sorted(tabela.items(), key=lambda kv: np.mean(kv[1])):
        v = np.mean(v, 0)
        print(f"  {nome:30s} " + "  ".join(f"{NOMES[k]} {v[k]:4.2f}" for k in range(3)) + f"  | media {v.mean():.2f}")


def main_resumo(arquivos):
    """Junta os cenarios rodados em paralelo (um processo por cenario)."""
    tabela = {}
    for arq in arquivos:
        r = json.load(open(arq, encoding="utf-8"))
        imprimir(r["dens"], r["borrao"], r["R"], r["erros"], tabela)
    resumo(tabela)


if __name__ == "__main__":
    if sys.argv[1] == "resumo":
        main_resumo(sys.argv[2:])
    elif sys.argv[1] == "janela":
        main_janela(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 40)
    elif sys.argv[1] == "validar":
        main_validar(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 40)
    else:
        main()
