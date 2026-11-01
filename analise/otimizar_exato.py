"""Numeros exatos do PSA do dia por otimizacao (nada de multiplo redondo).

Simula o protocolo bloco a bloco, com os MESMOS sorteios para todos os desenhos comparados
(numeros aleatorios comuns): a diferenca entre dois desenhos sai quase sem ruido de
simulacao. Modelo:
  nota do bloco = curva(x) + ruido; ruido = raiz(sd_duelo^2 / duelos + sd_bloco^2)
  sd_duelo = 0,38 e sd_bloco = 0,04 no comeco; com cansaco, sd_duelo +10% e sd_bloco +0,02
  a cada 10 minutos de teste (sem cansaco, mais alvos sempre ajudam e nao existe "melhor
  tamanho"). Curvas: pico, fundo chato e torta (perda 4x mais rapida para cima), melhor sens
  sorteada entre -40% e +40% da de partida. Tempo: 1,05 s por duelo (kill + 0,45 s de
  espera), 6 s de pausa por bloco, aquecimento 20, 3 alvos de adaptacao por bloco.
  Rodada: A B B A / B A A B nas pontas; w = diferenca / (gama x t975 x erro), entre -1 e 1;
  centro -= w x k x faixa; faixa x= rho.
Objetivo: perda media de desempenho (tempo ate matar) por nao estar na melhor sens.

Otimiza por descida coordenada: duelos de cada rodada (inteiros, um por um), numero de
rodadas, faixa inicial W0, passo k, encolhimento rho e gama. Depois confere o vencedor com
sorteios novos e mede a diferenca para o atual com erro padrao.

Uso: python otimizar_exato.py [N]   (N = dias simulados por avaliacao; padrao 120000)
"""
import json
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LN3 = np.log(3)
SIGMA0, GL0 = 0.088, 6
MEIA = np.log(2) / 2


def t975(gl):
    z = 1.959964
    z3, z5, z7 = z ** 3, z ** 5, z ** 7
    return z + (z3 + z) / (4 * gl) + (5 * z5 + 16 * z3 + 3 * z) / (96 * gl ** 2) + (3 * z7 + 19 * z5 + 17 * z3 - 15 * z) / (384 * gl ** 3)


def curva(x, x0, tipo):
    """0 pico, 1 fundo chato, 2 torta (usadas para otimizar); 3 vira reta longe do otimo,
    4 fica mais ingreme longe (so para conferir robustez, o otimizador nunca viu)."""
    d = x - x0
    pico = 0.28 * d * d
    chato = 0.9 * np.maximum(0.0, np.abs(d) - MEIA) ** 2 + 0.02 * d * d
    torta = np.where(d > 0, 0.5, 0.125) * d * d
    s = 0.3
    reta = 2 * 0.28 * s * s * (np.sqrt(1 + (d / s) ** 2) - 1)
    ingreme = 0.28 * d * d + 0.6 * d ** 4
    return np.select([tipo == 0, tipo == 1, tipo == 2, tipo == 3], [pico, chato, torta, reta], ingreme)


class Sorteio:
    def __init__(self, N, semente, max_blocos=64, ruido_incerto=False):
        r = np.random.default_rng(semente)
        self.x0 = r.uniform(-0.4, 0.4, N)
        self.tipo = np.arange(N) % 3
        self.Z = r.standard_normal((N, max_blocos)).astype(np.float64)
        self.f0 = curva(self.x0, self.x0, self.tipo)
        # ruido verdadeiro de cada dia: o teu ainda nao foi medido, entao sorteia de x0,5 a x2
        # (log-uniforme) em volta do valor do modelo
        self.escala = np.exp(r.uniform(np.log(0.5), np.log(2.0), N)) if ruido_incerto else None


