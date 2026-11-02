"""Onde fica cada parte do corpo no jogo, medido nos tiros de todo mundo nas demos.

Para cada bala que acertou alguem (bullet_damage), o ponto do acerto e
    olho do atirador + direcao da bala x distancia percorrida
e a parte do corpo vem do player_hurt do mesmo tick. Entram balas em alvo em pe (sem
agachar), sem atravessar parede, perto do eixo do corpo (menos de 3,5 de lado). Isso da a
altura do acerto acima do pe do alvo na postura do jogo (o arquivo de hitbox vem na pose de
referencia, em pe reto e de bracos abertos).

A posicao do alvo na demo nao e a da compensacao de lag, entao a altura medida tem um erro
(cerca de 3,5 unidades). O erro borra as fronteiras e empurra o ponto de 50% para o lado da
parte com menos tiros. A fronteira usada (fronteiras_corrigidas) e o ponto de 50% do probit
corrigido pela formula de Tweedie: se a densidade dos tiros tem inclinacao b no log perto da
fronteira, o ponto de 50% cai b*s^2 abaixo dela (s = borrao, medido pela largura do proprio
probit; b de todos os tiros numa janela em volta da fronteira, JANELA_INCLINACAO). Fronteira =
ponto de 50% + b*s^2, com IC por 200 sorteios das balas. Ganhou dos outros jeitos em simulacao
com a fronteira conhecida (concorrentes_regioes.py, 01/11/2026).
Ficam tambem, para comparar: o probit sem correcao e a maxima verossimilhanca com densidade
livre (EM; verossimilhanca quase chata, IC de +-3 ou mais).

Uso: python medir_regioes.py <pasta_das_demos> <saida.json>
"""
import glob
import math
import json
import os
import sys

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OLHO_PE, OLHO_QUEDA = 64.06, 18.0
ESPINGARDAS = ("nova", "xm1014", "mag7", "sawedoff")
ROTULO = {"left_leg": 0, "right_leg": 0, "stomach": 1, "chest": 2, "neck": 2, "head": 3}
NOMES = ["pernas", "barriga", "peito", "cabeca"]


def sid(v):
    if v is None:
        return 0
    s = str(v).strip().split(".")[0]
    return int(s) if s.isdigit() else 0


def ler(pasta):
    demos = sorted(glob.glob(os.path.join(pasta, "match730_*.dem")), key=os.path.getmtime)
    linhas = []
    for i, d in enumerate(demos):
        p = DemoParser(d)
        bd = p.parse_event("bullet_damage", player=["X", "Y", "Z", "duck_amount"])
        h = p.parse_event("player_hurt")
        for df, a, v in ((bd, "attacker_steamid", "victim_steamid"), (h, "attacker_steamid", "user_steamid")):
            df[a] = df[a].map(sid)
            df[v] = df[v].map(sid)
        h = h.rename(columns={"user_steamid": "victim_steamid"})
        h = h[~h["weapon"].isin(ESPINGARDAS)]
        h = h.drop_duplicates(["tick", "attacker_steamid", "victim_steamid"], keep=False)
        bd = bd.drop_duplicates(["tick", "attacker_steamid", "victim_steamid"], keep=False)
        m = bd.merge(h[["tick", "attacker_steamid", "victim_steamid", "hitgroup", "weapon"]],
                     on=["tick", "attacker_steamid", "victim_steamid"], how="inner")
        linhas.append(m)
        print(f"demo {i}: {len(m)} balas com parte do corpo")
    A = pd.concat(linhas, ignore_index=True)
    olho_z = A["attacker_Z"] + OLHO_PE - OLHO_QUEDA * A["attacker_duck_amount"].fillna(0)
    dx, dy, dz = A["damage_dir_x"], A["damage_dir_y"], A["damage_dir_z"]
    n = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    dx, dy, dz = dx / n, dy / n, dz / n
    hx = A["attacker_X"] + dx * A["distance"]
    hy = A["attacker_Y"] + dy * A["distance"]
    A["altura"] = olho_z + dz * A["distance"] - A["victim_Z"]
    nh = np.sqrt(dx ** 2 + dy ** 2)
    rx, ry = hx - A["victim_X"], hy - A["victim_Y"]
    A["lado"] = (rx * dy - ry * dx) / nh
    A["fundo"] = (rx * dx + ry * dy) / nh
    A["inclinacao"] = np.degrees(np.arcsin(np.clip(dz, -1, 1)))
    ok = ((A["victim_duck_amount"].fillna(1) == 0) & (A["num_penetrations"] == 0)
          & (A["lado"].abs() < 30) & (A["fundo"].abs() < 30) & (A["inclinacao"].abs() < 20) & (A["distance"] > 64))
    return A[ok].copy()


