"""Quantas rodadas, quantos blocos por rodada e como afunilar o PSA do dia.

Simula o protocolo do app bloco a bloco:
  - nota do bloco = curva verdadeira + aquecimento/cansaco + ruido
    (ruido de duelo 0,38 / raiz(duelos), mais 0,04 do bloco inteiro);
  - cada bloco tem 3 alvos de adaptacao que nao contam;
  - rodada: sondas nas pontas da faixa, ordem A B B A (4 blocos) ou A B B A B A A B (8);
  - ruido medido no dia como no app (pares da mesma sonda + 6 gl de partida em 0,088);
  - w = diferenca / (t * erro), entre -1 e 1; centro -= w * k * W; W *= rho.
Tempo de um duelo ~1,05 s e 6 s de pausa por bloco.

Uso: python otimizar_psa.py [rapido]
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LN3 = np.log(3)
SIGMA0, GL0 = 0.088, 6


def t975(gl):
    z = 1.959964
    z3, z5, z7 = z ** 3, z ** 5, z ** 7
    return z + (z3 + z) / (4 * gl) + (5 * z5 + 16 * z3 + 3 * z) / (96 * gl ** 2) + (3 * z7 + 19 * z5 + 17 * z3 - 15 * z) / (384 * gl ** 3)


def tendencia(tau):
    return -0.06 * tau + 0.2 * np.maximum(0, tau - 0.75) ** 2


def minutos(R, nblk, nduel):
    return (R * nblk * ((nduel + 3) * 1.05 + 6) + 20 * 1.05) / 60


def sessao(curva, rng, R, nblk=4, W0=LN3, rho=0.5, k=0.25, nduel=24, sd_duelo=0.38, sd_bloco=0.04):
    sd = np.sqrt(sd_duelo ** 2 / nduel + sd_bloco ** 2)
    c, W = 0.0, W0
    soma2, gl_med = 0.0, 0
    total = R * nblk
    kb = 0
    for r in range(R):
        a, b = c - W / 2, c + W / 2
        base = ["A", "B", "B", "A"] if r % 2 == 0 else ["B", "A", "A", "B"]
        ordem = base if nblk == 4 else base + base[::-1]
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            tau = kb / max(1, total - 1)
            ys[lado].append(curva(x) + tendencia(tau) + sd * rng.standard_normal())
            kb += 1
        for lado in ("A", "B"):
            v = np.array(ys[lado])
            soma2 += np.sum((v - v.mean()) ** 2)
            gl_med += len(v) - 1
        gl = gl_med + GL0
        sig = np.sqrt((soma2 + GL0 * SIGMA0 ** 2) / gl)
        se = sig * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"]) - np.mean(ys["A"])
        w = np.clip(delta / (t975(gl) * se), -1, 1)
        c -= w * k * W
        W *= rho
    return c


def sessao_plano(curva, rng, plano, W0=LN3, rho=0.5, k=0.25, sd_duelo=0.38, sd_bloco=0.04):
    """plano = lista de (blocos por rodada, duelos por bloco). Devolve centro final e sens jogadas."""
    c, W = 0.0, W0
    soma2, gl_med = 0.0, 0
    total = sum(nb for nb, _ in plano)
    kb = 0
    jogadas = []
    for r, (nblk, nduel) in enumerate(plano):
        sd = np.sqrt(sd_duelo ** 2 / nduel + sd_bloco ** 2)
        a, b = c - W / 2, c + W / 2
        base = ["A", "B", "B", "A"] if r % 2 == 0 else ["B", "A", "A", "B"]
        ordem = base if nblk == 4 else base + base[::-1]
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            jogadas.append(x)
            ys[lado].append(curva(x) + tendencia(kb / max(1, total - 1)) + sd * rng.standard_normal())
            kb += 1
        # o ruido do dia e medido em "nota de bloco"; blocos de tamanhos diferentes viram a mesma
        # escala dividindo pela raiz do tamanho (o app faz o mesmo)
        escala = np.sqrt(nduel / 24)
        for lado in ("A", "B"):
            v = np.array(ys[lado]) * escala
            soma2 += np.sum((v - v.mean()) ** 2)
            gl_med += len(v) - 1
        gl = gl_med + GL0
        sig24 = np.sqrt((soma2 + GL0 * SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"]) - np.mean(ys["A"])
        w = np.clip(delta / (t975(gl) * se), -1, 1)
        c -= w * k * W
        W *= rho
    return c, np.array(jogadas)


def minutos_plano(plano):
    return (sum(nb * ((nd + 3) * 1.05 + 6) for nb, nd in plano) + 20 * 1.05) / 60


def main_frente():
    """Concentrar duelos nas primeiras rodadas. Mede erro de sens e PERDA de desempenho."""
    N = 3000
    rng = np.random.default_rng(33)
    meia = np.log(2) / 2
    curvas = {
        "pico": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato": lambda x0: (lambda x: 0.9 * max(0.0, abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2),
        "torta": lambda x0: (lambda x: (0.5 if x > x0 else 0.125) * (x - x0) ** 2),
    }
    planos = {
        "atual: 5 x (4 de 24)": [(4, 24)] * 5,
        "3 x (4 de 24)": [(4, 24)] * 3,
        "4 x (4 de 30)": [(4, 30)] * 4,
        "36,36,24,12,12": [(4, 36), (4, 36), (4, 24), (4, 12), (4, 12)],
        "40,30,20,12": [(4, 40), (4, 30), (4, 20), (4, 12)],
        "48,32,16,12": [(4, 48), (4, 32), (4, 16), (4, 12)],
        "48,36,24,12,12": [(4, 48), (4, 36), (4, 24), (4, 12), (4, 12)],
        "8x24, 4x24, 4x12, 4x12": [(8, 24), (4, 24), (4, 12), (4, 12)],
        "60,36,12,12": [(4, 60), (4, 36), (4, 12), (4, 12)],
    }
    print(f"{'plano (duelos por bloco em cada rodada)':40s} {'min':>5s} | erro de sens (pico/chato/torta) | perda de desempenho media (pico/chato/torta) | jogada mais perto do final")
    for nome, plano in planos.items():
        er, perda, perto = [], [], []
        for nc, fab in curvas.items():
            e = np.empty(N); p = np.empty(N); pt = np.empty(N)
            for i in range(N):
                x0 = rng.uniform(-0.4, 0.4)
                f = fab(x0)
                c, jog = sessao_plano(f, rng, plano)
                e[i] = c - x0
                p[i] = np.exp(f(c) - f(x0)) - 1
                pt[i] = np.min(np.abs(jog - c))
            er.append(100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1))
            perda.append(100 * np.mean(p))
            perto.append(100 * (np.exp(np.median(pt)) - 1))
        print(f"{nome:40s} {minutos_plano(plano):5.1f} | {er[0]:5.1f} / {er[1]:5.1f} / {er[2]:5.1f}% | "
              f"{perda[0]:5.2f} / {perda[1]:5.2f} / {perda[2]:5.2f}% | {np.mean(perto):4.1f}%")


def sessoes_duelo(curva_v, x0, rng, desenho, aq):
    """Simula N sessoes em paralelo, duelo a duelo, com aquecimento e custo de troca de sens.

    nota do duelo = curva(x) + aq_amp * exp(-n/aq_tau)            (ainda esquentando)
                    + troca_amp * |dx|/ln3 * exp(-m/troca_k)       (acabou de trocar de sens)
                    + 0,04 do bloco + 0,38 do duelo
    n = duelos jogados desde o inicio (aquecimento incluido), m = posicao no bloco,
    dx = mudanca de sens em relacao ao bloco anterior. Os primeiros `adapt` do bloco nao contam.
    desenho: aquec, adapt, duelos (por rodada), ordem ('fixa' = A B B A / B A A B alternando,
    A = ponta de baixo; 'sorteada' = a 1a rodada sorteia A B B A ou B A A B), blocos8 (rodadas
    com A B B A B A A B)."""
    N = len(x0)
    c = np.zeros(N)
    W = LN3
    soma2 = np.zeros(N)
    gl_med = 0
    n_jogados = desenho["aquec"]
    x_ant = np.zeros(N)
    inverte = np.zeros(N, dtype=bool)
    if desenho.get("ordem") == "sorteada":
        inverte = rng.random(N) < 0.5
    for r, nduel in enumerate(desenho["duelos"]):
        nblk = 8 if r in desenho.get("blocos8", ()) else 4
        nd = nduel if nblk == 4 else nduel // 2
        a, b = c - W / 2, c + W / 2
        base = ["A", "B", "B", "A"] if r % 2 == 0 else ["B", "A", "A", "B"]
        ordem = base if nblk == 4 else base + base[::-1]
        ys = {"A": [], "B": []}
        for lado in ordem:
            # com 'sorteada', metade das sessoes troca A por B em todas as rodadas
            xa = np.where(inverte, b, a)
            xb = np.where(inverte, a, b)
            x = xa if lado == "A" else xb
            m = np.arange(desenho["adapt"] + nd)
            n = n_jogados + m
            dx = np.abs(x - x_ant)
            efeito = (aq["aq_amp"] * np.exp(-n[None, :] / aq["aq_tau"])
                      + aq["troca_amp"] * (dx / LN3)[:, None] * np.exp(-m[None, :] / aq["troca_k"]))
            y = (curva_v(x, x0)[:, None] + efeito + 0.04 * rng.standard_normal((N, 1))
                 + 0.38 * rng.standard_normal((N, len(m))))
            nota = y[:, desenho["adapt"]:].mean(axis=1)
            ys[lado].append(nota)
            n_jogados += len(m)
            x_ant = x
        escala = np.sqrt(nd / 24)
        for lado in ("A", "B"):
            v = np.array(ys[lado]) * escala
            soma2 += ((v - v.mean(axis=0)) ** 2).sum(axis=0)
            gl_med += v.shape[0] - 1
        gl = gl_med + GL0
        sig24 = np.sqrt((soma2 + GL0 * SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        # delta = nota da ponta de cima - nota da de baixo (positivo = cima mais lenta)
        dA, dB = np.mean(ys["A"], axis=0), np.mean(ys["B"], axis=0)
        delta = np.where(inverte, dA - dB, dB - dA)
        w = np.clip(delta / (t975(gl) * se), -1, 1)
        c = c - w * 0.25 * W
        W *= 0.5
    return c, n_jogados


def main_aquecimento():
    """Quantos alvos de aquecimento, quantos de adaptacao e que ordem de blocos, com
    aquecimento e custo de troca de sens fracos e fortes."""
    rng = np.random.default_rng(55)
    N = 1500
    meia = np.log(2) / 2
    curvas = {
        "pico": lambda x, x0: 0.28 * (x - x0) ** 2,
        "fundo chato": lambda x, x0: 0.9 * np.maximum(0.0, np.abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2,
        "torta": lambda x, x0: np.where(x > x0, 0.5, 0.125) * (x - x0) ** 2,
    }
    cenarios = []
    for aq_amp in (0.0, 0.05, 0.10, 0.20):
        for aq_tau in ((40,) if aq_amp == 0 else (15, 40, 100)):
            for troca_amp in (0.0, 0.10, 0.25):
                for troca_k in ((2,) if troca_amp == 0 else (2, 6)):
                    cenarios.append(dict(aq_amp=aq_amp, aq_tau=aq_tau, troca_amp=troca_amp, troca_k=troca_k))
    D = [36, 36, 24, 12, 12]
    desenhos = {
        "atual: aquec 20, adapt 3": dict(aquec=20, adapt=3, duelos=D),
        "aquec 40, adapt 3": dict(aquec=40, adapt=3, duelos=D),
        "aquec 60, adapt 3": dict(aquec=60, adapt=3, duelos=D),
        "aquec 100, adapt 3": dict(aquec=100, adapt=3, duelos=D),
        "aquec 20, adapt 6": dict(aquec=20, adapt=6, duelos=D),
        "aquec 40, adapt 6": dict(aquec=40, adapt=6, duelos=D),
        "aquec 20, adapt 3, ordem sorteada": dict(aquec=20, adapt=3, duelos=D, ordem="sorteada"),
        "aquec 40, adapt 3, ordem sorteada": dict(aquec=40, adapt=3, duelos=D, ordem="sorteada"),
        "aquec 40, adapt 6, ordem sorteada": dict(aquec=40, adapt=6, duelos=D, ordem="sorteada"),
        "aquec 20, adapt 3, 1a rodada ABBABAAB": dict(aquec=20, adapt=3, duelos=D, blocos8=(0,)),
        "aquec 40, adapt 3, 1a rodada ABBABAAB": dict(aquec=40, adapt=3, duelos=D, blocos8=(0,)),
        "aquec 40, adapt 3, rodadas 1-2 ABBABAAB": dict(aquec=40, adapt=3, duelos=D, blocos8=(0, 1)),
    }
    print(f"{len(cenarios)} cenarios de aquecimento/troca x 3 curvas x {N} dias")
    print(f"{'desenho':42s} {'min':>5s} | perda media | pior cenario | vies medio (sens) | pior vies | sem efeito nenhum")
    for nome, ds in desenhos.items():
        perdas, vieses, perda_zero = [], [], None
        for aq in cenarios:
            pc, vc = [], []
            for cv in curvas.values():
                x0 = rng.uniform(-0.4, 0.4, N)
                cf, njog = sessoes_duelo(cv, x0, rng, ds, aq)
                pc.append(np.mean(np.exp(cv(cf, x0) - cv(x0, x0)) - 1))
                vc.append(np.mean(cf - x0))
            perdas.append(np.mean(pc))
            vieses.append(np.mean(vc))
            if aq["aq_amp"] == 0 and aq["troca_amp"] == 0:
                perda_zero = np.mean(pc)
        perdas, vieses = np.array(perdas), np.array(vieses)
        nblocos = sum(8 if r in ds.get("blocos8", ()) else 4 for r in range(len(ds["duelos"])))
        minutos_ = ((njog) * 1.05 + nblocos * 6) / 60
        print(f"{nome:42s} {minutos_:5.1f} | {100 * perdas.mean():9.3f}% | {100 * perdas.max():10.3f}% | "
              f"{100 * (np.exp(vieses.mean()) - 1):+15.2f}% | {100 * (np.exp(vieses[np.argmax(np.abs(vieses))]) - 1):+8.2f}% | {100 * perda_zero:.3f}%")


def main_tamanho():
    """Quantos alvos por bloco no total: mais alvos = menos ruido, mas mais minutos.
    Mesmo desenho (5 rodadas, A B B A, mais duelos no comeco), com tudo multiplicado."""
    N = 3000
    rng = np.random.default_rng(77)
    meia = np.log(2) / 2
    curvas = {
        "pico": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato": lambda x0: (lambda x: 0.9 * max(0.0, abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2),
        "torta": lambda x0: (lambda x: (0.5 if x > x0 else 0.125) * (x - x0) ** 2),
    }
    base = [36, 36, 24, 12, 12]
    planos = {f"x{f:g}: " + ",".join(str(int(round(d * f))) for d in base): [(4, int(round(d * f))) for d in base]
              for f in (0.5, 0.75, 1, 1.5, 2, 3)}
    planos["x1 + 6a rodada de 12"] = [(4, d) for d in base + [12]]
    planos["x2 em 7 rodadas: 72,72,48,24,24,24,24"] = [(4, d) for d in (72, 72, 48, 24, 24, 24, 24)]
    for cansaco in (False, True):
        print(f"\n=== {'COM cansaco (ruido do bloco +0,02 a cada 10 min, do duelo +10% a cada 10 min)' if cansaco else 'sem cansaco'} ===")
        print(f"{'plano (duelos por bloco)':40s} {'min':>5s} | erro de sens (media das 3 curvas) | perda de desempenho | perda que sobra x ganho por minuto")
        anterior = None
        for nome, plano in planos.items():
            er, perda = [], []
            for fab in curvas.values():
                e = np.empty(N)
                p = np.empty(N)
                for i in range(N):
                    x0 = rng.uniform(-0.4, 0.4)
                    f = fab(x0)
                    if cansaco:
                        c, _ = sessao_plano_cansaco(f, rng, plano)
                    else:
                        c, _ = sessao_plano(f, rng, plano)
                    e[i] = c - x0
                    p[i] = np.exp(f(c) - f(x0)) - 1
                er.append(100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1))
                perda.append(100 * np.mean(p))
            mn = minutos_plano(plano)
            pm = np.mean(perda)
            marg = "" if anterior is None or mn <= anterior[0] else f"{(anterior[1] - pm) / (mn - anterior[0]):+.3f} pontos/min"
            if nome.startswith("x"):
                anterior = (mn, pm)
            print(f"{nome:40s} {mn:5.1f} | {np.mean(er):6.1f}% | {pm:6.3f}% | {marg}")


def sessao_plano_cansaco(curva, rng, plano, W0=LN3, rho=0.5, k=0.25):
    """Como sessao_plano, mas o ruido cresce com o tempo de teste (cansaco/atencao)."""
    c, W = 0.0, W0
    soma2, gl_med = 0.0, 0
    minuto = 20 * 1.05 / 60
    jogadas = []
    for r, (nblk, nduel) in enumerate(plano):
        a, b = c - W / 2, c + W / 2
        base = ["A", "B", "B", "A"] if r % 2 == 0 else ["B", "A", "A", "B"]
        ordem = base if nblk == 4 else base + base[::-1]
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            jogadas.append(x)
            sd_duelo = 0.38 * (1 + 0.10 * minuto / 10)
            sd_bloco = 0.04 + 0.02 * minuto / 10
            sd = np.sqrt(sd_duelo ** 2 / nduel + sd_bloco ** 2)
            ys[lado].append(curva(x) + sd * rng.standard_normal())
            minuto += ((nduel + 3) * 1.05 + 6) / 60
        escala = np.sqrt(nduel / 24)
        for lado in ("A", "B"):
            v = np.array(ys[lado]) * escala
            soma2 += np.sum((v - v.mean()) ** 2)
            gl_med += len(v) - 1
        gl = gl_med + GL0
        sig24 = np.sqrt((soma2 + GL0 * SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"]) - np.mean(ys["A"])
        w = np.clip(delta / (t975(gl) * se), -1, 1)
        c -= w * k * W
        W *= rho
    return c, np.array(jogadas)


def avaliar(cfg, curvas, rng, N):
    out = {}
    for nome, fab in curvas.items():
        e = np.empty(N)
        for i in range(N):
            x0 = rng.uniform(-0.4, 0.4)
            e[i] = sessao(fab(x0), rng, **cfg) - x0
        out[nome] = (100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1), 100 * (np.exp(np.mean(e)) - 1))
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "frente":
        return main_frente()
    if len(sys.argv) > 1 and sys.argv[1] == "aquecimento":
        return main_aquecimento()
    if len(sys.argv) > 1 and sys.argv[1] == "tamanho":
        return main_tamanho()
    rapido = len(sys.argv) > 1
    N = 1200 if rapido else 3000
    rng = np.random.default_rng(21)
    meia = np.log(2) / 2
    curvas = {
        "pico": lambda x0: (lambda x: 0.28 * (x - x0) ** 2),
        "fundo chato": lambda x0: (lambda x: 0.9 * max(0.0, abs(x - x0) - meia) ** 2 + 0.02 * (x - x0) ** 2),
        "torta": lambda x0: (lambda x: (0.5 if x > x0 else 0.125) * (x - x0) ** 2),
    }

    def linha(nome, cfg):
        r = avaliar(cfg, curvas, rng, N)
        mn = minutos(cfg.get("R", 5), cfg.get("nblk", 4), cfg.get("nduel", 24))
        media = np.mean([v[0] for v in r.values()])
        print(f"{nome:44s} {mn:5.1f} min | pico {r['pico'][0]:5.1f}% | chato {r['fundo chato'][0]:5.1f}% | "
              f"torta {r['torta'][0]:5.1f}% (vies {r['torta'][1]:+5.1f}%) | media {media:5.1f}%")
        return media

    print("=== 1) quantas rodadas (A B B A, blocos de 24) ===")
    for R in (3, 4, 5, 6, 7, 8):
        linha(f"{R} rodadas x 4 blocos", dict(R=R))
    print("\n=== 2) 4 ou 8 blocos por rodada (mesmo tempo total aproximado) ===")
    linha("5 rodadas x 4 blocos de 24", dict(R=5))
    linha("5 rodadas x 8 blocos de 12", dict(R=5, nblk=8, nduel=12))
    linha("5 rodadas x 4 blocos de 36", dict(R=5, nduel=36))
    linha("4 rodadas x 4 blocos de 30", dict(R=4, nduel=30))
    linha("6 rodadas x 4 blocos de 20", dict(R=6, nduel=20))
    linha("8 rodadas x 4 blocos de 15", dict(R=8, nduel=15))
    print("\n=== 3) afunilamento (5 rodadas x 4 blocos de 24) ===")
    for rho in (0.5, 0.6, 0.7, 0.8):
        for k in (0.25, 0.35, 0.5):
            linha(f"faixa x{rho} por rodada, passo {k} da faixa", dict(R=5, rho=rho, k=k))
    print("\n=== 4) faixa inicial ===")
    for W0, nome in ((np.log(2.5), "x2,5"), (LN3, "x3"), (np.log(4), "x4")):
        linha(f"faixa inicial {nome}", dict(R=5, W0=W0))


if __name__ == "__main__":
    main()
