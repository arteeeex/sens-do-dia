"""Monta o perfil de situacoes (e o peso de cada uma) a partir dos duelos das demos.

Peso de cada situacao = soma do "valor de 1% de tempo" dos duelos dela:

    valor do duelo i = f(t_i) * t_i

f(t) e a densidade do tempo do inimigo (Kaplan-Meier, com censura quando voce matou
antes ou ele sumiu) e t_i e o teu tempo ate o primeiro dano naquele duelo. f(t_i) diz
quantos duelos por segundo sao decididos exatamente no teu tempo; vezes t_i vira o
ganho de chance de vencer por 1% a menos de tempo. Duelo que voce ganharia de qualquer
jeito (inimigo muito mais lento) ou perderia de qualquer jeito vale pouco; duelo
decidido no milissegundo vale muito.

Saida: perfil.js (window.PERFIL) para o app e um resumo em texto.

Uso: python perfil.py <duelos.json> <cabeca.json> <saida.js> <resumo.txt>
"""
import json
import math
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JANELA = 2.5
ESTRATOS = [
    {"id": "fino", "nome": "Mira já em cima", "desc": "cabeça a menos de 1,5° da mira"},
    {"id": "curto", "nome": "Ajuste curto", "desc": "1,5° a 4°"},
    {"id": "flick", "nome": "Flick curto", "desc": "4° a 10°"},
    {"id": "medio", "nome": "Flick médio", "desc": "10° a 35°"},
    {"id": "virada", "nome": "Virada", "desc": "35° ou mais, fora da tua visão"},
    {"id": "rapido", "nome": "Alvo rápido", "desc": "alvo cruzando a 20°/s ou mais"},
]


def estrato(d):
    if d["theta"] >= 35:
        return "virada"
    if d["vel"] is not None and d["vel"] >= 20:
        return "rapido"
    if d["theta"] < 1.5:
        return "fino"
    if d["theta"] < 4:
        return "curto"
    if d["theta"] < 10:
        return "flick"
    return "medio"


def kaplan_meier(tempos, eventos):
    """Devolve tempos dos eventos e o tamanho do salto de S em cada um."""
    ordem = np.argsort(tempos, kind="stable")
    t, e = np.asarray(tempos)[ordem], np.asarray(eventos)[ordem]
    n = len(t)
    s = 1.0
    saltos_t, saltos = [], []
    i = 0
    while i < n:
        j = i
        while j < n and t[j] == t[i]:
            j += 1
        risco = n - i
        mortes = int(e[i:j].sum())
        if mortes:
            novo = s * (1 - mortes / risco)
            saltos_t.append(t[i])
            saltos.append(s - novo)
            s = novo
        i = j
    return np.array(saltos_t), np.array(saltos), s


def densidade(saltos_t, saltos, banda):
    def f(x):
        x = np.atleast_1d(x)[:, None]
        k = np.exp(-0.5 * ((x - saltos_t[None, :]) / banda) ** 2) / (banda * math.sqrt(2 * math.pi))
        return (k * saltos[None, :]).sum(axis=1)
    return f


HZ = 32
N_TRAJ = int(JANELA * HZ) + 1       # 81 amostras = 2,5 s


def velocidade_linear(tr, ds, k):
    """Velocidade do alvo na tela no fim da amostra k (unidades/s, eixo de lado e de altura),
    pela media dos ultimos 2 passos. Linear (e nao em graus) para servir em outra distancia."""
    if k < 1:
        return np.zeros(2)
    a = max(0, k - 2)
    passo = (np.asarray(tr[k]) - np.asarray(tr[a])) / ((k - a) / HZ)
    return passo * math.pi / 180 * ds[k]


def passo_linear(tr, ds, k):
    """Velocidade de UM passo (da amostra k-1 para a k), em unidades/s, na distancia da amostra k-1."""
    if k < 1:
        return np.zeros(2)
    return (np.asarray(tr[k]) - np.asarray(tr[k - 1])) * HZ * math.pi / 180 * ds[k - 1]