def em_fronteiras(z, lab, c, sg, iters=150):
    """Log-verossimilhanca com fronteiras c (3 valores) e erro sg; densidade da altura por EM."""
    tb = np.arange(-5, 85, 0.5)
    lab_b = np.searchsorted(np.asarray(c), tb, side="right")         # parte de cada faixa de altura
    K = np.exp(-0.5 * ((z[:, None] - tb[None, :]) / sg) ** 2) / sg     # n x bins
    K = K * (lab_b[None, :] == lab[:, None])
    f = np.full(len(tb), 1 / len(tb))
    for _ in range(iters):
        num = K * f[None, :]
        den = num.sum(axis=1, keepdims=True) + 1e-300
        f = (num / den).mean(axis=0)
    return float(np.log((K * f[None, :]).sum(axis=1) + 1e-300).sum())


def ajustar(z, lab, c0):
    c = list(c0)
    sg = 3.5
    ll = em_fronteiras(z, lab, c, sg)
    for volta in range(3):
        passo = 0.5 if volta == 0 else 0.25
        for k in range(3):
            melhor = (ll, c[k])
            for v in np.arange(c[k] - 4 / (volta + 1), c[k] + 4 / (volta + 1) + 0.01, passo):
                cc = c.copy()
                cc[k] = v
                if not (cc[0] < cc[1] < cc[2]):
                    continue
                l = em_fronteiras(z, lab, cc, sg, iters=60)
                if l > melhor[0]:
                    melhor = (l, v)
            c[k] = float(melhor[1])
            ll = melhor[0]
        melhor = (ll, sg)
        for v in np.arange(1.5, 6.01, 0.25):
            l = em_fronteiras(z, lab, c, v, iters=60)
            if l > melhor[0]:
                melhor = (l, v)
        sg = float(melhor[1])
        ll = em_fronteiras(z, lab, c, sg)
    return c, sg


def probit_simples(z, y, c0):
    """Ponto de 50% de P(parte de cima | altura medida), sem tirar o borrao (logistica em grade).
    Devolve o ponto e a largura (com o fator 1,702 a largura e o desvio do borrao)."""
    cs = np.arange(c0 - 8, c0 + 8, 0.05)
    melhor, arg, arg_s = -np.inf, c0, 4.0
    for sg in np.exp(np.linspace(np.log(0.3), np.log(8), 40)):
        q = np.clip(1 / (1 + np.exp(-1.702 * (z[None, :] - cs[:, None]) / sg)), 1e-9, 1 - 1e-9)
        ll = (y[None, :] * np.log(q) + (1 - y[None, :]) * np.log(1 - q)).sum(axis=1)
        i = int(np.argmax(ll))
        if ll[i] > melhor:
            melhor, arg, arg_s = ll[i], float(cs[i]), float(sg)
    return arg, arg_s


JANELAS = ((0, (15, 45)), (1, (35, 56)), (2, (50, 68)))
FRONTEIRAS = ["pernas|barriga", "barriga|peito", "peito|cabeca"]
# janela (+-w) da inclinacao de cada fronteira: a de menor erro em simulacao com a fronteira conhecida
# (concorrentes_regioes.py janela, grade de 0,25 em 0,25 ate 30; conferida em sorteios separados com
# `validar`: erro 0,82 / 0,31 / 0,28 contra 0,93 / 0,41 / 0,43 com +-6). Na pernas|barriga o erro cai
# ate a janela encostar no pe (w = 30, o limite fisico: a fronteira fica a ~30 do chao).
JANELA_INCLINACAO = (30.0, 12.75, 19.25)


def probits(z, lab):
    """Probit de cada fronteira, so com as duas partes vizinhas dentro da janela de altura."""
    out = []
    for k, jan in JANELAS:
        m = ((lab == k) | (lab == k + 1)) & (z > jan[0]) & (z < jan[1])
        out.append(probit_simples(z[m], (lab[m] == k + 1).astype(float), float(np.median(z[m]))))
    return out


def inclinacao_log(z_todos, centro, w=6.0):
    """b = derivada do log da densidade de TODOS os tiros perto do centro: exponencial truncada em
    [centro-w, centro+w] por maxima verossimilhanca (media observada = media do modelo)."""
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


def corrigidas(z, lab, pr=None):
    """Fronteira = ponto de 50% + b * s^2 (Tweedie), b na janela de cada fronteira."""
    pr = pr or probits(z, lab)
    return [c + inclinacao_log(z, c, JANELA_INCLINACAO[k]) * s * s for k, (c, s) in enumerate(pr)]


