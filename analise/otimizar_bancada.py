"""Quantos alvos por bloco (e quantas rodadas) com as REGRAS DA BANCADA PSA dele, por duracao.

Regras fixas, iguais a calibracao da bancada PSA v3 (bancada-psa-como-funciona.md, 6.4 e 6.5):
  faixa da 1a rodada de /1,732 a x1,732 (largura ln 3), centrada na sens dele;
  sondas a 25% e 75% da faixa: A = centro / 1,316 e B = centro x 1,316 na 1a rodada;
  w = diferenca / MDE de 95% (t de Student com os gl medidos + 6 do ruido inicial), entre -1 e 1;
  centro novo = centro - w x faixa/4 (w = 1 leva o centro ate a sonda que venceu);
  a faixa cai pela metade a cada rodada; ordem A B B A, B A A B, alternando.
No app (onde a "faixa" e a distancia entre as sondas): W0 = ln3/2, rho = 0,5, k = 0,5, gama = 1, gl0 = 6.
Com --pontas: o centro anda EXATAMENTE como na bancada (w x faixa/4, a faixa cai pela metade), mas
as sondas ficam nas pontas da faixa (/1,732 e x1,732 na 1a rodada), como nas primeiras versoes do app:
W0 = ln 3, rho = 0,5, k = 0,25, gama = 1, gl0 = 6.

Livre (a bancada nao fixa isso, ou fixa para um teste de kills, nao de alvos): alvos por bloco de
cada rodada, numero de rodadas e aquecimento no comeco. Mesma simulacao do otimizar_livre.py
(simular_v: ruido de cada dia sorteado de x0,5 a x2, cansaco, 25 cenarios de custo de troca e
aquecimento), mesmos sorteios para todos os desenhos, sem passar do tempo. Descida coordenada nos
inteiros (um a um, passando alvos entre rodadas, uma rodada a mais ou a menos) e confere em 300 mil
dias novos contra o desenho que esta no app.

Uso: python otimizar_bancada.py <duracao> [N] [--pontas] [--sem-custo] [--igual] [--de arquivo.json] [--saida arquivo.json]
     --pontas: sondas nas pontas da faixa (primeiras versoes), o resto igual a bancada
     --sem-custo: otimiza sem o custo de troca nem o aquecimento (a conferencia final continua com eles)
     --igual: o mesmo numero de alvos em todas as rodadas (como os kills fixos da bancada)
     duracao: 8, 11.8, 16, 20, 25 ou 35 (minutos; o tempo maximo do desenho)
"""
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import otimizar_exato as oe  # noqa: E402
from concorrentes_rodada import simular_v, sortear_adapt  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
REGRAS = {"W0": float(oe.LN3 / 2), "rho": 0.5, "k": 0.5, "gam": 1.0, "gl0": 6}
if "--pontas" in sys.argv:
    REGRAS = {"W0": float(oe.LN3), "rho": 0.5, "k": 0.25, "gam": 1.0, "gl0": 6}


def bancada(n, aquec=0):
    return dict(REGRAS, n=list(n), adapt=0, aquec=int(aquec))


