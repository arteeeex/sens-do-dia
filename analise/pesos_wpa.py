"""Pesos pelo IMPACTO NO ROUND (WPA) contra os pesos atuais (impacto no duelo).

Atual: valor do duelo = f(t) * t (quanto 1% a menos de tempo aumenta a chance de vencer o duelo).
WPA:   valor do duelo = f(t) * t * (chance de ganhar o round se vence o duelo - se perde),
       com a chance de ganhar o round pelo numero de vivos de cada lado e bomba plantada,
       ajustada em TODOS os rounds das tuas demos (os dois times).
Vencer um duelo num 1x1 vale o round inteiro; vencer um 5x5 no comeco vale menos. Se o tipo de
situacao muda com o momento do round, os pesos mudam.
Compara os dois pesos, o sorteio (bootstrap) de cada um e o efeito na sens (mesma conta do
pesos_robustez.py).

Uso: python pesos_wpa.py <pasta_das_demos> <duelos.json>
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from meu_id import meu_steamid  # noqa: E402
from perfil import densidade, kaplan_meier  # noqa: E402
from pesos_robustez import CURV, IDS, preparar, tempos  # noqa: E402


def sid(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return 0
    s = str(v).strip().split(".")[0]
    return int(s) if s.isdigit() else 0


def ler_demo(caminho, ticks_duelos, eu):
    p = DemoParser(caminho)
    fim = p.parse_event("round_end")[["tick", "winner"]].sort_values("tick")
    congel = np.sort(p.parse_event("round_freeze_end")["tick"].to_numpy(int))
    try:
        bomba = np.sort(p.parse_event("bomb_planted")["tick"].to_numpy(int))
    except Exception:
        bomba = np.array([], int)
    try:
        inicio = int(p.parse_event("begin_new_match")["tick"].max())
    except Exception:
        inicio = 0
    mortes = np.sort(p.parse_event("player_death")["tick"].to_numpy(int))
    rounds = []
    ant = inicio
    for t_fim, venc in fim[["tick", "winner"]].itertuples(index=False):
        if t_fim <= inicio:
            continue
        c = congel[(congel > ant) & (congel < t_fim)]
        if len(c):
            rounds.append((int(c.max()), int(t_fim), str(venc)))
        ant = t_fim
    pedir = set()
    for a, b, _ in rounds:
        pedir.add(a + 1)
        for t in mortes[(mortes > a) & (mortes <= b)]:
            pedir.add(int(t) - 1)
    pedir |= set(int(t) for t in ticks_duelos)
    tk = p.parse_ticks(["team_num", "is_alive"], ticks=sorted(pedir))
    tk["steamid"] = tk["steamid"].map(sid)
    vivos = tk[tk["is_alive"].fillna(False).astype(bool)].groupby(["tick", "team_num"]).size().unstack(fill_value=0)
    time_eu = tk[tk["steamid"] == eu].set_index("tick")["team_num"]

    def estado(t):
        aT = int(vivos.loc[t, 2]) if t in vivos.index and 2 in vivos.columns else 0
        aCT = int(vivos.loc[t, 3]) if t in vivos.index and 3 in vivos.columns else 0
        return aT, aCT

    def plantada(t, r0):
        return bool(((bomba > r0) & (bomba < t)).any())
    linhas = []        # estados dos rounds (para a chance de vencer)
    pos_bomba = []     # T todos mortos com a bomba plantada: quem ganhou
    for a, b, venc in rounds:
        ts = [a + 1] + [int(t) - 1 for t in mortes[(mortes > a) & (mortes <= b)]]
        for t in ts:
            aT, aCT = estado(t)
            pl = plantada(t, a)
            linhas.append((aT, aCT, pl, venc))
        aT_fim, _ = estado(int(mortes[(mortes > a) & (mortes <= b)].max()) - 1) if ((mortes > a) & (mortes <= b)).any() else (5, 5)
        if plantada(b, a) and venc in ("T", "CT"):
            # todos os T morreram depois de plantar? (ultimo estado antes do fim com T = 1 e morte dele)
            pos_bomba.append((aT_fim, venc))
    duelos = {}
    for t in ticks_duelos:
        r = [(a, b) for a, b, _ in rounds if a <= t <= b]
        if not r or t not in time_eu.index:
            duelos[t] = None
            continue
        aT, aCT = estado(t)
        lado = int(time_eu.loc[t])
        pl = plantada(t, r[0][0])
        duelos[t] = (aT, aCT, lado, pl)
    return linhas, duelos, pos_bomba


def ajustar_wp(linhas):
    """Logistica sem intercepto, simetrica (cada estado entra pelos dois times)."""
    X, y = [], []
    for aT, aCT, pl, venc in linhas:
        if aT == 0 or aCT == 0 or venc not in ("T", "CT"):
            continue
        for meu, dele, lado, ganhou in ((aT, aCT, 1, venc == "T"), (aCT, aT, -1, venc == "CT")):
            X.append(feats(meu, dele, lado, pl))
            y.append(float(ganhou))
    X, y = np.array(X), np.array(y)
    b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ b))
        g = X.T @ (y - p)
        Hm = (X * (p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(len(b))
        b = b + np.linalg.solve(Hm, g)
    return b, len(y)


def feats(meu, dele, lado, pl):
    d = meu - dele
    return [d, d / (meu + dele), lado * float(pl), float(lado)]


def wp(b, meu, dele, lado, pl, p_explode):
    if meu <= 0:
        return p_explode if (lado == 1 and pl) else 0.0
    if dele <= 0:
        return 1 - p_explode if (lado == -1 and pl) else 1.0
    return float(1 / (1 + np.exp(-np.dot(b, feats(meu, dele, lado, pl)))))


def valores(df):
    """O valor de cada duelo, igual ao perfil.py (corrida pelo primeiro dano, curva por situacao)."""
    t_ini, ev, t_eu = tempos(df, "dano")
    d = df.assign(t_ini=t_ini, ev_ini=ev)
    bandas = {tp: 1.06 * np.std(g.loc[g["ev_ini"] == 1, "t_ini"]) * max(1, (g["ev_ini"] == 1).sum()) ** (-1 / 5)
              for tp, g in d.groupby("tipo")}
    dens = {}
    for chave, g in d.groupby(["estrato", "tipo"]):
        st, sj, _ = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
        dens[chave] = densidade(st, sj, bandas[chave[1]]) if len(st) else (lambda x: np.zeros(1))
    v = []
    for i, r in enumerate(d.to_dict("records")):
        t = t_eu[i]
        if t is None or not np.isfinite(t):
            t = r["t_ini"]
        t = max(float(t), 1 / 64)
        v.append(float(dens[(r["estrato"], r["tipo"])](t)[0]) * t)
    return np.array(v)


def pesos_de(df, dwp=None):
    v = valores(df)
    if dwp is not None:
        v = v * dwp
    est = df["estrato"].to_numpy()
    return np.array([v[est == e].sum() for e in IDS]) / v.sum()


def main():
    pasta, duelos_p = sys.argv[1:3]
    eu = meu_steamid()
    bruto = json.load(open(duelos_p, encoding="utf-8"))
    df = preparar(duelos_p)
    arquivos = {d["id"]: d["arquivo"] for d in bruto["demos"]}
    todas_linhas, por_duelo, pos_bomba = [], {}, []
    for id_demo, arq in arquivos.items():
        ticks = df.loc[df["demo"] == id_demo, "t0"].astype(int).tolist()
        linhas, duelos, pb = ler_demo(os.path.join(pasta, arq), ticks, eu)
        todas_linhas += linhas
        pos_bomba += pb
        for t, e in duelos.items():
            por_duelo[(id_demo, t)] = e
        print(f"demo {id_demo}: {len(linhas)} estados de round, {len(ticks)} duelos", flush=True)
    b, n = ajustar_wp(todas_linhas)
    so_bomba = [v for a, v in pos_bomba if a == 0]
    p_explode = float(np.mean([v == "T" for v in so_bomba])) if len(so_bomba) >= 5 else 0.25
    print(f"\nchance de vencer o round: logistica com {n} estados (os dois lados); coeficientes {np.round(b, 3).tolist()}")
    print("  exemplos (teu time x inimigos, sem bomba, lado CT):", ", ".join(f"{a}x{e} {100 * wp(b, a, e, -1, False, p_explode):.0f}%" for a, e in ((5, 5), (5, 4), (4, 5), (3, 3), (2, 1), (1, 2), (1, 1))))
    dwp, faltou = [], 0
    for r in df.to_dict("records"):
        e = por_duelo.get((r["demo"], int(r["t0"])))
        if e is None:
            dwp.append(np.nan); faltou += 1
            continue
        aT, aCT, lado_num, pl = e
        lado = 1 if lado_num == 2 else -1
        meu, dele = (aT, aCT) if lado == 1 else (aCT, aT)
        dwp.append(wp(b, meu, dele - 1, lado, pl, p_explode) - wp(b, meu - 1, dele, lado, pl, p_explode))
    dwp = np.array(dwp)
    dwp = np.where(np.isfinite(dwp), dwp, np.nanmean(dwp))
    print(f"duelos sem estado (usam a media): {faltou} de {len(df)}")
    est = df["estrato"].to_numpy()
    print("\nquanto o round muda com o duelo (media por situacao):", "  ".join(f"{e} {dwp[est == e].mean():.2f}" for e in IDS))
    wA = pesos_de(df)
    wE = pesos_de(df, dwp)
    print(f"\n{'':34s}" + "".join(f"{e:>9s}" for e in IDS))
    print(f"{'atual (duelo)':34s}" + "".join(f"{100 * x:8.1f}%" for x in wA))
    print(f"{'WPA (round)':34s}" + "".join(f"{100 * x:8.1f}%" for x in wE))
    rng = np.random.default_rng(11)
    bootA, bootE, bootD = [], [], []
    for _ in range(600):
        ix = rng.integers(0, len(df), len(df))
        s = df.iloc[ix].reset_index(drop=True)
        a_, e_ = pesos_de(s), pesos_de(s, dwp[ix])
        bootA.append(a_); bootE.append(e_); bootD.append(e_ - a_)
    bootA, bootE, bootD = map(np.array, (bootA, bootE, bootD))
    print(f"{'diferenca WPA - atual, IC 95%':34s}" + "".join(f" {100 * lo:+.1f}/{100 * hi:+.1f}" for lo, hi in zip(np.quantile(bootD, 0.025, 0), np.quantile(bootD, 0.975, 0))))
    # efeito na sens (mesma conta do pesos_robustez.py)
    c = np.array([CURV[e] for e in IDS])
    M = 20000
    dd = rng.normal(0, 0.20, (M, len(IDS)))

    def efeito(w_usado, w_verdade):
        x = (dd * w_usado * c).sum(1) / (w_usado * c).sum()
        x0 = (dd * w_verdade * c).sum(1) / (w_verdade * c).sum()
        dx = x - x0
        return 100 * (np.exp(np.sqrt(np.mean(dx ** 2))) - 1), 100 * np.mean((w_verdade * c).sum() * dx ** 2)
    a1, p1 = efeito(wA, wE)
    print(f"\nse o certo for o WPA e o app usar o atual: sens muda {a1:.2f}% (tipico), perda {p1:.4f}%")
    ef_E = np.array([efeito(bootE[i], wE) for i in range(0, 600, 3)])
    ef_A = np.array([efeito(bootA[i], wA) for i in range(0, 600, 3)])
    print(f"ruido do proprio peso (sorteio): atual {np.median(ef_A[:, 0]):.2f}% / perda {np.median(ef_A[:, 1]):.4f}% | WPA {np.median(ef_E[:, 0]):.2f}% / perda {np.median(ef_E[:, 1]):.4f}%")
    # decisao: erro esperado de cada escolha contra o objetivo do round (vies^2 + ruido)
    perda_atual = p1 + np.median(ef_A[:, 1])
    perda_wpa = np.median(ef_E[:, 1])
    print(f"perda esperada contra o objetivo do round: atual {perda_atual:.4f}% (vies + ruido) | WPA {perda_wpa:.4f}% (so ruido)")
    json.dump({"coef_wp": b.tolist(), "p_explode": p_explode, "pesos_atual": wA.tolist(), "pesos_wpa": wE.tolist(),
               "dwp_medio_por_situacao": {e: float(dwp[est == e].mean()) for e in IDS}},
              open(os.path.join(os.path.dirname(os.path.abspath(duelos_p)), "pesos_wpa.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
