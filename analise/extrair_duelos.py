"""Extrai das demos do CS2 todos os duelos do usuario, com a situacao de mira de cada um.

Duelo = um inimigo entra no campo de visao do usuario (approximate_spotted_by) e, nos
2,5 s seguintes, alguem dos dois acerta o outro ou o usuario atira na direcao dele.

Para cada duelo grava: onde a mira estava em relacao a cabeca do inimigo no instante em
que ele apareceu, a distancia, como o alvo se moveu na tela (trajetoria angular, ja
somando o movimento do proprio usuario) e quanto tempo cada um levou para dar o
primeiro dano.

Uso: python extrair_duelos.py <pasta_das_demos> <saida.json>
"""
import glob
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I tira a pasta do script do caminho
from meu_id import meu_steamid  # noqa: E402

EU = meu_steamid()      # teu SteamID64, de analise/meu_steamid.txt (fora do git)
TICK = 64
OLHO_PE = 63.6          # medido nos tiros (fire_bullets): mediana 63.5 em pe
OLHO_QUEDA = 18.0       # agachado: mediana 45.5
JANELA = int(2.5 * TICK)
JUNTA_BURACO = 4        # ticks de "piscada" do spotted que ainda contam como o mesmo episodio
TRAJ_TICKS = JANELA     # caminho do alvo na janela inteira (2,5 s) enquanto os dois estao vivos
TRAJ_PASSO = 2          # grava a trajetoria a 32 Hz
MIRA_NA_DIRECAO = 4.0   # graus: tiro conta como "atirou nele" se passou a menos disso da cabeca
SEM_MIRA = ("knife", "bayonet", "grenade", "flashbang", "smoke", "molotov", "incgrenade",
            "decoy", "c4", "taser", "zeus", "karambit", "dagger", "butterfly", "falchion",
            "bowie", "huntsman", "navaja", "stiletto", "talon", "ursus", "kukri", "paracord",
            "survival", "nomad", "skeleton", "gut", "flip", "m9", "push", "classic", "css")

PROPS = ["X", "Y", "Z", "pitch", "yaw", "team_num", "is_alive", "approximate_spotted_by",
         "duck_amount", "active_weapon_name", "is_scoped", "velocity_X", "velocity_Y",
         "flash_duration"]


FRANCO = ("awp", "ssg", "scar-20", "scar20", "g3sg1")  # luneta: outra sens, fica fora


def sid(v):
    """SteamID64 sem passar por float (float perde os ultimos digitos)."""
    if v is None:
        return 0
    s = str(v).strip()
    if s in ("", "nan", "None", "<NA>"):
        return 0
    s = s.split(".")[0]
    return int(s) if s.isdigit() else 0


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def angulos_para(dx, dy, dz):
    """Yaw e pitch (convencao do Source: pitch positivo = olhando para baixo)."""
    yaw = np.degrees(np.arctan2(dy, dx))
    pitch = -np.degrees(np.arctan2(dz, np.hypot(dx, dy)))
    return yaw, pitch


def direcao(pitch, yaw):
    p, y = np.radians(pitch), np.radians(yaw)
    return np.stack([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), -np.sin(p)], axis=-1)


def sem_mira(arma):
    a = str(arma or "").lower()
    return a == "" or any(k in a for k in SEM_MIRA)