def continuar_caminhos(df):
    """O caminho real do inimigo acaba quando alguem morre (65% dos duelos antes de 1,5 s).
    No teste, se tu demora mais que o duelo real, o boneco ficaria parado. Aqui ele segue com
    o movimento de OUTRO inimigo real que ainda estava vivo naquele mesmo instante do duelo e
    se movia na velocidade mais parecida (mesmo tipo de duelo, de frente ou virada). O passo
    vai em unidades do jogo (de lado e de aproximacao), convertido para a distancia deste
    alvo, sem nunca chegar mais perto que o duelo mais perto das demos. Se o doador tambem
    acaba, escolhe outro, ate 2,5 s. Determinista: a mesma situacao sempre anda igual."""
    recs = df.to_dict("records")
    trs = [list(map(list, r["traj"])) for r in recs]
    dss = [list(r["dists"]) for r in recs]
    tipos = [r["tipo"] for r in recs]
    nreal = [len(t) for t in trs]
    # o alvo nunca chega mais perto do que o mais perto que ja aconteceu nas demos
    d_min = min(min(x) for x in dss if len(x))
    novos_tr, novos_ds, doacoes = [], [], []
    for i, r in enumerate(recs):
        tr = [list(p) for p in trs[i]]
        ds = list(dss[i])
        if not tr:
            tr, ds = [[0.0, 0.0]], [float(r["dist"])]
        usados = 0
        while len(tr) < N_TRAJ:
            k = len(tr) - 1
            v = passo_linear(tr, ds, k)
            vivos = [j for j in range(len(recs)) if j != i and nreal[j] > k + 1]
            cands = []
            # doador na mesma faixa de distancia (inimigo de perto nao anda como inimigo de longe),
            # do mesmo tipo de duelo; abre a faixa se tiver pouca gente
            for faixa in (1.3, 1.6, 2.2, None):
                for mesmo_tipo in (True, False):
                    cands = [j for j in vivos
                             if (not mesmo_tipo or tipos[j] == tipos[i])
                             and (faixa is None or 1 / faixa <= dss[j][k] / max(1.0, ds[-1]) <= faixa)]
                    if len(cands) >= 10:
                        break
                if len(cands) >= 10:
                    break
            if not cands:
                cands = vivos
            if not cands:
                break
            # casa o PROXIMO passo do doador com o ULTIMO passo real deste alvo (unidades/s): a costura
            # nao aparece. Teste contra o futuro real escondido (concorrentes_caminho.py, 01/11/2026):
            # ganhou da velocidade media dos 2 ultimos passos em 100% dos sorteios.
            dif = [np.hypot(*(passo_linear(trs[j], dss[j], k + 1) - v)) for j in cands]
            j = cands[int(np.argmin(dif))]
            usados += 1
            for m in range(k + 1, min(N_TRAJ, nreal[j])):
                passo = np.asarray(trs[j][m]) - np.asarray(trs[j][m - 1])
                escala = dss[j][m - 1] / max(1.0, ds[-1])            # mesmo deslocamento de lado, em unidades
                d_novo = max(d_min, ds[-1] + (dss[j][m] - dss[j][m - 1]))  # mesma aproximacao, em unidades
                tr.append([tr[-1][0] + passo[0] * escala, tr[-1][1] + passo[1] * escala])
                ds.append(d_novo)
        novos_tr.append(tr[:N_TRAJ])
        novos_ds.append(ds[:N_TRAJ])
        doacoes.append(usados)
    return novos_tr, novos_ds, nreal, doacoes


