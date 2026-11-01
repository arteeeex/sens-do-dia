"""Revisao das situacoes e dos pesos com as demos.

1) Dois inimigos ao mesmo tempo: duelos com outro duelo (inimigo diferente) comecando a
   menos de 1 s, na mesma demo.
2) Peso por situacao com Kaplan-Meier PROPRIO de cada situacao (o tempo do inimigo muda
   com a situacao) contra o Kaplan-Meier agrupado por tipo que o app usa hoje.
3) Mistura de armas e distancia por situacao (para ver se falta algum tipo).

Uso: python revisar_situacoes.py <duelos.json>
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perfil import ESTRATOS, JANELA, densidade, estrato, kaplan_meier  # noqa: E402


def main():
    bruto = json.load(open(sys.argv[1], encoding="utf-8"))
    df = pd.DataFrame(bruto["duelos"])
    df = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].reset_index(drop=True)
    df["estrato"] = [estrato(r) for r in df.to_dict("records")]

    # 1) dois ao mesmo tempo
    multi = np.zeros(len(df), dtype=bool)
    for d, g in df.groupby("demo"):
        t = g["t0"].to_numpy()
        e = g["inimigo"].to_numpy()
        for i, idx in enumerate(g.index):
            multi[idx] = bool(np.any((np.abs(t - t[i]) < 64) & (e != e[i])))
    df["multi"] = multi
    print(f"1) duelos com outro inimigo a menos de 1 s: {multi.mean() * 100:.1f}% ({multi.sum()} de {len(df)})")
    kills = df[df["t_kill"].notna()]
    print(f"   entre as kills: {kills['multi'].mean() * 100:.1f}%")

    # 2) Kaplan-Meier do inimigo por situacao contra agrupado
    def evento(r):
        if r["tipo"] == "frente":
            if pd.notna(r["ttd_ele"]):
                return r["ttd_ele"], 1
            fim = JANELA
            if pd.notna(r["t_kill"]):
                fim = min(fim, r["t_kill"])
            if pd.notna(r["visao_s"]):
                fim = min(fim, r["visao_s"] + 0.25)
            return fim, 0
        if pd.notna(r["t_morte"]):
            return r["t_morte"], 1
        return (JANELA if pd.isna(r["t_kill"]) else min(JANELA, r["t_kill"])), 0

    ev = [evento(r) for r in df.to_dict("records")]
    df["t_ini"] = [e[0] for e in ev]
    df["ev_ini"] = [e[1] for e in ev]
    df["t_eu"] = [r["ttd_eu"] if pd.notna(r["ttd_eu"]) else (max(r["tiro_nele"], 1 / 64) if pd.notna(r["tiro_nele"]) else np.nan)
                  for r in df.to_dict("records")]

    def dens_de(g):
        st, sj, _ = kaplan_meier(g["t_ini"].to_numpy(float), g["ev_ini"].to_numpy(int))
        tt = g.loc[g["ev_ini"] == 1, "t_ini"].to_numpy(float)
        banda = max(0.03, 1.06 * np.std(tt) * len(tt) ** (-1 / 5)) if len(tt) > 5 else 0.15
        return densidade(st, sj, banda)

    def valores(df_, por):
        dens = {}
        for chave, g in df_.groupby(por):
            dens[chave if isinstance(chave, tuple) else (chave,)] = dens_de(g)
        v = []
        for r in df_.to_dict("records"):
            t = r["t_eu"] if np.isfinite(r["t_eu"]) else r["t_ini"]
            chave = tuple(r[c] for c in por)
            v.append(float(dens[chave](max(float(t), 1 / 64))[0]) * max(float(t), 1 / 64))
        return np.array(v)

    v_tipo = valores(df, ["tipo"])
    v_estr = valores(df, ["estrato", "tipo"])
    rng = np.random.default_rng(4)
    print("\n2) peso por situacao: Kaplan-Meier agrupado por tipo (app hoje) x proprio de cada situacao")
    print(f"{'situacao':18s} {'n':>4s} {'aparece':>8s} {'agrupado':>9s} {'proprio':>8s} {'IC 95% do proprio':>18s}")
    ids = df["estrato"].to_numpy()
    boot = []
    for _ in range(1000):
        k = rng.integers(0, len(df), len(df))
        sub = df.iloc[k].reset_index(drop=True)
        vv = valores(sub, ["estrato", "tipo"])
        boot.append([vv[sub["estrato"].to_numpy() == e["id"]].sum() / vv.sum() for e in ESTRATOS])
    boot = np.array(boot)
    for i, e in enumerate(ESTRATOS):
        m = ids == e["id"]
        print(f"{e['nome']:18s} {m.sum():4d} {100 * m.mean():7.1f}% {100 * v_tipo[m].sum() / v_tipo.sum():8.1f}% "
              f"{100 * v_estr[m].sum() / v_estr.sum():7.1f}% {100 * np.quantile(boot[:, i], 0.025):8.1f}-{100 * np.quantile(boot[:, i], 0.975):5.1f}%")

    # 3) armas e distancia
    print("\n3) arma mais comum e distancia mediana por situacao")
    for e in ESTRATOS:
        g = df[df["estrato"] == e["id"]]
        print(f"{e['nome']:18s} dist {g['dist'].median():6.0f} u | {g['arma'].value_counts(normalize=True).head(3).round(2).to_dict()}")


if __name__ == "__main__":
    main()
