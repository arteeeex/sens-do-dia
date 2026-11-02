"""Monta o boneco do teste com as hitboxes oficiais do CS2 (agente FBI, physics_group_playerflesh).

As 35 pecas viram 16 formas: cabeca (esfera r 5), tronco de cima (peito) e de baixo (barriga),
braco, antebraco, coxa, canela e pe de cada lado, com os raios oficiais. O arquivo vem na pose
de referencia (em pe reto, bracos abertos); a postura do jogo sai das demos:
  - alturas medidas nos acertos de todo mundo (analise/medir_regioes.py, regioes.json):
    fim da barriga (pernas|barriga) e fronteira barriga|peito, contadas a partir do centro
    da cabeca. O tronco de baixo e a ponta de baixo do peito vao para essas alturas e as
    pernas encolhem na vertical (joelho dobrado) ate o quadril ficar no lugar medido;
  - cabeca na altura do olho em pe do jogo (63,6) menos 1,28 (medido nos teus tiros);
  - bracos segurando arma (cotovelo para baixo e para a frente, maos na frente do peito).
    Braco leva o mesmo dano do peito com colete (27), entao a posicao exata dele nao muda a conta.
Origem = centro da cabeca. Eixos: x para a frente do boneco, y para a esquerda dele, z para cima.

Grava app/boneco.js e duas imagens de conferencia (frente e lado).
Uso: python boneco.py <hitboxes_cs2.json> <regioes.json> <saida.js> <pasta_das_imagens>
"""
import json
import struct
import sys
import zlib

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OLHO_PE = 63.6
CABECA_ABAIXO_DO_OLHO = 1.28
CENTRO_CABECA_JOGO = OLHO_PE - CABECA_ABAIXO_DO_OLHO