def main():
    pasta, saida = sys.argv[1:3]
    B = ler(pasta)
    out = {"balas_em_pe": int(len(B)), "por_grupo": {}}
    print(f"\nbalas em pe, sem parede: {len(B)}")
    print(f"{'parte':10s} {'n':>5s} | altura medida acima do pe: 5% 25% 50% 75% 95%")
    for g in ["head", "neck", "chest", "stomach", "left_arm", "right_arm", "left_leg", "right_leg"]:
        s = B[B["hitgroup"] == g]
        q = s["altura"].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).round(1).tolist()
        out["por_grupo"][g] = {"n": int(len(s)), "altura_q05_25_50_75_95": q}
        print(f"{g:10s} {len(s):5d} | {q[0]:5.1f} {q[1]:5.1f} {q[2]:5.1f} {q[3]:5.1f} {q[4]:5.1f}")
    E = B[B["hitgroup"].isin(list(ROTULO)) & (B["lado"].abs() < 3.5)]
    z = E["altura"].to_numpy(float)
    lab = E["hitgroup"].map(ROTULO).to_numpy(int)
    # 1) probit simples de cada fronteira (borrado: puxa para o lado da parte com menos tiros)
    pr = probits(z, lab)
    simples = [c for c, _ in pr]
    out["fronteiras_probit"] = {n: round(v, 2) for n, v in zip(FRONTEIRAS, simples)}
    print(f"\nprobit simples: {out['fronteiras_probit']}")
    # 2) probit corrigido pela inclinacao da densidade (Tweedie): e o que o boneco usa
    tw = corrigidas(z, lab, pr)
    rng = np.random.default_rng(20261101)
    boot = np.array([corrigidas(z[ix], lab[ix]) for ix in (rng.integers(0, len(z), len(z)) for _ in range(200))])
    out["fronteiras_corrigidas"] = {}
    print("\nprobit corrigido (Tweedie), o que o boneco usa:")
    for k, nome in enumerate(FRONTEIRAS):
        b = inclinacao_log(z, pr[k][0], JANELA_INCLINACAO[k])
        ic = [round(float(q), 2) for q in np.quantile(boot[:, k], [0.025, 0.975])]
        out["fronteiras_corrigidas"][nome] = {"altura": round(tw[k], 2), "ic95": ic, "ponto_50": round(pr[k][0], 2),
                                              "borrao": round(pr[k][1], 2), "inclinacao_log": round(b, 4)}
        print(f"  {nome:16s} {tw[k]:6.2f}  (IC 95% {ic[0]} a {ic[1]}; ponto de 50% {pr[k][0]:.2f} + {b:+.4f} x {pr[k][1]:.2f}^2)")
    # 3) para comparar: maxima verossimilhanca com o borrao no modelo e densidade livre (EM)
    c, sg = ajustar(z, lab, simples)
    ll0 = em_fronteiras(z, lab, c, sg)
    out["erro_de_medida_altura"] = round(sg, 2)
    out["fronteiras_sem_borrao"] = {}
    print(f"\nperto do eixo do corpo: {len(z)} balas; erro de medida da altura {sg:.2f}")
    for k, nome in enumerate(["pernas|barriga", "barriga|peito", "peito|cabeca (no eixo, com a borda redonda da cabeca)"]):
        # IC 95% pela verossimilhanca perfilada (cai 1,92)
        dentro = []
        for v in np.arange(c[k] - 3, c[k] + 3.01, 0.25):
            cc = list(c)
            cc[k] = float(v)
            if not (cc[0] < cc[1] < cc[2]):
                continue
            if ll0 - em_fronteiras(z, lab, cc, sg) <= 1.92:
                dentro.append(float(v))
        ic = [round(min(dentro), 2), round(max(dentro), 2)] if dentro else [None, None]
        # se o IC encosta nas pontas da busca (+-3), a verossimilhanca e chata: a fronteira esta
        # mal determinada so com a altura (a densidade livre compensa); fica marcado
        fraca = bool(dentro) and (min(dentro) <= c[k] - 2.99 or max(dentro) >= c[k] + 2.99)
        out["fronteiras_sem_borrao"][nome.split(" ")[0]] = {"altura": round(c[k], 2), "ic95": ic, "ic_pelo_menos_3": fraca}
        print(f"  {nome:55s} {c[k]:6.2f}  (IC 95% {'pelo menos +-3' if fraca else f'{ic[0]} a {ic[1]}'})")
    cab = B[(B["hitgroup"] == "head") & (B["lado"].abs() < 3.5)]["altura"]
    out["cabeca_mediana_perto_do_eixo"] = round(float(cab.median()), 2)
    print(f"  mediana dos acertos de cabeca perto do eixo: {cab.median():.2f}")
    json.dump(out, open(saida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
