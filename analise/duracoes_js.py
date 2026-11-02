"""Escreve o bloco DURACOES do app/js/app.js a partir dos desenhos escolhidos (sem copiar numero a mao).

Uso: python duracoes_js.py 8=otimo_livre_8_gfixo.json 11.8=... 16=... 20=... 25=... 35=...
"""
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
NOMES = {"8": ("8", "8 minutos"), "11.8": ("12", "12 minutos (padrão)"), "16": ("16", "16 minutos"),
         "20": ("20", "20 minutos"), "25": ("25", "25 minutos"), "35": ("35", "35 minutos (máximo)")}


def main():
    linhas = ["  const DURACOES = {"]
    perdas = []
    for arg in sys.argv[1:]:
        dur, arq = arg.split("=", 1)
        dado = json.load(open(os.path.join(BASE, arq), encoding="utf-8"))
        p = dado["desenho"]
        chave, nome = NOMES[dur]
        num = lambda v, d=5: f"{v:.{d}f}".rstrip("0").rstrip(".")
        ws = ", ".join(f"Math.log({num(math.exp(w))})" for w in p["Ws"])
        ks = ", ".join(num(k) for k in p["ks"])
        linhas.append(f"    '{chave}': {{ nome: '{nome}', Ws: [{ws}],")
        linhas.append(f"      ks: [{ks}], gama: {num(p['gam'])}, gl0: {int(p.get('gl0', 16))},")
        linhas.append(f"      duelosPorRodada: [{', '.join(str(int(n)) for n in p['n'])}], adapt: {int(p.get('adapt', 1))}, aquec: {int(p.get('aquec', 0))} }},")
        perdas.append(f"{chave} min {dado['perda']:.4f}%")
    linhas.append("  };")
    print("  // Perda media (300 mil dias novos, ruido incerto, com custo de troca de sens e aquecimento): " + ", ".join(perdas))
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
