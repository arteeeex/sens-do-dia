"""Qual caminho deixa o boneco na velocidade certa: o RELATIVO (inimigo visto do teu olho, os dois
andando; e o que o app usa) ou SO O INIMIGO (o teu olho parado onde estava no comeco do duelo)?

No teste tu fica parado. A parte do movimento na tela que vinha do teu corpo so deve estar no
boneco se ela pesava na MIRA nos duelos reais. O teu corpo andando pode atrasar o duelo por dois
motivos:
  (a) mira: o alvo anda na tela e a mao tem que compensar -> conta a parte DE LADO do teu
      movimento (a que gira o alvo na tela);
  (b) parar para atirar: no CS2 o tiro andando erra -> conta a velocidade no chao em QUALQUER
      direcao (de lado ou de frente/de costas igual).
Teste que separa os dois: ln(teu tempo ate o 1o dano) contra a tua velocidade de lado e a tua
velocidade de frente/costas (em u/s, a mesma unidade), com a velocidade do inimigo na tela, o
angulo e a distancia fixos. Se so (a), o "de lado" pesa e o "de frente" nao: fica o relativo. Se
(b), os dois pesam igual: o boneco deve andar so o que o inimigo andou.
Tambem compara qual caminho preve melhor o teu tempo fora da amostra (deixa-um-fora exato da
regressao, pareado duelo a duelo).

Uso: python velocidade_boneco.py <duelos_com_traj_ini.json> [saida.json]
"""
import json
import math
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HZ = 32


def media_vel(tr, m):
    tr = np.asarray(tr, float)
    return float(np.hypot(*(np.diff(tr[:m + 1], axis=0) * HZ).T).mean())


def ols(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    cov = XtXi * (res @ res) / (len(y) - X.shape[1])
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    loo = res / (1 - h)              # erro deixa-um-fora exato da regressao linear
    r2 = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    return b, cov, loo, r2


def main():
    bruto = json.load(open(sys.argv[1], encoding="utf-8"))
    saida = sys.argv[2] if len(sys.argv) > 2 else None
    d = pd.DataFrame(bruto["duelos"])
    d = d[~d["sem_mira"] & ~d["luneta"] & ~d["franco"]].reset_index(drop=True)
    linhas = []
    for r in d.to_dict("records"):
        t = r["ttd_eu"]
        tr, ti = r["traj"], r["traj_ini"]
        if t is None or not np.isfinite(t) or t <= 0 or len(tr) < 3 or len(ti) != len(tr):
            continue
        m = max(1, min(len(tr) - 1, int(round(min(t, 2.5) * HZ))))
        dr, di = np.asarray(r["dists"], float), np.asarray(r["dists_ini"], float)
        tu = np.asarray(tr, float) - np.asarray(ti, float)          # parte que veio do teu corpo (graus)
        v_tu = media_vel(tu, m)
        dist_med = float(np.mean(di[:m + 1]))
        lado = v_tu * math.pi / 180 * dist_med                        # teu movimento de lado (u/s)
        frente = float(np.abs(np.diff((dr - di)[:m + 1])).mean() * HZ)  # teu movimento de frente/costas (u/s)
        linhas.append({"tipo": r["tipo"], "t": t, "theta": r["theta"], "dist": r["dist"],
                       "v_rel": media_vel(tr, m), "v_ini": media_vel(ti, m), "v_tu": v_tu,
                       "lado": lado, "frente": frente, "eu_vel": r["eu_vel"]})
    P = pd.DataFrame(linhas)
    out = {}
    for nome, Q in (("de frente", P[P["tipo"] == "frente"]), ("todos", P)):
        y = np.log(Q["t"].to_numpy(float))
        base = [np.ones(len(Q)), np.log1p(Q["theta"]), np.log(Q["dist"])]
        if nome == "todos":
            base.append((Q["tipo"] == "virada").to_numpy(float))
        Xr = np.column_stack(base + [np.log1p(Q["v_rel"])])
        Xi = np.column_stack(base + [np.log1p(Q["v_ini"])])
        Xs = np.column_stack(base + [np.log1p(Q["v_ini"]), np.log1p(Q["lado"]), np.log1p(Q["frente"])])
        br, _, lr, r2r = ols(Xr, y)
        bi, _, li, r2i = ols(Xi, y)
        bs, cs, _, r2s = ols(Xs, y)
        dif = lr ** 2 - li ** 2                       # >0: o relativo erra mais fora da amostra
        z_dif = dif.mean() / (dif.std(ddof=1) / np.sqrt(len(dif)))
        k = Xs.shape[1]
        i_lado, i_frente = k - 2, k - 1
        dl = bs[i_lado] - bs[i_frente]
        se_dl = math.sqrt(cs[i_lado, i_lado] + cs[i_frente, i_frente] - 2 * cs[i_lado, i_frente])
        print(f"\n== duelos {nome}: {len(Q)} (com o teu 1o dano)")
        print(f"velocidade media na tela ate o teu 1o dano (graus/s), mediana: relativo {Q['v_rel'].median():.1f} | "
              f"so o inimigo {Q['v_ini'].median():.1f} | so o teu corpo {Q['v_tu'].median():.1f}")
        print(f"teu corpo (u/s), mediana: de lado {Q['lado'].median():.0f} | de frente/costas {Q['frente'].median():.0f}")
        print(f"preve o teu tempo (R2 na amostra): relativo {r2r:.4f} | so o inimigo {r2i:.4f} | separado {r2s:.4f}")
        print(f"erro fora da amostra (deixa-um-fora, ln t ao quadrado): relativo {np.mean(lr ** 2):.5f} | so o inimigo {np.mean(li ** 2):.5f} "
              f"| diferenca {dif.mean():+.5f} (z = {z_dif:+.2f}; negativo = relativo preve melhor)")
        for nome_c, i in (("inimigo na tela", k - 3), ("teu corpo de lado", i_lado), ("teu corpo de frente/costas", i_frente)):
            print(f"  ln(tempo) por ln(1+vel) {nome_c:28s} {bs[i]:+.3f} +- {math.sqrt(cs[i, i]):.3f} (t = {bs[i] / math.sqrt(cs[i, i]):+.2f})")
        print(f"  de lado - de frente: {dl:+.3f} +- {se_dl:.3f} (z = {dl / se_dl:+.2f}; positivo = o que pesa e o alvo andando na tela)")
        out[nome] = {"n": int(len(Q)), "r2_relativo": r2r, "r2_inimigo": r2i, "r2_separado": r2s,
                     "loo_relativo": float(np.mean(lr ** 2)), "loo_inimigo": float(np.mean(li ** 2)),
                     "loo_dif": float(dif.mean()), "loo_z": float(z_dif),
                     "coef_inimigo": [float(bs[k - 3]), math.sqrt(cs[k - 3, k - 3])],
                     "coef_lado": [float(bs[i_lado]), math.sqrt(cs[i_lado, i_lado])],
                     "coef_frente": [float(bs[i_frente]), math.sqrt(cs[i_frente, i_frente])],
                     "lado_menos_frente": [dl, se_dl],
                     "tela_mediana": {"relativo": float(Q["v_rel"].median()), "inimigo": float(Q["v_ini"].median()),
                                      "corpo": float(Q["v_tu"].median())}}
    if saida:
        json.dump(out, open(saida, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