def carregar(caminho):
    p = DemoParser(caminho)
    mapa = p.parse_header().get("map_name", "?")
    df = p.parse_ticks(PROPS)
    df["steamid"] = df["steamid"].astype("int64")
    nmax = int(df["tick"].max()) + 1
    jogadores = {}
    for sid_j, g in df.groupby("steamid"):
        g = g.sort_values("tick")
        idx = g["tick"].to_numpy(dtype=np.int64)
        arr = {}
        for col in ["X", "Y", "Z", "pitch", "yaw", "team_num", "duck_amount", "velocity_X",
                    "velocity_Y", "flash_duration"]:
            a = np.full(nmax, np.nan)
            a[idx] = g[col].to_numpy(dtype=float)
            arr[col] = a
        vivo = np.zeros(nmax, dtype=bool)
        vivo[idx] = g["is_alive"].fillna(False).to_numpy(dtype=bool)
        arr["vivo"] = vivo
        esc = np.zeros(nmax, dtype=bool)
        esc[idx] = g["is_scoped"].fillna(False).to_numpy(dtype=bool)
        arr["mirando_luneta"] = esc
        arma = np.empty(nmax, dtype=object)
        arma[idx] = g["active_weapon_name"].to_numpy()
        arr["arma"] = arma
        vistos = np.empty(nmax, dtype=object)
        vistos[idx] = g["approximate_spotted_by"].to_numpy()
        arr["visto_por"] = vistos
        jogadores[int(sid_j)] = arr

    def evento(nome):
        try:
            e = p.parse_event(nome)
        except Exception:
            return pd.DataFrame()
        for c in ("attacker_steamid", "user_steamid"):
            if c in e.columns:
                e[c] = e[c].map(sid).astype("int64")
        return e

    hurt = evento("player_hurt")
    morte = evento("player_death")
    tiros = evento("fire_bullets")
    inicio_partida = evento("begin_new_match")
    congel = evento("round_freeze_end")
    t_inicio = 0
    if len(inicio_partida):
        t_inicio = int(inicio_partida["tick"].max())
    if len(congel):
        depois = congel[congel["tick"] >= t_inicio]["tick"]
        if len(depois):
            t_inicio = int(depois.min())
    return mapa, nmax, jogadores, hurt, morte, tiros, t_inicio


def olho(j, t):
    return np.array([j["X"][t], j["Y"][t], j["Z"][t] + OLHO_PE - OLHO_QUEDA * np.nan_to_num(j["duck_amount"][t])])


def episodios(mask):
    """Inicios e fins de trechos True, juntando buracos curtos."""
    t = np.flatnonzero(mask)
    if len(t) == 0:
        return []
    quebras = np.flatnonzero(np.diff(t) > JUNTA_BURACO + 1)
    inicios = np.concatenate([[t[0]], t[quebras + 1]])
    fins = np.concatenate([t[quebras], [t[-1]]])
    return list(zip(inicios.tolist(), fins.tolist()))