def otimizar(p0, s, ad, orc, igual=False, max_rodadas=16, passes=40):
    p = copy.deepcopy(p0)

    def custo(q):
        l, m, _ = simular_v(q, s, adapta=ad)
        return float(np.mean(l)) + (1.0 if m > orc + 1e-9 else 0.0)

    def cabe(q):
        while simular_v(q, s, adapta=ad)[1] > orc + 1e-9 and max(q["n"]) > 2:
            if igual:
                q["n"] = [q["n"][0] - 1] * len(q["n"])
            else:
                q["n"][int(np.argmax(q["n"]))] -= 1
        return q

    p = cabe(p)
    melhor = custo(p)
    for it in range(passes):
        mudou = False
        R = len(p["n"])
        cands = []
        for d in (8, 4, 2, 1):
            if igual:
                for sinal in (1, -1):
                    cands.append([max(2, p["n"][0] + sinal * d)] * R)
                continue
            for r in range(R):
                for sinal in (1, -1):
                    q = list(p["n"]); q[r] += sinal * d
                    cands.append(q)
                for r2 in range(R):
                    if r2 != r:
                        q = list(p["n"]); q[r] += d; q[r2] -= d
                        cands.append(q)
        for nq in cands:
            if min(nq) < 2 or max(nq) > 200 or nq == p["n"]:
                continue
            q = copy.deepcopy(p); q["n"] = nq
            v = custo(q)
            if v < melhor - 1e-9:
                p, melhor, mudou = q, v, True
        for acao in ("mais", "menos"):
            q = copy.deepcopy(p)
            if acao == "mais" and len(q["n"]) < max_rodadas:
                q["n"].append(q["n"][-1]); q = cabe(q)
            elif acao == "menos" and len(q["n"]) > 1:
                q["n"].pop()
            else:
                continue
            v = custo(q)
            if v < melhor - 1e-9:
                p, melhor, mudou = q, v, True
        for d in (8, 4, 2, 1):
            for sinal in (1, -1):
                q = copy.deepcopy(p); q["aquec"] = max(0, p["aquec"] + sinal * d)
                if q["aquec"] != p["aquec"]:
                    v = custo(q)
                    if v < melhor - 1e-9:
                        p, melhor, mudou = q, v, True
        print(f"  passada {it + 1}: perda {100 * melhor:.4f}% | n {p['n']} | aquec {p['aquec']} | "
              f"{simular_v(p, s, adapta=ad)[1]:.2f} min", flush=True)
        if not mudou:
            break
    return p, melhor


def main():
    dur = sys.argv[1]
    N = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 120000
    orc = float(dur)
    sem_custo = "--sem-custo" in sys.argv
    igual = "--igual" in sys.argv
    app = json.load(open(os.path.join(BASE, f"otimo_livre_{dur}_semcusto_adapt0.json"), encoding="utf-8"))["desenho"]
    if "--de" in sys.argv:
        p0 = json.load(open(sys.argv[sys.argv.index("--de") + 1], encoding="utf-8"))["desenho"]
    else:
        # partida: a quantidade de alvos da primeira versao (36, 36, 24, 12, 12), escalada para caber
        p0 = bancada([36, 36, 24, 12, 12] if not igual else [24] * 5)
    s = oe.Sorteio(N, 4242, max_blocos=64, ruido_incerto=True)
    ad = None if sem_custo else sortear_adapt(N)
    print(f"{dur} min | partida: n {p0['n']} perda {100 * simular_v(p0, s, adapta=ad)[0].mean():.4f}% "
          f"({simular_v(p0, s, adapta=ad)[1]:.2f} min) | app agora: {100 * simular_v(app, s, adapta=ad)[0].mean():.4f}%", flush=True)
    p, v = otimizar(p0, s, ad, orc, igual=igual)
    s2 = oe.Sorteio(300000, 99, max_blocos=64, ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    la, _, ea = simular_v(app, s2, adapta=ad2)
    lb, mb, eb = simular_v(p, s2, adapta=ad2)
    d = lb - la
    erro = lambda e: 100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1)
    res = {"desenho": p, "minutos": mb, "perda": 100 * lb.mean(), "perda_app": 100 * la.mean(), "diferenca": 100 * d.mean(),
           "erro_padrao": 100 * d.std() / np.sqrt(len(d)), "erro_sens": erro(eb), "erro_sens_app": erro(ea),
           "faixa_final": float(np.exp(p["W0"] * p["rho"] ** (len(p["n"]) - 1) / 2))}
    print(f"\nFINAL {dur} min ({mb:.2f} min): n {p['n']} aquec {p['aquec']} | perda {res['perda']:.4f}% contra {res['perda_app']:.4f}% "
          f"do app (dif {res['diferenca']:+.4f} +- {res['erro_padrao']:.4f}) | erro de sens {res['erro_sens']:.1f}% (app {res['erro_sens_app']:.1f}%) "
          f"| ultima rodada: sondas a x{res['faixa_final']:.4f}", flush=True)
    suf = ("_pontas" if "--pontas" in sys.argv else "") + ("_semcusto" if sem_custo else "") + ("_igual" if igual else "")
    destino = sys.argv[sys.argv.index("--saida") + 1] if "--saida" in sys.argv else os.path.join(BASE, f"otimo_bancada_{dur}{suf}.json")
    json.dump(res, open(destino, "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main()
