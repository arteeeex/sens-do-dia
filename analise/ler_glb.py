"""Le um .glb (glTF binario) e mostra malhas, nos, ossos e o tamanho de cada parte.

Uso: python ler_glb.py <arquivo.glb>
"""
import json
import struct
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TIPOS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
COMPS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def abrir(caminho):
    dados = open(caminho, "rb").read()
    magic, versao, total = struct.unpack_from("<III", dados, 0)
    assert magic == 0x46546C67, "nao e glb"
    off = 12
    js, binario = None, b""
    while off < total:
        tam, tipo = struct.unpack_from("<II", dados, off)
        corpo = dados[off + 8: off + 8 + tam]
        if tipo == 0x4E4F534A:
            js = json.loads(corpo.decode("utf-8"))
        elif tipo == 0x004E4942:
            binario = corpo
        off += 8 + tam
    return js, binario


def acessor(js, binario, i):
    a = js["accessors"][i]
    v = js["bufferViews"][a["bufferView"]]
    tipo = TIPOS[a["componentType"]]
    n = COMPS[a["type"]]
    ini = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    passo = v.get("byteStride", 0)
    tam_el = np.dtype(tipo).itemsize * n
    if passo and passo != tam_el:
        bruto = np.frombuffer(binario, dtype=np.uint8, count=passo * a["count"], offset=ini).reshape(a["count"], passo)
        arr = bruto[:, :tam_el].copy().view(tipo).reshape(a["count"], n)
    else:
        arr = np.frombuffer(binario, dtype=tipo, count=a["count"] * n, offset=ini).reshape(a["count"], n)
    if a.get("normalized"):
        arr = arr.astype(np.float32) / np.iinfo(tipo).max
    return arr


def main():
    js, binario = abrir(sys.argv[1])
    print("cena/nos:", len(js.get("nodes", [])), "| malhas:", len(js.get("meshes", [])), "| skins:", len(js.get("skins", [])),
          "| animacoes:", len(js.get("animations", [])))
    for i, m in enumerate(js.get("meshes", [])):
        for p in m["primitives"]:
            pos = acessor(js, binario, p["attributes"]["POSITION"])
            ntri = (js["accessors"][p["indices"]]["count"] // 3) if "indices" in p else len(pos) // 3
            print(f"malha {i} '{m.get('name')}': {len(pos)} vertices, {ntri} triangulos, atributos {list(p['attributes'])}, "
                  f"caixa min {np.round(pos.min(0), 1)} max {np.round(pos.max(0), 1)}")
    nomes = [n.get("name", "") for n in js.get("nodes", [])]
    print("\nprimeiros nos:", nomes[:80])
    for s in js.get("skins", []):
        print(f"\nskin com {len(s['joints'])} ossos; alguns: {[nomes[j] for j in s['joints'][:40]]}")


if __name__ == "__main__":
    main()
