"""Resumo dos duelos extraidos: o que tem nas tuas partidas."""
import json
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
pd.set_option("display.width", 220)

d = json.load(open(sys.argv[1], encoding="utf-8"))
df = pd.DataFrame(d["duelos"])
print("total:", len(df), "| por tipo:", df["tipo"].value_counts().to_dict())
ok = df[~df["sem_mira"] & ~df["luneta"] & ~df["franco"]].copy()
print("validos (sem faca/granada, sem luneta, sem AWP/scout):", len(ok), ok["tipo"].value_counts().to_dict())
q = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
for tipo, g in ok.groupby("tipo"):
    print(f"\n===== {tipo} (n={len(g)}) =====")
    for c in ["theta", "dist", "vel", "ttd_eu", "ttd_ele", "t_kill", "t_morte", "eu_vel"]:
        s = pd.to_numeric(g[c], errors="coerce").dropna()
        print(f"{c:8s} n={len(s):4d} quantis: {np.round(s.quantile(q).to_numpy(), 3)}")
    eu_pri = g["ttd_eu"].notna() & (g["ttd_ele"].isna() | (g["ttd_eu"] < g["ttd_ele"]))
    ele_pri = g["ttd_ele"].notna() & (g["ttd_eu"].isna() | (g["ttd_ele"] <= g["ttd_eu"]))
    print("primeiro dano: eu", int(eu_pri.sum()), "| ele", int(ele_pri.sum()), "| ninguem", int((~eu_pri & ~ele_pri).sum()))
    print("matei:", int(g["t_kill"].notna().sum()), "| morri:", int(g["t_morte"].notna().sum()))
    print("grupo do meu primeiro dano:", g["grupo_eu"].value_counts().to_dict())
bins = [0, 1, 2, 3, 5, 8, 12, 20, 35, 53, 90, 180]
print("\ntheta (graus) por faixa e tipo:\n", pd.crosstab(pd.cut(ok["theta"], bins), ok["tipo"]).to_string())
print("\nvelocidade angular do alvo (graus/s):\n",
      pd.cut(pd.to_numeric(ok["vel"], errors="coerce"), [0, 2, 5, 10, 20, 40, 80, 1e9]).value_counts().sort_index().to_string())
print("\npor mapa:", ok["mapa"].value_counts().to_dict())