def montar(tipo, t0, t_fim, sid_e, E, U, nmax, hurt, morte, meus_tiros, id_demo, mapa, exigir_acao):
    """Monta um duelo a partir do instante t0 (em que a situacao de mira comecou)."""
    t1 = min(t0 + JANELA, nmax - 1)
    dano_eu = hurt[(hurt["attacker_steamid"] == EU) & (hurt["user_steamid"] == sid_e)
                   & (hurt["tick"] >= t0) & (hurt["tick"] <= t1)]
    dano_ele = hurt[(hurt["attacker_steamid"] == sid_e) & (hurt["user_steamid"] == EU)
                    & (hurt["tick"] >= t0) & (hurt["tick"] <= t1)]
    # primeiro tiro do usuario que passou perto da cabeca dele
    tiro_nele = None
    primeiro_tiro = None
    if len(meus_tiros):
        tj = meus_tiros[(meus_tiros["tick"] >= t0) & (meus_tiros["tick"] <= t1)]
        for _, r in tj.iterrows():
            t = int(r["tick"])
            v = olho(E, t) - np.array([r["origin_x"], r["origin_y"], r["origin_z"]])
            d = np.linalg.norm(v)
            if not np.isfinite(d) or d < 1:
                continue
            dirt = direcao(r["angles_x"], r["angles_y"])
            ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(dirt, v / d))))))
            if ang < MIRA_NA_DIRECAO:
                tiro_nele = t
                primeiro_tiro = r
                break
    if exigir_acao and not len(dano_eu) and not len(dano_ele) and tiro_nele is None:
        return None
    t_acao = min([x for x in [tiro_nele, int(dano_eu["tick"].min()) if len(dano_eu) else None] if x is not None],
                 default=t0)
    arma = U["arma"][t_acao] if U["arma"][t_acao] is not None else U["arma"][t0]
    luneta = bool(U["mirando_luneta"][t_acao])
    if primeiro_tiro is not None and pd.notna(primeiro_tiro.get("player_scoped")):
        luneta = luneta or bool(primeiro_tiro.get("player_scoped"))
    o = olho(U, t0)
    v = olho(E, t0) - o
    dist = float(np.linalg.norm(v))
    if not np.isfinite(dist) or dist < 16:
        return None
    yaw_alvo, pitch_alvo = angulos_para(v[0], v[1], v[2])
    dyaw = float(wrap180(yaw_alvo - U["yaw"][t0]))
    dpitch = float(pitch_alvo - U["pitch"][t0])
    mira = direcao(U["pitch"][t0], U["yaw"][t0])
    theta = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(mira, v / dist))))))
    # trajetoria do alvo na tela: movimento relativo, ja somando o do proprio usuario
    traj, dists = [], []
    for t in range(t0, min(t0 + TRAJ_TICKS, nmax - 1) + 1, TRAJ_PASSO):
        if not (E["vivo"][t] and U["vivo"][t]):
            break
        vv = olho(E, t) - olho(U, t)
        if not np.all(np.isfinite(vv)):
            break
        ya, pa = angulos_para(vv[0], vv[1], vv[2])
        traj.append([round(float(wrap180(ya - yaw_alvo)), 3), round(float(pa - pitch_alvo), 3)])
        dists.append(round(float(np.linalg.norm(vv)), 1))
    vel = None
    if len(traj) >= 3:
        tr = np.array(traj)
        n = min(len(tr), int(0.5 * TICK / TRAJ_PASSO) + 1)
        passos = np.hypot(np.diff(tr[:n, 0]), np.diff(tr[:n, 1]))
        vel = float(passos.sum() / ((n - 1) * TRAJ_PASSO / TICK))
    mortes_par = morte[(morte["tick"] >= t0) & (morte["tick"] <= t1)] if len(morte) else morte
    kill = mortes_par[(mortes_par["attacker_steamid"] == EU) & (mortes_par["user_steamid"] == sid_e)]
    morte_eu = mortes_par[(mortes_par["attacker_steamid"] == sid_e) & (mortes_par["user_steamid"] == EU)]
    primeiro_dano_eu = dano_eu.sort_values("tick").head(1)
    return {
        "tipo": tipo, "demo": id_demo, "mapa": mapa, "t0": int(t0),
        "visao_s": round((t_fim - t0) / TICK, 3) if t_fim is not None else None,
        "inimigo": str(sid_e),
        "dyaw": round(dyaw, 3), "dpitch": round(dpitch, 3), "theta": round(theta, 3),
        # altura da tua mira no inicio (pitch do Source: + = olhando para baixo). O teste poe a
        # camera nessa altura quando o alvo nasce, para nao acumular desvio de um alvo para o outro.
        "pitch_eu": round(float(U["pitch"][t0]), 2),
        "dist": round(dist, 1), "vel": None if vel is None else round(vel, 2),
        "traj": traj, "dists": dists,
        "ttd_eu": (int(dano_eu["tick"].min()) - t0) / TICK if len(dano_eu) else None,
        "ttd_ele": (int(dano_ele["tick"].min()) - t0) / TICK if len(dano_ele) else None,
        "grupo_eu": str(primeiro_dano_eu["hitgroup"].iloc[0]) if len(primeiro_dano_eu) else None,
        "tiro_nele": None if tiro_nele is None else (tiro_nele - t0) / TICK,
        "t_kill": (int(kill["tick"].min()) - t0) / TICK if len(kill) else None,
        "t_morte": (int(morte_eu["tick"].min()) - t0) / TICK if len(morte_eu) else None,
        "arma": str(arma), "luneta": luneta,
        "franco": any(k in str(arma).lower() for k in FRANCO),
        "agachado": round(float(np.nan_to_num(U["duck_amount"][t0])), 2),
        "eu_vel": round(float(np.hypot(np.nan_to_num(U["velocity_X"][t0]), np.nan_to_num(U["velocity_Y"][t0]))), 1),
        "flash": round(float(np.nan_to_num(U["flash_duration"][t0])), 2),
        "sem_mira": sem_mira(arma),
    }