def png(caminho, img):
    h, w = img.shape[:2]
    bruto = b"".join(b"\x00" + img[y].astype(np.uint8).tobytes() for y in range(h))
    def bloco(tipo, dados):
        c = struct.pack(">I", len(dados)) + tipo + dados
        return c + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    with open(caminho, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(bloco(b"IDAT", zlib.compress(bruto, 9)))
        f.write(bloco(b"IEND", b""))


def desenhar(capsulas, eixo_h, eixo_v, caminho, escala=6, margem=12):
    pts = np.array([c["a"] for c in capsulas] + [c["b"] for c in capsulas])
    rmax = max(c["r"] for c in capsulas)
    lo = pts.min(0) - rmax - 2
    hi = pts.max(0) + rmax + 2
    W = int((hi[eixo_h] - lo[eixo_h]) * escala) + 2 * margem
    H = int((hi[eixo_v] - lo[eixo_v]) * escala) + 2 * margem
    img = np.zeros((H, W, 3), dtype=np.float64) + np.array([22, 25, 31])
    ys, xs = np.mgrid[0:H, 0:W]
    ph = lo[eixo_h] + (xs - margem) / escala
    pv = hi[eixo_v] - (ys - margem) / escala
    for c in capsulas:
        a = np.array(c["a"])[[eixo_h, eixo_v]]
        b = np.array(c["b"])[[eixo_h, eixo_v]]
        ab = b - a
        t = np.clip(((ph - a[0]) * ab[0] + (pv - a[1]) * ab[1]) / max(1e-9, ab @ ab), 0, 1)
        dx = ph - (a[0] + t * ab[0])
        dy = pv - (a[1] + t * ab[1])
        d = np.sqrt(dx * dx + dy * dy)
        dentro = d <= c["r"]
        luz = 0.55 + 0.45 * np.sqrt(np.clip(1 - (d / c["r"]) ** 2, 0, 1))
        cor = np.array([214, 168, 128]) if c["nome"] != "cabeca" else np.array([232, 190, 150])
        img[dentro] = (cor[None, :] * luz[dentro][:, None])
    # linha do olho do jogo (63,6 acima do pe) para conferir a altura
    if eixo_v == 2:
        yolho = int(margem + (hi[2] - CABECA_ABAIXO_DO_OLHO) * escala)
        if 0 <= yolho < H:
            img[yolho, :, :] = [123, 211, 137]
    png(caminho, img)


def main():
    hb = json.load(open(sys.argv[1], encoding="utf-8"))
    rg = json.load(open(sys.argv[2], encoding="utf-8"))
    saida_js, pasta = sys.argv[3], sys.argv[4]
    # alturas medidas (relativas ao centro da cabeca = mediana dos acertos de cabeca no eixo)
    ref = rg["cabeca_mediana_perto_do_eixo"]
    fc = rg.get("fronteiras_corrigidas")
    if fc:
        # probit corrigido pela inclinacao da densidade dos tiros (Tweedie): ganhou do probit, do EM
        # e do meio a meio em simulacao com a fronteira conhecida (concorrentes_regioes.py, 01/11/2026).
        # barriga|peito so decide 3 ou 4 tiros a menos de ~16 m.
        base_barriga = fc["pernas|barriga"]["altura"] - ref
        juncao = fc["barriga|peito"]["altura"] - ref
    else:   # regioes.json de antes da terceira revisao
        fr = rg["fronteiras_sem_borrao"]
        base_barriga = fr["pernas|barriga"]["altura"] - ref
        simples = rg.get("fronteiras_probit", {}).get("barriga|peito", fr["barriga|peito"]["altura"])
        juncao = 0.5 * (simples + fr["barriga|peito"]["altura"]) - ref
    P = hb["pecas"]
    esferas = [p for p in P if abs(p["comprimento_total"] - 2 * p["raio"]) < 0.3]
    capsulas_ref = [p for p in P if p not in esferas]

    def esfera_perto(alvo, raio=None):
        cands = [s for s in esferas if raio is None or abs(s["raio"] - raio) < 0.2]
        return min(cands, key=lambda s: np.linalg.norm(np.array(s["centro"]) - np.array(alvo)))

    cabeca = max(esferas, key=lambda s: s["centro"][2])
    tronco = sorted([c for c in capsulas_ref if c["raio"] > 6], key=lambda c: -c["centro"][2])
    pontas = lambda c: (np.array(c["centro"]) - np.array(c["eixo"]) * (c["comprimento_total"] / 2 - c["raio"]),
                        np.array(c["centro"]) + np.array(c["eixo"]) * (c["comprimento_total"] / 2 - c["raio"]))
    juntas = {}
    for lado, s in (("e", 1), ("d", -1)):           # y > 0 = esquerda do boneco
        juntas["ombro_" + lado] = np.array(esfera_perto([-3.3, 7.2 * s, 61.7])["centro"])
        juntas["quadril_" + lado] = np.array(esfera_perto([-1.5, 4.2 * s, 35.2])["centro"])
        juntas["joelho_" + lado] = np.array(esfera_perto([-1.5, 4.7 * s, 23.0])["centro"])
        juntas["tornozelo_" + lado] = np.array(esfera_perto([-3.3, 4.95 * s, 3.85])["centro"])
        juntas["dedo_" + lado] = np.array(esfera_perto([4.6, 6.45 * s, 1.8])["centro"])
    r_braco = np.median([c["raio"] for c in capsulas_ref if 2.9 <= c["raio"] <= 3.1])
    r_antebraco = np.median([c["raio"] for c in capsulas_ref if 2.6 <= c["raio"] <= 2.8])
    r_perna = np.median([c["raio"] for c in capsulas_ref if 3.9 <= c["raio"] <= 4.1])
    r_pe = np.median([c["raio"] for c in capsulas_ref if 1.9 <= c["raio"] <= 2.1])

    # postura de arma: cotovelos para baixo e para a frente, maos na frente do peito
    def pose_braco(ombro, s):
        cotovelo = ombro + np.array([5.5, 2.5 * s, -9.0])
        if s > 0:   # braco esquerdo vai mais longe, segurando o cano
            mao = cotovelo + np.array([11.0, -6.5, 4.0])
        else:       # braco direito segura o cabo, perto do ombro
            mao = cotovelo + np.array([7.5, 3.5, 3.0])
        return cotovelo, mao

    formas = [{"nome": "cabeca", "a": cabeca["centro"], "b": cabeca["centro"], "r": round(cabeca["raio"] + 0.1, 2)}]
    for i, t in enumerate(tronco):
        a, b = pontas(t)
        formas.append({"nome": "tronco_cima" if i == 0 else "tronco_baixo", "a": a.tolist(), "b": b.tolist(), "r": t["raio"]})
    for lado, s in (("e", 1), ("d", -1)):
        ombro = juntas["ombro_" + lado]
        cot, mao = pose_braco(ombro, s)
        formas.append({"nome": "braco_" + lado, "a": ombro.tolist(), "b": cot.tolist(), "r": float(r_braco)})
        formas.append({"nome": "antebraco_" + lado, "a": cot.tolist(), "b": mao.tolist(), "r": float(r_antebraco)})
        formas.append({"nome": "coxa_" + lado, "a": juntas["quadril_" + lado].tolist(), "b": juntas["joelho_" + lado].tolist(), "r": float(r_perna)})
        formas.append({"nome": "canela_" + lado, "a": juntas["joelho_" + lado].tolist(), "b": juntas["tornozelo_" + lado].tolist(), "r": float(r_perna)})
        formas.append({"nome": "pe_" + lado, "a": juntas["tornozelo_" + lado].tolist(), "b": juntas["dedo_" + lado].tolist(), "r": float(r_pe)})

    # Postura do jogo pelas alturas medidas. Tudo relativo ao centro da cabeca (z = 0).
    z_cabeca = cabeca["centro"][2]
    c0 = np.array(cabeca["centro"])
    for f in formas:
        f["a"] = (np.array(f["a"], dtype=float) - c0)
        f["b"] = (np.array(f["b"], dtype=float) - c0)
    peito = next(f for f in formas if f["nome"] == "tronco_cima")
    barriga = next(f for f in formas if f["nome"] == "tronco_baixo")
    # peito: ponta de cima fica (ombros), ponta de baixo vai para a fronteira medida
    peito["a"][2] = juncao
    # barriga: de cima na fronteira, de baixo no fim medido da barriga (menos o raio)
    barriga["a"][2] = juncao
    barriga["b"][2] = base_barriga + barriga["r"]
    # pernas: quadril no lugar medido (mesma folga da pose de referencia entre o quadril e o fim
    # da barriga) e pe no chao, com o resto da perna encolhido na mesma proporcao
    z_quadril_ref = float(np.mean([juntas["quadril_e"][2], juntas["quadril_d"][2]])) - z_cabeca
    fim_barriga_ref = min(t["centro"][2] - t["comprimento_total"] / 2 for t in tronco) - z_cabeca
    z_quadril = base_barriga + (z_quadril_ref - fim_barriga_ref)
    chao_ref = min(min(f["a"][2], f["b"][2]) - f["r"] for f in formas if f["nome"].startswith("pe"))
    chao = -CENTRO_CABECA_JOGO
    fator_perna = (z_quadril - chao) / (z_quadril_ref - chao_ref)
    for f in formas:
        if f["nome"].startswith(("coxa", "canela", "pe")):
            for k in ("a", "b"):
                p = f[k]
                p[2] = z_quadril - (z_quadril_ref - p[2]) * fator_perna
    altura_cabeca = CENTRO_CABECA_JOGO
    for f in formas:
        f["a"] = np.round(f["a"], 2).tolist()
        f["b"] = np.round(f["b"], 2).tolist()
        f["r"] = round(float(f["r"]), 2)
    print(f"alturas medidas (do centro da cabeca): fim da barriga {base_barriga:+.2f}, barriga|peito {juncao:+.2f}; "
          f"quadril {z_quadril:+.2f}; perna encolhida para {100 * fator_perna:.0f}% na vertical")
    saida = {
        "fonte": "CS2, agents/models/ctm_fbi, physics_group_playerflesh (35 pecas), Source 2 Viewer 20.1; "
                 "postura pelas alturas medidas nos acertos das demos (regioes.json)",
        "cabeca_raio_oficial": cabeca["raio"],
        "altura_cabeca_sobre_o_pe": round(float(altura_cabeca), 2),
        "altura_cabeca_no_jogo": CENTRO_CABECA_JOGO,
        "balas_medidas": int(rg.get("balas_em_pe", 0)),
        "fim_da_barriga_sobre_o_pe": round(float(CENTRO_CABECA_JOGO + base_barriga), 2),
        "barriga_peito_sobre_o_pe": round(float(CENTRO_CABECA_JOGO + juncao), 2),
        "formas": formas,
    }
    with open(saida_js, "w", encoding="utf-8") as fjs:
        fjs.write("// Gerado por analise/boneco.py a partir das hitboxes do CS2. Nao editar a mao.\n")
        fjs.write("window.BONECO = ")
        json.dump(saida, fjs, ensure_ascii=False, separators=(",", ":"))
        fjs.write(";\n")
    desenhar(formas, 1, 2, pasta + "/boneco_frente.png")
    desenhar(formas, 0, 2, pasta + "/boneco_lado.png")
    print(json.dumps({k: v for k, v in saida.items() if k != "formas"}, ensure_ascii=False))
    for f in formas:
        print(f"{f['nome']:14s} r {f['r']:5.2f}  a {f['a']}  b {f['b']}")


if __name__ == "__main__":
    main()