def simular(p, s, cansaco=True, t_duelo=1.05, t_pausa=6.0, escala_ruido=1.0, escala_curva=1.0):
    n, W, k, rho, gam = p["n"], p["W0"], p["k"], p["rho"], p["gam"]
    adapt, aquec = p.get("adapt", 3), p.get("aquec", 20)
    gl0 = p.get("gl0", GL0)
    if s.escala is not None:
        escala_ruido = escala_ruido * s.escala
    N = len(s.x0)
    c = np.zeros(N)
    soma2 = np.zeros(N)
    gl_med = 0
    minuto = aquec * t_duelo / 60
    kb = 0
    for r, nd in enumerate(n):
        a, b = c - W / 2, c + W / 2
        ordem = "ABBA" if r % 2 == 0 else "BAAB"
        ys = {"A": [], "B": []}
        for lado in ordem:
            x = a if lado == "A" else b
            if cansaco:
                sdd = 0.38 * (1 + 0.10 * minuto / 10)
                sdb = 0.04 + 0.02 * minuto / 10
            else:
                sdd, sdb = 0.38, 0.04
            sd = escala_ruido * np.sqrt(sdd ** 2 / nd + sdb ** 2)
            ys[lado].append(escala_curva * curva(x, s.x0, s.tipo) + sd * s.Z[:, kb])
            kb += 1
            minuto += ((nd + adapt) * t_duelo + t_pausa) / 60
        escala = np.sqrt(nd / 24)
        for lado in "AB":
            v = np.array(ys[lado]) * escala
            soma2 += ((v - v.mean(axis=0)) ** 2).sum(axis=0)
            gl_med += v.shape[0] - 1
        gl = gl_med + gl0
        sig24 = np.sqrt((soma2 + gl0 * SIGMA0 ** 2) / gl)
        se = sig24 / escala * np.sqrt(1 / len(ys["A"]) + 1 / len(ys["B"]))
        delta = np.mean(ys["B"], axis=0) - np.mean(ys["A"], axis=0)
        w = np.clip(delta / (gam * t975(gl) * se), -1, 1)
        c = c - w * k * W
        W *= rho
    perda = np.exp(escala_curva * (curva(c, s.x0, s.tipo) - s.f0)) - 1
    return perda, minuto, c - s.x0


