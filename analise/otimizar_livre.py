"""Numeros exatos do PSA com faixa e passo PROPRIOS de cada rodada (quarta revisao), por duracao.

Mesmo jogo do otimizar_exato.py, mais o que faltava na conta: o custo de trocar de sens (cresce
com o tamanho da troca, some com os alvos) e o aquecimento natural ao longo do teste, os 25
cenarios do otimizar_adapt.py, um sorteado por dia; o ruido de cada dia sorteado entre x0,5 e x2.
Descida coordenada com numeros aleatorios comuns: alvos de cada rodada (um a um e passando alvos
entre rodadas), faixa de cada rodada, passo de cada rodada, gama, GL0 e numero de rodadas, sem
passar do tempo. Parte do desenho final da duracao (otimo_orcamento_<d>_final.json) na forma
livre (ou de outro arquivo, com --de). Confere em 300 mil dias novos contra o desenho atual.

Uso: python otimizar_livre.py <duracao> [N] [--de arquivo.json] [--gama-fixo]
     --gama-fixo: gama fica o do desenho atual (exige a mesma evidencia; robusto com ruido alto)
     --sem-custo: otimiza sem o custo de troca nem o aquecimento (a conferencia final continua com eles)
     --adapt N: alvos de adaptacao por bloco
     --saida arquivo.json: onde gravar (padrao: otimo_livre_<duracao><sufixo>.json)
     --max-rodadas K: limite de rodadas (padrao 16; acima disso os sorteios ficam maiores)
     --faixa-final F: regra de afinar (pedida por ele): a faixa encolhe a cada rodada e a ultima e x F
                      (a da primeira versao: x1,07177 = 3^(1/16))
     --afina-geometrico: com --faixa-final, a faixa encolhe pela mesma razao a cada rodada (zoom das
                      primeiras versoes); so a 1a faixa e o numero de rodadas sao otimizados
     --min-alvos M: toda rodada com pelo menos M alvos por bloco (sem isso, o otimizador deixa as rodadas
                      estreitas com 2 alvos: o zoom vira so de fachada)
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


def livre_de(p):
    """Desenho geometrico (W0, rho, k) escrito como faixa e passo de cada rodada."""
    q = copy.deepcopy(p)
    if "Ws" not in q:
        R = len(q["n"])
        q["Ws"] = [float(q["W0"] * q["rho"] ** r) for r in range(R)]
        q["ks"] = [float(q["k"])] * R
    q["W0"] = q["Ws"][0]
    return q


def afina(q, faixa_final):
    """Regra dele (02/11): a faixa encolhe (ou fica igual) a cada rodada e a ultima e sempre a menor."""
    if faixa_final is None:
        return True
    W = q["Ws"]
    return abs(W[-1] - faixa_final) < 1e-12 and all(W[i] >= W[i + 1] - 1e-12 for i in range(len(W) - 1))


def geo(q, faixa_final):
    """Zoom como nas primeiras versoes: a faixa encolhe pela MESMA razao a cada rodada, da 1a ate a menor
    (x faixa_final) na ultima. So a 1a faixa e o numero de rodadas sao livres; a razao sai deles."""
    R = len(q["n"]); W1 = q["Ws"][0]
    q["Ws"] = [float(W1 * (faixa_final / W1) ** (r / (R - 1))) for r in range(R)] if R > 1 else [W1]
    q["W0"] = q["Ws"][0]
    return q


def otimizar(p0, s, ad, orc, passes=12, passo_w=0.06, passo_k=0.02, passo_g=0.15, gama_fixo=False, max_rodadas=16, faixa_final=None, geometrico=False, min_alvos=2):
    p = copy.deepcopy(p0)

    def custo(q):
        l, m, _ = simular_v(q, s, adapta=ad)
        return float(np.mean(l)) + (1.0 if m > orc + 1e-9 else 0.0)

    while simular_v(p, s, adapta=ad)[1] > orc and max(p["n"]) > 2:
        p["n"][int(np.argmax(p["n"]))] -= 1
    melhor = custo(p)
    pw, pk, pg = passo_w, passo_k, passo_g
    for it in range(passes):
        mudou = False
        R = len(p["n"])
        for d in ((4, 2, 1) if it == 0 else (2, 1)):
            for r in range(R):
                for sinal in (1, -1):
                    q = copy.deepcopy(p); q["n"][r] += sinal * d
                    if min_alvos <= q["n"][r] <= 200:
                        v = custo(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
                for r2 in range(R):
                    if r2 == r:
                        continue
                    q = copy.deepcopy(p); q["n"][r] += d; q["n"][r2] -= d
                    if q["n"][r2] >= min_alvos:
                        v = custo(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
        lim_w = (np.log(1.2) if faixa_final is None else faixa_final, np.log(8))
        for chave, passo, lim in (("Ws", pw, lim_w), ("ks", pk, (0.01, 0.6))):
            for r in range(R):
                if chave == "Ws" and faixa_final is not None and r == R - 1:
                    continue                       # a ultima faixa e fixa (a menor)
                if chave == "Ws" and geometrico and r > 0:
                    continue                       # zoom geometrico: as outras faixas saem da 1a
                for sinal in (1, -1):
                    while True:
                        q = copy.deepcopy(p)
                        q[chave][r] = float(np.clip(p[chave][r] + sinal * passo, *lim))
                        if geometrico and chave == "Ws":
                            geo(q, faixa_final)
                        if q[chave][r] == p[chave][r] or not afina(q, faixa_final):
                            break
                        q["W0"] = q["Ws"][0]
                        v = custo(q)
                        if v < melhor - 1e-9:
                            p, melhor, mudou = q, v, True
                        else:
                            break
        for sinal in ((1, -1) if not gama_fixo else ()):
            while True:
                q = copy.deepcopy(p); q["gam"] = float(np.clip(p["gam"] + sinal * pg, 0.2, 4.0))
                if q["gam"] == p["gam"]:
                    break
                v = custo(q)
                if v < melhor - 1e-9:
                    p, melhor, mudou = q, v, True
                else:
                    break
        for d in (4, 2, 1):
            for sinal in (1, -1):
                q = copy.deepcopy(p); q["gl0"] = int(max(1, p.get("gl0", 16) + sinal * d))
                if q["gl0"] != p.get("gl0", 16):
                    v = custo(q)
                    if v < melhor - 1e-9:
                        p, melhor, mudou = q, v, True
        for acao in ("mais", "menos"):
            q = copy.deepcopy(p)
            if acao == "mais" and len(q["n"]) < max_rodadas:
                q["n"].append(q["n"][-1]); q["Ws"].append(q["Ws"][-1]); q["ks"].append(q["ks"][-1])
                while simular_v(q, s, adapta=ad)[1] > orc and max(q["n"]) > 2:
                    q["n"][int(np.argmax(q["n"]))] -= 1
            elif acao == "menos" and len(q["n"]) > 2:
                q["n"].pop(); q["Ws"].pop(); q["ks"].pop()
                if faixa_final is not None:
                    q["Ws"][-1] = faixa_final
            else:
                continue
            if geometrico:
                geo(q, faixa_final)
            if not afina(q, faixa_final) or min(q["n"]) < min_alvos:
                continue
            v = custo(q)
            if v < melhor - 1e-9:
                p, melhor, mudou = q, v, True
        print(f"  passada {it + 1}: perda {100 * melhor:.4f}% | n {p['n']} | faixas x" + ", ".join(f"{np.exp(w):.3f}" for w in p["Ws"])
              + " | passos " + ", ".join(f"{k:.4f}" for k in p["ks"]) + f" | gama {p['gam']:.4f} | gl0 {p.get('gl0')}", flush=True)
        if not mudou:
            pw, pk, pg = pw / 2, pk / 2, pg / 2
            if max(pw, pk, pg) < 0.002:
                break
    return p, melhor


def main():
    dur = sys.argv[1]
    N = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 120000
    de = sys.argv[sys.argv.index("--de") + 1] if "--de" in sys.argv else os.path.join(BASE, f"otimo_orcamento_{dur}_final.json")
    orc = float(dur)
    atual = json.load(open(os.path.join(BASE, f"otimo_orcamento_{dur}_final.json"), encoding="utf-8"))["desenho"]
    dado = json.load(open(de, encoding="utf-8"))
    if "desenho" in dado:
        base = dado["desenho"]
    elif "livre" in dado:
        base = dado["livre"]
    else:
        base = next(v for v in dado.values() if isinstance(v, dict) and "n" in v)
    p0 = livre_de(base)
    p0.setdefault("adapt", 1); p0.setdefault("aquec", 0); p0.setdefault("gl0", atual.get("gl0", 16))
    if "--adapt" in sys.argv:      # alvos de adaptacao por bloco (quarta revisao: 0 ganha em todos os cenarios de custo de troca)
        p0["adapt"] = int(sys.argv[sys.argv.index("--adapt") + 1])
    # ate 16 rodadas os sorteios sao os mesmos de sempre (64 blocos); com mais rodadas, sorteios maiores
    max_r = int(sys.argv[sys.argv.index("--max-rodadas") + 1]) if "--max-rodadas" in sys.argv else 16
    mb = max(64, 4 * max_r)
    s = oe.Sorteio(N, 4242, max_blocos=mb, ruido_incerto=True)
    sem_custo = "--sem-custo" in sys.argv
    ad = None if sem_custo else sortear_adapt(N)     # sem custo: so o modelo do otimizar_exato.py; a conferencia final e com custo
    ff = float(np.log(float(sys.argv[sys.argv.index("--faixa-final") + 1]))) if "--faixa-final" in sys.argv else None
    ma = int(sys.argv[sys.argv.index("--min-alvos") + 1]) if "--min-alvos" in sys.argv else 2
    p0["n"] = [max(ma, n) for n in p0["n"]]
    gm = "--afina-geometrico" in sys.argv
    if gm:
        geo(p0, ff)
    if ff is not None and not afina(p0, ff):
        # partida: encolhe em progressao geometrica da faixa da 1a rodada ate a menor na ultima
        R0 = len(p0["n"]); W1 = p0["Ws"][0]
        p0["Ws"] = [float(W1 * (ff / W1) ** (r / (R0 - 1))) for r in range(R0)]
        p0["W0"] = p0["Ws"][0]
    gf = "--gama-fixo" in sys.argv
    if gf:
        p0["gam"] = atual["gam"]      # exige a mesma forca de evidencia do desenho atual (robusto no ruido alto)
    # perda da partida JA com as regras aplicadas (antes saia antes do zoom e enganava)
    print(f"{dur} min | inicio: perda {100 * simular_v(p0, s, adapta=ad)[0].mean():.4f}% ({simular_v(p0, s, adapta=ad)[1]:.2f} min) | "
          f"atual: {100 * simular_v(atual, s, adapta=ad)[0].mean():.4f}%", flush=True)
    p, v = otimizar(p0, s, ad, orc, gama_fixo=gf, max_rodadas=max_r, faixa_final=ff, geometrico=gm, min_alvos=ma)
    # refino com passos finos
    p, v = otimizar(p, s, ad, orc, passes=8, passo_w=0.01, passo_k=0.005, passo_g=0.05, gama_fixo=gf, max_rodadas=max_r, faixa_final=ff, geometrico=gm, min_alvos=ma)
    s2 = oe.Sorteio(300000, 99, max_blocos=max(64, 4 * len(p["n"])), ruido_incerto=True)
    ad2 = sortear_adapt(300000, semente=77)
    la, m_atual, ea = simular_v(atual, s2, adapta=ad2)
    lb, mb, eb = simular_v(p, s2, adapta=ad2)
    d = lb - la
    erro = lambda e: 100 * (np.exp(np.sqrt(np.mean(e ** 2))) - 1)
    res = {"desenho": p, "minutos": mb, "perda": 100 * lb.mean(), "perda_atual": 100 * la.mean(), "diferenca": 100 * d.mean(),
           "erro_padrao": 100 * d.std() / np.sqrt(len(d)), "erro_sens": erro(eb), "erro_sens_atual": erro(ea)}
    print(f"\nFINAL {dur} min ({mb:.2f} min): perda {res['perda']:.4f}% contra {res['perda_atual']:.4f}% do atual "
          f"(dif {res['diferenca']:+.4f} +- {res['erro_padrao']:.4f}) | erro de sens {res['erro_sens']:.1f}% (atual {res['erro_sens_atual']:.1f}%)", flush=True)
    suf = ('_gfixo' if gf else '') + ('_semcusto' if sem_custo else '') + (f"_adapt{p['adapt']}" if "--adapt" in sys.argv else '') + (('_zoom' if gm else '_afina') if ff is not None else '') + (f"_min{ma}" if ma != 2 else '')
    destino = sys.argv[sys.argv.index("--saida") + 1] if "--saida" in sys.argv else os.path.join(BASE, f"otimo_livre_{dur}{suf}.json")
    json.dump(res, open(destino, "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main()
