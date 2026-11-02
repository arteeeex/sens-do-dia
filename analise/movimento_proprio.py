"""Quanto do movimento do boneco vem do INIMIGO e quanto vem de TI (o teu corpo andando).

O caminho do boneco e o inimigo visto do teu olho, com os dois andando: o teu movimento de
teclado entra (a mira nao). No teste tu fica parado, entao a parte que vinha do teu corpo
aparece como se fosse o boneco andando. Aqui separa as duas, em cada duelo das demos:
  relativo (o que o app usa): olho dele - teu olho, os dois andando;
  so o inimigo: olho dele andando, o teu parado onde estava no comeco do duelo;
  so tu: o teu olho andando, o dele parado.
Mostra a velocidade na tela de cada um, a velocidade no chao de cada jogador (u/s) e quanto da
"energia" do movimento relativo (velocidade ao quadrado) e de cada lado.

Uso: python movimento_proprio.py <pasta_das_demos> <duelos.json> [saida.json]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import extrair_duelos as ex  # noqa: E402


def caminho(fonte_e, fonte_u, t0, n, passo, ang0):
    out = []
    for i in range(n):
        te, tu = fonte_e(t0 + i * passo), fonte_u(t0 + i * passo)
        v = te - tu
        ya, pa = ex.angulos_para(v[0], v[1], v[2])
        out.append([float(ex.wrap180(ya - ang0[0])), float(pa - ang0[1])])
    return np.array(out)


def main():
    pasta, duelos_p = sys.argv[1:3]
    saida = sys.argv[3] if len(sys.argv) > 3 else None
    bruto = json.load(open(duelos_p, encoding="utf-8"))
    d = pd.DataFrame(bruto["duelos"])
    d = d[~d["sem_mira"] & ~d["luneta"] & ~d["franco"]].reset_index(drop=True)
    arquivos = {x["id"]: x["arquivo"] for x in bruto["demos"]}
    eu = ex.EU
    V = {"relativo": [], "so o inimigo": [], "so tu": []}
    chao = {"inimigo": [], "tu": []}
    dif_traj = []
    energia = []          # por duelo: (|v_rel|^2, |v_ini|^2, |v_tu|^2) somados
    por_duelo = []
    for id_demo, arq in arquivos.items():
        sub = d[d["demo"] == id_demo]
        if not len(sub):
            continue
        mapa, nmax, J, hurt, morte, tiros, t_inicio = ex.carregar(os.path.join(pasta, arq))
        U = J.get(eu)
        if U is None:
            continue
        for r in sub.to_dict("records"):
            E = J.get(int(r["inimigo"]))
            n = len(r["traj"])
            if E is None or n < 3:
                continue
            t0 = int(r["t0"])
            o_u0, o_e0 = ex.olho(U, t0), ex.olho(E, t0)
            v0 = o_e0 - o_u0
            ang0 = ex.angulos_para(v0[0], v0[1], v0[2])
            rel = caminho(lambda t: ex.olho(E, t), lambda t: ex.olho(U, t), t0, n, ex.TRAJ_PASSO, ang0)
            ini = caminho(lambda t: ex.olho(E, t), lambda t: o_u0, t0, n, ex.TRAJ_PASSO, ang0)
            tu = caminho(lambda t: o_e0, lambda t: ex.olho(U, t), t0, n, ex.TRAJ_PASSO, ang0)
            dif_traj.append(float(np.max(np.abs(rel - np.array(r["traj"])))))
            hz = ex.TICK / ex.TRAJ_PASSO
            vr, vi, vt = (np.diff(c, axis=0) * hz for c in (rel, ini, tu))
            V["relativo"].append(np.hypot(*vr.T)); V["so o inimigo"].append(np.hypot(*vi.T)); V["so tu"].append(np.hypot(*vt.T))
            energia.append(((vr ** 2).sum(), (vi ** 2).sum(), (vt ** 2).sum()))
            ticks = np.arange(t0, t0 + n * ex.TRAJ_PASSO, ex.TRAJ_PASSO)
            ve = np.hypot(np.nan_to_num(E["velocity_X"][ticks]), np.nan_to_num(E["velocity_Y"][ticks]))
            vu = np.hypot(np.nan_to_num(U["velocity_X"][ticks]), np.nan_to_num(U["velocity_Y"][ticks]))
            chao["inimigo"].append(ve)
            chao["tu"].append(vu)
            # por duelo: velocidade media na tela ate o teu 1o dano (ou 0,5 s), e a tua velocidade no chao no teu 1o tiro nele
            fim = r["ttd_eu"] if r["ttd_eu"] is not None and np.isfinite(r["ttd_eu"]) else 0.5
            m = max(1, min(len(vr), int(round(min(fim, 2.5) * hz))))
            k_tiro = None if r["tiro_nele"] is None or not np.isfinite(r["tiro_nele"]) else min(len(vu) - 1, int(round(r["tiro_nele"] * hz)))
            por_duelo.append({"demo": int(id_demo), "t0": t0, "ttd_eu": r["ttd_eu"], "tiro_nele": r["tiro_nele"], "theta": r["theta"], "dist": r["dist"],
                              "tipo": r["tipo"], "v_rel": float(np.hypot(*vr[:m].T).mean()), "v_ini": float(np.hypot(*vi[:m].T).mean()),
                              "v_tu": float(np.hypot(*vt[:m].T).mean()), "chao_tu_no_tiro": None if k_tiro is None else float(vu[k_tiro]),
                              "chao_tu_inicio": float(vu[0]), "chao_ini_inicio": float(ve[0])})
        print(f"demo {id_demo}: {len(sub)} duelos", flush=True)
    q = lambda x: np.round(np.quantile(np.concatenate(x), [0.5, 0.9, 0.99]), 1).tolist()
    print(f"\nconferencia: o caminho refeito bate com o gravado (maior diferenca, graus): mediana {np.median(dif_traj):.4f}, max {np.max(dif_traj):.4f}")
    print("velocidade na tela (graus/s), mediana / 90% / 99%:")
    for k, v in V.items():
        print(f"  {k:14s} {q(v)}")
    print("velocidade no chao (u/s), mediana / 90% / 99%:")
    for k, v in chao.items():
        print(f"  {k:14s} {q(v)}")
    e = np.array(energia)
    tot = e[:, 0].sum()
    print(f"\nenergia do movimento relativo (soma de velocidade^2): vinda do inimigo {100 * e[:, 1].sum() / tot:.0f}%, "
          f"vinda de ti {100 * e[:, 2].sum() / tot:.0f}% (o resto e a soma/cancelamento dos dois: {100 * (1 - (e[:, 1].sum() + e[:, 2].sum()) / tot):+.0f}%)")
    frac_tu = e[:, 2] / np.maximum(e[:, 1] + e[:, 2], 1e-9)
    print(f"duelos em que mais da metade do movimento e teu: {100 * np.mean(frac_tu > 0.5):.0f}%")
    P = pd.DataFrame(por_duelo)
    tiro = P["chao_tu_no_tiro"].dropna()
    print(f"\ntua velocidade no chao no teu 1o tiro nele (u/s): mediana {tiro.median():.0f}, 90% {tiro.quantile(0.9):.0f}; "
          f"parado ou quase (< 85 u/s, tiro preciso no CS2): {100 * (tiro < 85).mean():.0f}% | no comeco do duelo: mediana {P['chao_tu_inicio'].median():.0f}")
    # o que deixa o duelo mais lento? ln(teu tempo ate o 1o dano) contra a velocidade de cada parte
    Q = P.dropna(subset=["ttd_eu"])
    Q = Q[(Q["ttd_eu"] > 0) & (Q["tipo"] == "frente")]
    X = np.column_stack([np.ones(len(Q)), np.log1p(Q["v_ini"]), np.log1p(Q["v_tu"]), np.log1p(Q["theta"]), np.log(Q["dist"])])
    y = np.log(Q["ttd_eu"].to_numpy(float))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    cov = np.linalg.inv(X.T @ X) * (res @ res) / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(cov))
    print(f"\nduelos de frente com o teu 1o dano: {len(Q)}. ln(teu tempo) = ... (efeito de dobrar a velocidade na tela, com angulo e distancia fixos)")
    for nome, i in (("velocidade do inimigo", 1), ("velocidade tua (teu corpo)", 2)):
        print(f"  {nome:28s} coef {beta[i]:+.3f} +- {se[i]:.3f}  (t = {beta[i] / se[i]:+.1f})")
    Xr = np.column_stack([np.ones(len(Q)), np.log1p(Q["v_rel"]), np.log1p(Q["theta"]), np.log(Q["dist"])])
    br, *_ = np.linalg.lstsq(Xr, y, rcond=None)
    r2 = lambda Xm, b: 1 - ((y - Xm @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    Xi = np.column_stack([np.ones(len(Q)), np.log1p(Q["v_ini"]), np.log1p(Q["theta"]), np.log(Q["dist"])])
    bi, *_ = np.linalg.lstsq(Xi, y, rcond=None)
    print(f"  quanto explica do teu tempo: so o inimigo R2 {r2(Xi, bi):.3f} | relativo (o que o app usa) R2 {r2(Xr, br):.3f} | os dois separados R2 {r2(X, beta):.3f}")
    if saida:
        json.dump({"tela": {k: q(v) for k, v in V.items()}, "chao": {k: q(v) for k, v in chao.items()},
                   "energia_inimigo": float(e[:, 1].sum() / tot), "energia_tu": float(e[:, 2].sum() / tot),
                   "coef_inimigo": [float(beta[1]), float(se[1])], "coef_tu": [float(beta[2]), float(se[2])]},
                  open(saida, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