def otimizar(p0, s, cansaco=True, passes=12, log=True):
    p = json.loads(json.dumps(p0))
    def f(q):
        return float(np.mean(simular(q, s, cansaco)[0]))
    melhor = f(p)
    passos = {"W0": 0.08, "k": 0.03, "rho": 0.05, "gam": 0.15}
    limites = {"W0": (np.log(1.5), np.log(8)), "k": (0.05, 0.6), "rho": (0.2, 0.9), "gam": (0.2, 3.0)}
    for it in range(passes):
        mudou = False
        # duelos de cada rodada, um por um
        for r in range(len(p["n"])):
            for d in (16, 8, 4, 2, 1):
                for sinal in (1, -1):
                    while True:
                        q = json.loads(json.dumps(p))
                        q["n"][r] = int(q["n"][r] + sinal * d)
                        if q["n"][r] < 2 or q["n"][r] > 200:
                            break
                        v = f(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
                        else:
                            break
        # numero de rodadas: tirar a ultima ou por mais uma (com o tamanho da ultima)
        for acao in ("mais", "menos"):
            q = json.loads(json.dumps(p))
            if acao == "mais" and len(q["n"]) < 9:
                q["n"].append(q["n"][-1])
            elif acao == "menos" and len(q["n"]) > 2:
                q["n"].pop()
            else:
                continue
            v = f(q)
            if v < melhor - 1e-9:
                p, melhor, mudou = q, v, True
        # parametros continuos
        for nome in ("W0", "k", "rho", "gam"):
            for sinal in (1, -1):
                while True:
                    q = dict(p)
                    q["n"] = list(p["n"])
                    q[nome] = float(np.clip(p[nome] + sinal * passos[nome], *limites[nome]))
                    if q[nome] == p[nome]:
                        break
                    v = f(q)
                    if v < melhor - 1e-9:
                        p, melhor, mudou = q, v, True
                    else:
                        break
        if log:
            mins = simular(p, s, cansaco)[1]
            print(f"  passe {it + 1}: perda {100 * melhor:.4f}% | {mins:.2f} min | n={p['n']} W0=x{np.exp(p['W0']):.3f} "
                  f"k={p['k']:.3f} rho={p['rho']:.3f} gama={p['gam']:.3f}", flush=True)
        if not mudou:
            for nome in passos:
                passos[nome] /= 2
            if max(passos.values()) < 0.004:
                break
    return p, melhor


def otimizar_orcamento(p0, s, orcamento, cansaco=True, passes=10, passos0=None, ds=None):
    """Melhor desenho que cabe em `orcamento` minutos: mesma descida coordenada, mas com
    trocas de duelos entre rodadas (tira de uma, poe na outra) e nada que passe do tempo."""
    p = json.loads(json.dumps(p0))
    def custo(q):
        l, m, _ = simular(q, s, cansaco)
        return float(np.mean(l)) + (1.0 if m > orcamento + 1e-9 else 0.0)
    # comeca encolhendo os duelos ate caber
    while simular(p, s, cansaco)[1] > orcamento and max(p["n"]) > 2:
        i = int(np.argmax(p["n"]))
        p["n"][i] -= 1
    melhor = custo(p)
    passos = dict(passos0) if passos0 else {"W0": 0.08, "k": 0.03, "rho": 0.05, "gam": 0.15}
    limites = {"W0": (np.log(1.5), np.log(8)), "k": (0.05, 0.6), "rho": (0.2, 0.95), "gam": (0.2, 4.0)}
    R = len(p["n"])
    for it in range(passes):
        mudou = False
        for d in (ds or ((8, 4, 2, 1) if it == 0 else (4, 2, 1))):
            for r in range(R):
                for sinal in (1, -1):              # mexer uma rodada so
                    q = json.loads(json.dumps(p))
                    q["n"][r] += sinal * d
                    if 2 <= q["n"][r] <= 200:
                        v = custo(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
                for s2 in range(R):                 # passar duelos de uma rodada para outra
                    if s2 == r:
                        continue
                    q = json.loads(json.dumps(p))
                    q["n"][r] += d
                    q["n"][s2] -= d
                    if q["n"][s2] >= 2:
                        v = custo(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
        for nome in ("W0", "k", "rho", "gam"):
            for sinal in (1, -1):
                while True:
                    q = dict(p)
                    q["n"] = list(p["n"])
                    q[nome] = float(np.clip(p[nome] + sinal * passos[nome], *limites[nome]))
                    if q[nome] == p[nome]:
                        break
                    v = custo(q)
                    if v < melhor - 1e-9:
                        p, melhor, mudou = q, v, True
                    else:
                        break
        # quanto confiar no ruido de partida (graus de liberdade do prior), inteiro
        if "gl0" in p:
            for d in (4, 2, 1):
                for sinal in (1, -1):
                    q = json.loads(json.dumps(p))
                    q["gl0"] = int(max(1, p["gl0"] + sinal * d))
                    if q["gl0"] == p["gl0"]:
                        continue
                    v = custo(q)
                    if v < melhor - 1e-9:
                        p, melhor, mudou = q, v, True
        # numero de rodadas: uma a mais (tirando duelos das maiores ate caber) ou uma a menos
        for acao in ("mais", "menos"):
            q = json.loads(json.dumps(p))
            if acao == "mais" and len(q["n"]) < 14:
                q["n"].append(q["n"][-1])
                while simular(q, s, cansaco)[1] > orcamento and max(q["n"]) > 2:
                    q["n"][int(np.argmax(q["n"]))] -= 1
            elif acao == "menos" and len(q["n"]) > 2:
                q["n"].pop()
            else:
                continue
            v = custo(q)
            if v < melhor - 1e-9:
                p, melhor, mudou = q, v, True
                R = len(p["n"])
        if not mudou:
            for nome in passos:
                passos[nome] /= 2
            if max(passos.values()) < 0.002:
                break
    return p, melhor


def main_polir(orcamento, arquivo, extras=()):
    """Refina o desenho de um tempo com 200 mil dias e passos finos (o ultimo algarismo).
    extras: 'adapt=1' 'aquec=0' trocam esses numeros antes de refinar."""
    incerto = "incerto" in extras
    N = next((int(e.split("=")[1]) for e in extras if e.startswith("N=")), 200000)
    s = Sorteio(N, 31337, ruido_incerto=incerto)
    dado = json.load(open(arquivo, encoding="utf-8"))
    p0 = dado["desenho"] if "desenho" in dado else next(iter(dado.values()))["desenho"]
    for e in extras:
        if "=" not in e or e.startswith("N="):
            continue
        k, v = e.split("=")
        p0[k] = int(v)
    print(f"inicio: n={p0['n']} perda {100 * np.mean(simular(p0, s)[0]):.4f}% {simular(p0, s)[1]:.2f} min", flush=True)
    p, v = otimizar_orcamento(p0, s, orcamento, passes=12, passos0={"W0": 0.02, "k": 0.01, "rho": 0.01, "gam": 0.05}, ds=(2, 1))
    s2 = Sorteio(300000, 99991, ruido_incerto=incerto)
    atual = {"n": [36, 36, 24, 12, 12], "W0": float(LN3), "k": 0.25, "rho": 0.5, "gam": 1.0, "adapt": 3, "aquec": 20}
    cmp = comparar(atual, p, s2, True)
    cmp0 = comparar(p0, p, s2, True)
    print(f"polido{' (ruido incerto)' if incerto else ''}: n={p['n']} W0=x{np.exp(p['W0']):.4f} k={p['k']:.4f} rho={p['rho']:.4f} gama={p['gam']:.4f} gl0={p.get('gl0', GL0)} "
          f"| {cmp['min_b']:.2f} min | perda {cmp['perda_b']:.4f}% (atual {cmp['perda_a']:.4f}%, dif {cmp['diferenca']:+.4f} +- {cmp['erro_padrao']:.4f}) "
          f"| vs antes de polir: {cmp0['diferenca']:+.4f} +- {cmp0['erro_padrao']:.4f} | erro de sens {cmp['erro_sens_b']:.1f}%", flush=True)
    sufixo = "_final.json" if incerto else "_polido.json"
    destino = arquivo.replace("_polido.json", ".json").replace("_polido_polido.json", ".json").replace(".json", sufixo)
    json.dump({"desenho": p, "conferencia": cmp, "vs_antes": cmp0}, open(destino, "w", encoding="utf-8"), indent=1)


def main_orcamento(orcamentos):
    """Fronteira perda x minutos: para cada tempo, o melhor desenho exato (4 a 9 rodadas)."""
    s = Sorteio(40000, 2026)
    s2 = Sorteio(200000, 777)
    atual = {"n": [36, 36, 24, 12, 12], "W0": float(LN3), "k": 0.25, "rho": 0.5, "gam": 1.0, "adapt": 3, "aquec": 20}
    la, ma, ea = simular(atual, s2)
    print(f"atual: {ma:.2f} min, perda {100 * la.mean():.4f}%, erro de sens {100 * (np.exp(np.sqrt(np.mean(ea ** 2))) - 1):.1f}%", flush=True)
    resultados = {}
    for orc in orcamentos:
        melhor = None
        for R in ((4, 5, 6) if orc < 14 else (5, 6, 7, 8, 9)):
            perfil = np.linspace(1.6, 0.6, R)     # comeca com mais duelos nas primeiras rodadas
            p0 = dict(atual)
            p0["n"] = [int(v) for v in np.maximum(2, perfil * 40)]
            p0["rho"], p0["k"], p0["gam"], p0["W0"] = 0.5 + 0.05 * (R - 5), 0.25, 1.0, float(LN3)
            p, v = otimizar_orcamento(p0, s, orc)
            if melhor is None or v < melhor[1]:
                melhor = (p, v)
        p = melhor[0]
        l, m, e = simular(p, s2)
        d = l - la
        resultados[str(orc)] = {"desenho": p, "minutos": m, "perda": 100 * l.mean(), "dif_vs_atual": 100 * d.mean(),
                                "erro_padrao_dif": 100 * d.std() / np.sqrt(len(d)),
                                "erro_sens": 100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1)}
        print(f"orcamento {orc:5.1f} min -> {m:5.2f} min | perda {100 * l.mean():.4f}% (atual {100 * la.mean():.4f}%, "
              f"dif {100 * d.mean():+.4f} +- {100 * d.std() / np.sqrt(len(d)):.4f}) | erro sens {resultados[str(orc)]['erro_sens']:.1f}% | "
              f"n={p['n']} W0=x{np.exp(p['W0']):.3f} k={p['k']:.4f} rho={p['rho']:.4f} gama={p['gam']:.4f}", flush=True)
    nome = "otimo_orcamento_" + "_".join(f"{o:g}" for o in orcamentos) + ".json"
    json.dump(resultados, open(__file__.replace("otimizar_exato.py", nome), "w", encoding="utf-8"), indent=1)


def comparar(pa, pb, s, cansaco=True):
    la, ma, ea = simular(pa, s, cansaco)
    lb, mb, eb = simular(pb, s, cansaco)
    d = lb - la
    return {"perda_a": 100 * la.mean(), "perda_b": 100 * lb.mean(), "diferenca": 100 * d.mean(),
            "erro_padrao": 100 * d.std() / np.sqrt(len(d)), "min_a": ma, "min_b": mb,
            "erro_sens_a": 100 * (np.exp(np.sqrt(np.mean(ea ** 2))) - 1), "erro_sens_b": 100 * (np.exp(np.sqrt(np.mean(eb ** 2))) - 1)}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "polir":
        return main_polir(float(sys.argv[2]), sys.argv[3], sys.argv[4:])
    if len(sys.argv) > 1 and sys.argv[1] == "orcamento":
        return main_orcamento([float(v) for v in sys.argv[2:]] or [8.0, 11.8, 16.0, 20.0, 25.0, 35.0])
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 120000
    atual = {"n": [36, 36, 24, 12, 12], "W0": float(LN3), "k": 0.25, "rho": 0.5, "gam": 1.0, "adapt": 3, "aquec": 20}
    t = time.time()
    s = Sorteio(N, 2026)
    print(f"atual: perda {100 * np.mean(simular(atual, s)[0]):.4f}% em {simular(atual, s)[1]:.2f} min (com cansaco)", flush=True)
    print("otimizando com cansaco...", flush=True)
    otimo, perda = otimizar(atual, s, cansaco=True)
    print(f"tempo {time.time() - t:.0f} s")
    # conferencia com sorteios novos
    s2 = Sorteio(N, 777)
    cmp = comparar(atual, otimo, s2, True)
    print("\nconferencia com sorteios novos (com cansaco):", json.dumps({k: round(v, 4) for k, v in cmp.items()}))
    cmp0 = comparar(atual, otimo, s2, False)
    print("mesmos desenhos sem cansaco:", json.dumps({k: round(v, 4) for k, v in cmp0.items()}))
    # perda x tempo: reotimiza so as quantidades para varios orcamentos de tempo (escala)
    print("\nperda do otimo escalado (todas as rodadas x fator), com cansaco, sorteios novos:")
    for fat in (0.6, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5):
        q = dict(otimo)
        q["n"] = [max(2, int(round(v * fat))) for v in otimo["n"]]
        l, m, _ = simular(q, s2, True)
        print(f"  x{fat:4.2f}: n={q['n']} -> {m:5.2f} min, perda {100 * l.mean():.4f}%")
    json.dump({"atual": atual, "otimo": otimo, "conferencia": cmp, "sem_cansaco": cmp0},
              open(__file__.replace("otimizar_exato.py", "otimo_psa.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