def fator_disco(p):
    """Quantil de |x| de um disco uniforme de raio 1 (marginal)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        u = (lo + hi) / 2
        g = (2 / math.pi) * (u * math.sqrt(1 - u * u) + math.asin(u))
        lo, hi = (u, hi) if g < p else (lo, u)
    return (lo + hi) / 2


def main():
    duelos_p, cabeca_p, saida_js, saida_txt = sys.argv[1:5]
    bruto = json.load(open(duelos_p, encoding="utf-8"))
    cab = json.load(open(cabeca_p, encoding="utf-8"))
    df = pd.DataFrame(bruto["duelos"])
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    df["estrato"] = [estrato(r) for r in df.to_dict("records")]

    # --- tempo do inimigo (evento) e censura, por tipo de duelo ---
    def evento_inimigo(r):
        if r["tipo"] == "frente":
            if pd.notna(r["ttd_ele"]):
                return r["ttd_ele"], 1
            fim = JANELA
            if pd.notna(r["t_kill"]):
                fim = min(fim, r["t_kill"])
            if pd.notna(r["visao_s"]):
                fim = min(fim, r["visao_s"] + 0.25)
            return fim, 0
        # virada: ele ja acertou; o que decide e voce acertar antes de morrer
        if pd.notna(r["t_morte"]):
            return r["t_morte"], 1
        fim = JANELA if pd.isna(r["t_kill"]) else min(JANELA, r["t_kill"])
        return fim, 0

    ev = [evento_inimigo(r) for r in df.to_dict("records")]
    df["t_ini"] = [e[0] for e in ev]
    df["ev_ini"] = [e[1] for e in ev]

    # --- teu tempo em cada duelo ---
    def meu_tempo(r):
        if pd.notna(r["ttd_eu"]):
            return r["ttd_eu"]
        if pd.notna(r["tiro_nele"]):
            return max(r["tiro_nele"], 1 / 64)   # atirou e errou: pelo menos isso
        return None

    df["t_eu"] = [meu_tempo(r) for r in df.to_dict("records")]

    # Kaplan-Meier do tempo do inimigo PROPRIO de cada situacao e tipo (frente/virada):
    # o tempo dele muda com a situacao (com a mira ja em cima, ele quase sempre ainda nao te
    # viu; no flick medio ele costuma ser rapido). Revisao de 01/11/2026.
    def valores_de(d):
        dens, info = {}, {}
        # largura da suavizacao: Silverman com TODOS os eventos do mesmo tipo de duelo (frente ou
        # virada). Uma por tipo, sem constante chutada (antes: 0,15 s fixo nos grupos com ate 5
        # eventos e piso de 0,03 s). A curva de cada situacao continua sendo o Kaplan-Meier dela.
        bandas = {}
        for tp, g in d.groupby("tipo"):
            tt = g.loc[g["ev_ini"] == 1, "t_ini"].to_numpy(float)
            bandas[tp] = 1.06 * np.std(tt) * len(tt) ** (-1 / 5)
        for chave, g in d.groupby(["estrato", "tipo"]):
            st, sj, s_fim = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
            banda = bandas[chave[1]]
            dens[chave] = densidade(st, sj, banda) if len(st) else (lambda x: np.zeros(np.atleast_1d(x).shape[0]))
            info["/".join(chave)] = {"eventos": int(g["ev_ini"].sum()), "n": int(len(g)), "banda_s": round(float(banda), 3),
                                     "sobrevive_ate_fim": round(float(s_fim), 3)}
        v = []
        for r in d.to_dict("records"):
            t = r["t_eu"]
            if t is None or not np.isfinite(t):
                t = r["t_ini"]                   # sem acao: avalia no fim do duelo dele
            t = max(float(t), 1 / 64)
            v.append(float(dens[(r["estrato"], r["tipo"])](t)[0]) * t)
        return np.array(v), info

    df["valor"], km_info = valores_de(df)

    # --- pesos por situacao ---
    linhas = []
    total_v = df["valor"].sum()
    for e in ESTRATOS:
        g = df[df["estrato"] == e["id"]]
        linhas.append({
            **e, "n": int(len(g)),
            "freq": float(len(g) / len(df)),
            "peso": float(g["valor"].sum() / total_v) if total_v > 0 else 0.0,
            "theta_med": float(g["theta"].median()) if len(g) else None,
            "dist_med": float(g["dist"].median()) if len(g) else None,
            "vel_med": float(pd.to_numeric(g["vel"], errors="coerce").median()) if len(g) else None,
            "teu_tempo_med": float(pd.to_numeric(g["t_eu"], errors="coerce").median()) if len(g) else None,
            "venceu_primeiro": float(((g["ttd_eu"].notna()) & (g["ttd_ele"].isna() | (g["ttd_eu"] < g["ttd_ele"]))).mean()) if len(g) else None,
        })

    # --- incerteza dos pesos: bootstrap nos duelos, refazendo o Kaplan-Meier de cada situacao ---
    rng = np.random.default_rng(7)
    boot = []
    for _ in range(1000):
        sub = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        vv, _ = valores_de(sub)
        ids = sub["estrato"].to_numpy()
        boot.append([vv[ids == e["id"]].sum() / vv.sum() for e in ESTRATOS])
    boot = np.array(boot)
    for i, l in enumerate(linhas):
        l["peso_ic"] = [float(np.quantile(boot[:, i], 0.025)), float(np.quantile(boot[:, i], 0.975))]

    # --- cabeca: meia-largura e meia-altura pelo disco uniforme (media de 4 quantis) ---
    m = cab["modelo"]
    ps = [0.5, 0.75, 0.9, 0.95]
    fat = [fator_disco(p) for p in ps]
    meia_l = float(np.mean([q / f for q, f in zip(m["lateral_abs_quantis_50_75_90_95"], fat)]))
    meia_a = float(np.mean([q / f for q, f in zip(m["vertical_abs_quantis_50_75_90_95"], fat)]))
    cabeca = {"meia_largura": round(meia_l, 2), "meia_altura": round(meia_a, 2),
              "centro_abaixo_do_olho": m["centro_abaixo_do_olho"], "n_tiros": m["n"]}

    # --- caminho do alvo ate 2,5 s (o real e, quando acaba, movimento real de outro inimigo) ---
    trs, dss, nreal, doacoes = continuar_caminhos(df)
    nreal_s = np.array(nreal) / HZ
    print(f"caminho real: mediana {np.median(nreal_s):.2f} s; {100 * np.mean(np.array(nreal) >= N_TRAJ):.0f}% chegam a 2,5 s; "
          f"emendas por situacao: mediana {np.median(doacoes):.0f}, max {max(doacoes)}")

    # --- situacoes para o app (so o necessario) ---
    sit = []
    for k, r in enumerate(df.to_dict("records")):
        sit.append({
            "e": r["estrato"], "v": 1 if r["tipo"] == "virada" else 0,
            "dy": round(r["dyaw"], 2), "dp": round(r["dpitch"], 2), "d": int(round(r["dist"])),
            "pe": round(float(r["pitch_eu"]), 1) if r.get("pitch_eu") is not None and np.isfinite(r["pitch_eu"]) else 0.0,
            "tr": [[round(a, 2), round(b, 2)] for a, b in trs[k]],
            "ds": [int(round(x)) for x in dss[k]],
            "nr": int(nreal[k]),      # quantas amostras do caminho sao deste inimigo (o resto e emenda)
            "w": round(r["valor"], 5),
        })
    perfil = {
        "versao": 1,
        "gerado": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": {"demos": len(bruto["demos"]), "periodo": [bruto["demos"][0]["data"], bruto["demos"][-1]["data"]],
                  "duelos": int(len(df)), "km": km_info},
        "cabeca": cabeca,
        "estratos": linhas,
        "situacoes": sit,
        "traj_hz": 32,
    }
    with open(saida_js, "w", encoding="utf-8") as f:
        f.write("// Gerado por analise/perfil.py a partir das tuas demos. Nao editar a mao.\n")
        f.write("window.PERFIL = ")
        json.dump(perfil, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    txt = []
    txt.append(f"Duelos validos: {len(df)} de {len(bruto['demos'])} demos ({perfil['fonte']['periodo'][0]} a {perfil['fonte']['periodo'][1]})")
    txt.append(f"Kaplan-Meier do inimigo: {json.dumps(km_info, ensure_ascii=False)}")
    txt.append(f"Cabeca: {cabeca}")
    txt.append("")
    txt.append(f"{'situacao':18s} {'n':>4s} {'aparece':>8s} {'peso':>7s} {'IC 95% do peso':>16s} {'theta':>6s} {'dist':>6s} {'vel':>6s} {'teu t':>6s} {'1o dano teu':>11s}")
    for l in linhas:
        txt.append(f"{l['nome']:18s} {l['n']:4d} {100 * l['freq']:7.1f}% {100 * l['peso']:6.1f}% "
                   f"{100 * l['peso_ic'][0]:6.1f}%-{100 * l['peso_ic'][1]:5.1f}% "
                   f"{(l['theta_med'] or 0):6.2f} {(l['dist_med'] or 0):6.0f} {(l['vel_med'] or 0):6.1f} "
                   f"{(l['teu_tempo_med'] or 0):6.3f} {100 * (l['venceu_primeiro'] or 0):10.0f}%")
    open(saida_txt, "w", encoding="utf-8").write("\n".join(txt) + "\n")
    print("\n".join(txt))
    print(f"\n-> {saida_js} ({len(sit)} situacoes)")


if __name__ == "__main__":
    main()
