"""Concorrentes da REGRA DA RODADA do PSA (quarta revisao), no mesmo tempo e com os mesmos sorteios.

Mesmo jogo do otimizar_exato.py (blocos, alvos por rodada do desenho de 12 min, ruido incerto,
cansaco); muda so como a faixa encolhe e quanto o centro anda:
  atual:       faixa x rho a cada rodada, centro anda w * k * faixa;
  livre:       uma faixa e um passo PROPRIOS para cada rodada (12 numeros + gama);
  Kesten:      a faixa so encolhe (x rho1) quando a direcao troca; se a evidencia continua
               apontando para o mesmo lado, encolhe menos (x rho2) e o centro segue andando;
  momento:     o centro anda w * k * faixa + beta * (o quanto andou na rodada anterior);
  sondas mais perto: W0 fixo menor (x0,5 a x0,8 do atual), com k, rho e gama re-otimizados.
Cada um tem os seus numeros otimizados (descida coordenada, 120 mil dias), depois e conferido
em 300 mil dias novos e nos cenarios de ataque (ruido x0,5/x1,5/x2, curva x0,5/x2, curvas que o
otimizador nao viu, melhor sens longe, sem cansaco). Tambem mostra quanto o centro anda com a
melhor sens a +20%.

Uso: python concorrentes_rodada.py [N]
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


AQ = [(0.0, 15)] + [(a, t) for a in (0.10, 0.25) for t in (15, 50)]      # aquecimento: amplitude, alvos para sumir
TR = [(0.0, 2)] + [(a, k) for a in (0.10, 0.25) for k in (2, 6)]       # troca de sens: amplitude por ln3 de troca, alvos
CENS_ADAPT = [(a, t, ta, tk) for (a, t) in AQ for (ta, tk) in TR]      # os 25 cenarios do otimizar_adapt.py


def sortear_adapt(N, semente=2611):
    """Cada dia sorteia um dos 25 cenarios de aquecimento e custo de troca de sens."""
    idx = np.random.default_rng(semente).integers(0, len(CENS_ADAPT), N)
    C = np.array(CENS_ADAPT)[idx]
    return {"aq_amp": C[:, 0], "aq_tau": C[:, 1], "tr_amp": C[:, 2], "tr_k": C[:, 3]}


def media_geom(q, a, nd):
    """media de q^m para m = a .. a+nd-1 (q por dia)."""
    q = np.minimum(q, 1 - 1e-12)
    return q ** a * (1 - q ** nd) / (nd * (1 - q))


def simular_v(p, s, cansaco=True, t_duelo=1.05, t_pausa=6.0, escala_ruido=1.0, escala_curva=1.0, adapta=None):
    """adapta: None (sem custo de troca nem aquecimento, como o otimizar_exato.py) ou o dict de
    sortear_adapt: cada bloco ganha, na media dos duelos que contam, o custo de troca de sens
    (proporcional ao tamanho da troca, sumindo com os alvos) e o do aquecimento (sumindo com os
    alvos desde o comeco), igual ao modelo duelo a duelo do otimizar_adapt.py."""
    n, gam = p["n"], p["gam"]
    adapt, aquec, gl0 = p.get("adapt", 3), p.get("aquec", 20), p.get("gl0", oe.GL0)
    Ws, ks = p.get("Ws"), p.get("ks")
    kesten, beta = p.get("kesten", False), p.get("momento", 0.0)
    esc = escala_ruido * (s.escala if s.escala is not None else 1.0)
    N = len(s.x0)
    c = np.zeros(N); soma2 = np.zeros(N); gl_med = 0
    W = np.full(N, p["W0"] if Ws is None else Ws[0])
    w_ant = np.zeros(N); mov_ant = np.zeros(N)
    minuto = aquec * t_duelo / 60
    kb = 0
    x_ant = np.zeros(N)
    n_jog = aquec
    if adapta is not None:
        q_tr = np.exp(-1 / adapta["tr_k"]); q_aq = np.exp(-1 / adapta["aq_tau"])
    for r, nd in enumerate(n):
        if Ws is not None:
            W = np.full(N, Ws[r])
        a, b = c - W / 2, c + W / 2
        ordem = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            if cansaco:
                sdd = 0.38 * (1 + 0.10 * minuto / 10); sdb = 0.04 + 0.02 * minuto / 10
            else:
                sdd, sdb = 0.38, 0.04
            sd = esc * np.sqrt(sdd ** 2 / nd + sdb ** 2)
            y = escala_curva * oe.curva(x, s.x0, s.tipo) + sd * s.Z[:, kb]
            if adapta is not None:
                y = (y + adapta["tr_amp"] * np.abs(x - x_ant) / oe.LN3 * media_geom(q_tr, adapt, nd)
                     + adapta["aq_amp"] * media_geom(q_aq, n_jog + adapt, nd))
            ys[lado].append(y)
            x_ant = x
            n_jog += adapt + nd
            kb += 1
            minuto += ((nd + adapt) * t_duelo + t_pausa) / 60
        e24 = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * e24
            soma2 += ((v - v.mean(axis=0)) ** 2).sum(axis=0)
            gl_med += v.shape[0] - 1
        gl = gl_med + gl0
        sig24 = np.sqrt((soma2 + gl0 * oe.SIGMA0 ** 2) / gl)
        se = sig24 / e24 * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"], axis=0) - np.mean(ys["A"], axis=0)
        w = np.clip(delta / (gam * oe.t975(gl) * se), -1, 1)
        kr = ks[r] if ks is not None else p["k"]
        mov = -w * kr * W + beta * mov_ant
        c = c + mov
        mov_ant = mov
        if Ws is None:
            if kesten:
                troca = (w * w_ant) < 0
                W = np.where(troca, W * p["rho"], W * p["rho2"])
                w_ant = np.where(w != 0, w, w_ant)
            else:
                W = W * p["rho"]
    perda = np.exp(escala_curva * (oe.curva(c, s.x0, s.tipo) - s.f0)) - 1
    return perda, minuto, c - s.x0


def otimizar(p0, s, chaves, passos, voltas=8, log="", adapta=None):
    """Descida coordenada com numeros aleatorios comuns. chaves: nomes (ou (nome, indice) para listas)."""
    p = copy.deepcopy(p0)

    def pega(q, ch):
        return q[ch[0]][ch[1]] if isinstance(ch, tuple) else q[ch]

    def poe(q, ch, v):
        if isinstance(ch, tuple):
            q[ch[0]][ch[1]] = v
        else:
            q[ch] = v
    melhor = simular_v(p, s, adapta=adapta)[0].mean()
    passo = dict(zip(map(str, chaves), passos))
    for volta in range(voltas):
        mexeu = False
        for ch in chaves:
            for sinal in (+1, -1):
                q = copy.deepcopy(p)
                v = pega(q, ch) + sinal * passo[str(ch)]
                if isinstance(ch, str) and ch in ("rho", "rho2") and not (0.3 <= v <= 1.0):
                    continue
                if v <= 0 and not (isinstance(ch, str) and ch == "momento"):
                    continue
                poe(q, ch, v)
                l = simular_v(q, s, adapta=adapta)[0].mean()
                if l < melhor - 1e-7:
                    p, melhor, mexeu = q, l, True
                    break
        if not mexeu:
            passo = {k: v / 2 for k, v in passo.items()}
        print(f"  {log} volta {volta + 1}: perda {100 * melhor:.4f}%", flush=True)
    return p, melhor


def cenarios(max_blocos=64):
    out = []
    for nome, kw_s, kw, mod in (
            ("modelo (ruido incerto)", dict(ruido_incerto=True), {}, None),
            ("sem cansaco", dict(ruido_incerto=True), {"cansaco": False}, None),
            ("ruido x0,5", {}, {"escala_ruido": 0.5}, None), ("ruido x1,5", {}, {"escala_ruido": 1.5}, None),
            ("ruido x2", {}, {"escala_ruido": 2.0}, None),
            ("curva x0,5", dict(ruido_incerto=True), {"escala_curva": 0.5}, None),
            ("curva x2", dict(ruido_incerto=True), {"escala_curva": 2.0}, None),
            ("curvas novas", dict(ruido_incerto=True), {}, "novas"),
            ("melhor sens ate +-60%", dict(ruido_incerto=True), {}, "longe")):
        s = oe.Sorteio(100000, 31337, max_blocos=max_blocos, **kw_s)
        if mod == "novas":
            s.tipo = 3 + (np.arange(len(s.x0)) % 2); s.f0 = oe.curva(s.x0, s.x0, s.tipo)
        if mod == "longe":
            s.x0 = np.random.default_rng(6).uniform(-0.6, 0.6, len(s.x0)); s.f0 = oe.curva(s.x0, s.x0, s.tipo)
        out.append((nome, s, kw))
    return out


def andou(p, pct=20, N=20000):
    s = oe.Sorteio(N, 7)
    x0 = np.log(1 + pct / 100)
    s.x0 = np.full(N, x0); s.tipo = np.zeros(N, int); s.f0 = oe.curva(s.x0, s.x0, s.tipo)
    c = simular_v(p, s)[2] + x0
    return 100 * (np.exp(c.mean()) - 1)


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 120000
    atual = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    R = len(atual["n"])
    s = oe.Sorteio(N, 4242, ruido_incerto=True)
    base = simular_v(atual, s)[0].mean()
    print(f"atual (12 min): perda {100 * base:.4f}% nos {N} dias de otimizacao", flush=True)
    cands = {}
    # livre: faixa e passo de cada rodada
    p = copy.deepcopy(atual)
    p["Ws"] = [atual["W0"] * atual["rho"] ** r for r in range(R)]
    p["ks"] = [atual["k"]] * R
    chaves = [("Ws", r) for r in range(R)] + [("ks", r) for r in range(R)] + ["gam"]
    cands["livre (faixa e passo por rodada)"] = otimizar(p, s, chaves, [0.08] * R + [0.02] * R + [0.2], log="livre")[0]
    # Kesten
    p = copy.deepcopy(atual); p["kesten"] = True; p["rho2"] = 1.0
    cands["Kesten (so encolhe quando a direcao troca)"] = otimizar(p, s, ["W0", "k", "rho", "rho2", "gam"], [0.08, 0.02, 0.05, 0.03, 0.2], log="kesten")[0]
    # momento
    p = copy.deepcopy(atual); p["momento"] = 0.2
    cands["momento"] = otimizar(p, s, ["W0", "k", "rho", "gam", "momento"], [0.08, 0.02, 0.03, 0.2, 0.1], log="momento")[0]
    # sondas mais perto (a ideia dele): W0 fixo menor, o resto re-otimizado
    for f in (0.5, 0.65, 0.8):
        p = copy.deepcopy(atual); p["W0"] = atual["W0"] * f
        cands[f"sondas mais perto (W0 x{np.exp(p['W0']):.2f} em vez de x{np.exp(atual['W0']):.2f})"] = otimizar(p, s, ["k", "rho", "gam"], [0.02, 0.03, 0.2], log=f"perto {f}")[0]
    # encolher mais rapido (rho fixo menor), o resto re-otimizado
    for rho in (0.5, 0.7):
        p = copy.deepcopy(atual); p["rho"] = rho
        cands[f"afinar mais rapido (rho {rho} em vez de {atual['rho']:.3f})"] = otimizar(p, s, ["W0", "k", "gam"], [0.08, 0.02, 0.2], log=f"rho {rho}")[0]
    # ---------- conferencia em dias novos e nos ataques ----------
    s2 = oe.Sorteio(300000, 99, ruido_incerto=True)
    la = simular_v(atual, s2)[0]
    print(f"\nDIAS NOVOS (300 mil): atual {100 * la.mean():.4f}% | anda com a melhor a +20%: {andou(atual):+.1f}%")
    resumo = {}
    for nome, p in cands.items():
        l = simular_v(p, s2)[0]
        d = l - la
        resumo[nome] = p
        print(f"  {nome:58s} {100 * l.mean():.4f}% | x atual {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f} | anda: {andou(p):+.1f}%", flush=True)
    print("\nCENARIOS DE ATAQUE (perda; diferenca para o atual):")
    sc = cenarios()
    for nome, p in cands.items():
        linha, piores = [], 0
        for cn, scen, kw in sc:
            l0 = simular_v(atual, scen, **kw)[0]; l1 = simular_v(p, scen, **kw)[0]
            d = l1 - l0
            sig = d.mean() / (d.std() / np.sqrt(len(d)))
            linha.append(f"{cn}: {100 * d.mean():+.4f}{'*' if abs(sig) > 3 else ''}")
            piores += d.mean() > 0
        print(f"  {nome:58s} pior que o atual em {piores} de {len(sc)} | " + " | ".join(linha), flush=True)
    json.dump({k: v for k, v in resumo.items()}, open(os.path.join(BASE, "concorrentes_rodada.json"), "w", encoding="utf-8"), indent=1, default=float)


def main_troca(N=120000):
    """Com custo de troca de sens e aquecimento (25 cenarios, um sorteado por dia): o desenho atual,
    o livre da corrida sem custo e as sondas mais perto; depois re-otimiza o geometrico (W0, k, rho,
    gama) e o livre (faixa e passo por rodada, gama) com o custo dentro da conta."""
    atual = json.load(open(os.path.join(BASE, "otimo_orcamento_11.8_final.json"), encoding="utf-8"))["desenho"]
    corrida = json.load(open(os.path.join(BASE, "concorrentes_rodada.json"), encoding="utf-8"))
    livre0 = corrida["livre (faixa e passo por rodada)"]
    R = len(atual["n"])
    s = oe.Sorteio(N, 4242, ruido_incerto=True)
    ad = sortear_adapt(N)
    print(f"com custo de troca e aquecimento ({N} dias, cenario sorteado por dia):", flush=True)
    for nome, p in (("atual", atual), ("livre (otimizado sem custo)", livre0)):
        print(f"  {nome:30s} {100 * simular_v(p, s, adapta=ad)[0].mean():.4f}%", flush=True)
    for f in (0.5, 0.65, 0.8):
        p = copy.deepcopy(atual); p["W0"] = atual["W0"] * f
        p = otimizar(p, s, ["k", "rho", "gam"], [0.02, 0.03, 0.2], voltas=6, log=f"perto {f}", adapta=ad)[0]
        print(f"  sondas mais perto x{np.exp(p['W0']):.2f} (k, rho, gama re-otimizados com custo): {100 * simular_v(p, s, adapta=ad)[0].mean():.4f}%", flush=True)
    geo = otimizar(copy.deepcopy(atual), s, ["W0", "k", "rho", "gam"], [0.08, 0.02, 0.03, 0.2], voltas=10, log="geometrico com custo", adapta=ad)[0]
    p = copy.deepcopy(livre0)
    chaves = [("Ws", r) for r in range(R)] + [("ks", r) for r in range(R)] + ["gam"]
    liv = otimizar(p, s, chaves, [0.08] * R + [0.02] * R + [0.2], voltas=10, log="livre com custo", adapta=ad)[0]
    s2 = oe.Sorteio(300000, 99, ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    l0 = simular_v(atual, s2, adapta=ad2)[0]
    print(f"\nDIAS NOVOS com custo (300 mil): atual {100 * l0.mean():.4f}%")
    for nome, p in (("geometrico re-otimizado com custo", geo), ("livre otimizado sem custo", livre0), ("livre re-otimizado com custo", liv)):
        l = simular_v(p, s2, adapta=ad2)[0]
        d = l - l0
        extra = f"W0 x{np.exp(p['W0']):.4f} k {p['k']:.4f} rho {p['rho']:.4f} gama {p['gam']:.4f}" if "Ws" not in p else \
            "faixas x" + ", ".join(f"{np.exp(w):.4f}" for w in p["Ws"]) + " | passos " + ", ".join(f"{k:.4f}" for k in p["ks"]) + f" | gama {p['gam']:.4f}"
        print(f"  {nome:36s} {100 * l.mean():.4f}% | x atual {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f} | anda {andou(p):+.1f}% | {extra}", flush=True)
    print("\nCENARIOS DE ATAQUE com custo (diferenca para o atual):")
    sc = cenarios()
    for nome, p in (("geometrico re-otimizado com custo", geo), ("livre re-otimizado com custo", liv)):
        linha, piores = [], 0
        for i, (cn, scen, kw) in enumerate(sc):
            ads = sortear_adapt(len(scen.x0), semente=500 + i)
            d = simular_v(p, scen, adapta=ads, **kw)[0] - simular_v(atual, scen, adapta=ads, **kw)[0]
            sig = d.mean() / (d.std() / np.sqrt(len(d)))
            linha.append(f"{cn}: {100 * d.mean():+.4f}{'*' if abs(sig) > 3 else ''}")
            piores += d.mean() > 0
        print(f"  {nome:36s} pior que o atual em {piores} de {len(sc)} | " + " | ".join(linha), flush=True)
    json.dump({"geometrico": geo, "livre": liv}, open(os.path.join(BASE, "concorrentes_rodada_troca.json"), "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "troca":
        main_troca(int(sys.argv[2]) if len(sys.argv) > 2 else 120000)
    else:
        main()