def processar(caminho, id_demo):
    mapa, nmax, J, hurt, morte, tiros, t_inicio = carregar(caminho)
    if EU not in J:
        print(f"  usuario nao esta na demo {os.path.basename(caminho)}")
        return []
    U = J[EU]
    duelos = []
    meus_tiros = tiros[tiros["user_steamid"] == EU] if len(tiros) else tiros
    for sid_e, E in J.items():
        if sid_e == EU:
            continue
        visto = np.zeros(nmax, dtype=bool)
        for t in range(t_inicio, nmax):
            v = E["visto_por"][t]
            if v is not None and len(v) and EU in v:
                visto[t] = True
        inimigo = (E["team_num"] != U["team_num"]) & np.isfinite(E["team_num"]) & np.isfinite(U["team_num"])
        visto &= inimigo & E["vivo"] & U["vivo"]
        # 1) viradas: ele te acertou sem estar no teu campo de visao (o "visto" do CS2 so marca
        #    quem esta na tua frente). O duelo comeca no tiro dele.
        viradas = []
        golpes = hurt[(hurt["attacker_steamid"] == sid_e) & (hurt["user_steamid"] == EU)
                      & (hurt["tick"] >= t_inicio)].sort_values("tick")
        for t_h in golpes["tick"].astype(int):
            if not inimigo[t_h] or not U["vivo"][max(t_h - 1, 0)]:
                continue
            if visto[max(t_h - 16, 0):t_h + 1].any():
                continue
            if viradas and t_h - viradas[-1] < JANELA:
                continue
            viradas.append(t_h)
            d = montar("virada", t_h, None, sid_e, E, U, nmax, hurt, morte, meus_tiros, id_demo, mapa, False)
            if d is not None:
                duelos.append(d)
        # 2) duelos de frente: ele entrou no teu campo de visao
        for t0, t_fim in episodios(visto):
            if any(0 <= t0 - tv <= TICK for tv in viradas):
                continue  # continuacao de uma virada, ja contada
            d = montar("frente", t0, t_fim, sid_e, E, U, nmax, hurt, morte, meus_tiros, id_demo, mapa, True)
            if d is not None:
                duelos.append(d)
    return duelos


def main():
    pasta, saida = sys.argv[1], sys.argv[2]
    demos = sorted(glob.glob(os.path.join(pasta, "match730_*.dem")), key=os.path.getmtime)
    todos = []
    fontes = []
    for i, d in enumerate(demos):
        t = time.time()
        try:
            du = processar(d, i)
        except Exception as e:
            print(f"[{i}] {os.path.basename(d)} FALHOU: {e}")
            continue
        todos.extend(du)
        fontes.append({"id": i, "arquivo": os.path.basename(d),
                       "data": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(d))),
                       "duelos": len(du)})
        print(f"[{i}] {os.path.basename(d)}: {len(du)} duelos ({time.time() - t:.1f}s)")
    with open(saida, "w", encoding="utf-8") as f:
        json.dump({"usuario": str(EU), "demos": fontes, "duelos": todos}, f, ensure_ascii=False)
    print(f"total: {len(todos)} duelos em {len(fontes)} demos -> {saida}")


if __name__ == "__main__":
    main()
