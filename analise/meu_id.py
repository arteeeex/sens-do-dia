"""Teu SteamID64, lido de fora do codigo (o repositorio e publico e nao leva o teu ID).

Ordem: variavel de ambiente SENS_STEAMID; senao o arquivo analise/meu_steamid.txt, que fica
fora do git. O numero e o de 17 digitos do link do teu perfil Steam (ou steamid.io).
"""
import os


def meu_steamid():
    v = os.environ.get("SENS_STEAMID", "").strip()
    if not v:
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meu_steamid.txt")
        if os.path.exists(caminho):
            v = open(caminho, encoding="utf-8").read().strip()
    if not (v.isdigit() and len(v) == 17):
        raise SystemExit("Falta o teu SteamID64: cria analise/meu_steamid.txt so com o numero de 17 digitos "
                         "(ou define a variavel de ambiente SENS_STEAMID).")
    return int(v)
