// O teste de mira: camera com a conta do CS2, alvo replicando o duelo real, tiro da AK.
(function (global) {
  'use strict';

  const MYAW = 0.022;        // m_yaw e m_pitch padrao do CS2 (graus por contagem por unidade de sens)
  const TAN_V = 0.75;        // FOV vertical do CS2 = 73,74 graus em qualquer formato
  const CICLO_AK = 100;      // ms entre tiros da AK-47 (600 por minuto); um tiro por clique, sem recuo
  const ESPERA = 450;        // ms entre a kill e o proximo alvo
  const LIMITE = 2500;       // ms: mesma janela usada nos duelos das demos
  const RAD = Math.PI / 180;

  // Dano da AK-47 do CS2 (conferido em 449 acertos de AK das demos: a conta bate exata em 85%,
  // o resto e bala atravessando parede). dano = 36 x parte x 0,98^(distancia/500); com colete
  // (ou capacete, na cabeca) a vida perde 77,5% disso, arredondado para baixo. O boneco vem
  // de colete e capacete, como 84% dos inimigos nas tuas partidas.
  const AK = { dano: 36, queda: 0.98, passo: 500, protecao: 0.775, armadura: 0.5 };
  const PARTE = {
    cabeca: { mult: 4, prot: 'capacete', cod: 1 },
    peito: { mult: 1, prot: 'colete', cod: 2 },
    barriga: { mult: 1.25, prot: 'colete', cod: 3 },
    braco: { mult: 1, prot: 'colete', cod: 4 },
    perna: { mult: 0.75, prot: null, cod: 5 },
  };
  function parteDaForma(nome) {
    if (nome === 'cabeca') return 'cabeca';
    if (nome.startsWith('tronco_cima')) return 'peito';
    if (nome.startsWith('tronco_baixo')) return 'barriga';
    if (nome.startsWith('braco') || nome.startsWith('antebraco')) return 'braco';
    return 'perna';
  }
  function danoAK(parte, dist, b) {
    const P = PARTE[parte];
    const bruto = AK.dano * P.mult * Math.pow(AK.queda, dist / AK.passo);
    const protegido = b.colete > 0 && (P.prot === 'colete' || (P.prot === 'capacete' && b.capacete));
    if (!protegido) return { vida: Math.floor(bruto), colete: 0 };
    const vida = bruto * AK.protecao;
    let colete = Math.floor((bruto - vida) * AK.armadura);
    if (colete > b.colete) {   // colete acabou no meio do tiro: o que faltou vai para a vida
      return { vida: Math.floor(bruto - b.colete / AK.armadura), colete: b.colete };
    }
    return { vida: Math.floor(vida), colete };
  }

  let gl, hud, ctx, rend, perfil;
  let RADS = [5, 7.6, 5], ABAIXO = 1.28;
  let fmt = { id: 'nativo', aspecto: 16 / 9, esticado: false, barras: false };
  const cam = { yaw: 0, pitch: 0 };
  let sens = 0.5;
  let travado = false, rodando = false, pausado = false;
  let fila = [], resultados = [], atual = null, proxT = 0, aoFim = null;
  let rotulo = '', progresso = 0, canto = '', ultimoTiro = -1e9, semRaw = false;
  let bot = null, aoPausar = null, somCtx = null;
  let tamanhoCanvas = { w: 1, h: 1 };

  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cruz = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const wrap180 = (a) => ((((a + 180) % 360) + 360) % 360) - 180;
  const limita = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function frente(yaw, pitch) {
    const y = yaw * RAD, p = pitch * RAD;
    return [Math.cos(p) * Math.sin(y), -Math.sin(p), Math.cos(p) * Math.cos(y)];
  }
  function direita(yaw) {
    const y = yaw * RAD;
    return [Math.cos(y), 0, -Math.sin(y)];
  }

  function tanH() {
    return TAN_V * (fmt.esticado || fmt.barras ? fmt.aspecto : tamanhoCanvas.w / tamanhoCanvas.h);
  }

  // ---------- som ----------
  function som(tipo) {
    if (!somCtx) return;
    const t = somCtx.currentTime;
    const g = somCtx.createGain();
    g.connect(somCtx.destination);
    const o = somCtx.createOscillator();
    o.connect(g);
    if (tipo === 'kill') {
      o.type = 'sine';
      o.frequency.setValueAtTime(1700, t);
      o.frequency.exponentialRampToValueAtTime(950, t + 0.07);
      g.gain.setValueAtTime(0.16, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.09);
      o.start(t); o.stop(t + 0.1);
    } else if (tipo === 'erro') {
      o.type = 'square';
      o.frequency.setValueAtTime(260, t);
      g.gain.setValueAtTime(0.025, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.03);
      o.start(t); o.stop(t + 0.04);
    } else if (tipo === 'corpo') {
      o.type = 'triangle';
      o.frequency.setValueAtTime(620, t);
      o.frequency.exponentialRampToValueAtTime(380, t + 0.05);
      g.gain.setValueAtTime(0.12, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
      o.start(t); o.stop(t + 0.07);
    } else if (tipo === 'dano') {
      o.type = 'triangle';
      o.frequency.setValueAtTime(140, t);
      o.frequency.exponentialRampToValueAtTime(60, t + 0.14);
      g.gain.setValueAtTime(0.3, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
      o.start(t); o.stop(t + 0.17);
    }
  }

  // ---------- alvo ----------
  function nascer(ts) {
    const it = fila[0];
    const s = perfil.situacoes[it.sit];
    const m = it.espelho;
    // a mira vertical volta para a altura real daquele duelo (senao ela acumula desvio de um
    // alvo para o outro e, depois de centenas de alvos, o duelo acontece olhando para o ceu)
    if (s.pe != null) cam.pitch = limita(s.pe, -89, 89);
    const yaw0 = cam.yaw - m * s.dy;              // dy do Source: + = esquerda
    const pitch0 = limita(cam.pitch + s.dp, -85, 85);
    const v0 = [wrap180(yaw0 - cam.yaw), pitch0 - cam.pitch];
    atual = { it, s, m, yaw0, pitch0, t0: ts, tiros: 0, rt: null, over: false,
      v0, theta0: Math.hypot(v0[0], v0[1]), cam0: [cam.yaw, cam.pitch], am: [], xy: [],
      vida: 100, colete: 100, capacete: true, partes: [0, 0, 0, 0, 0, 0], flashAte: 0 };
    amostrar(atual, 0, true);
    if (s.v === 1) som('dano');
  }

  const r3 = (v) => Math.round(v * 1000) / 1000;

  // Erro da mira em relacao ao CENTRO da cabeca, em graus: ex > 0 = mira a direita,
  // ey > 0 = mira abaixo. ax/ay = meia-largura e meia-altura angulares da cabeca.
  function erroMira(a, tms) {
    const p = posAlvo(a, tms);
    const n = Math.hypot(p.c[0], p.c[1], p.c[2]);
    const yawC = Math.atan2(p.c[0], p.c[2]) / RAD;
    const pitchC = -Math.asin(p.c[1] / n) / RAD;
    return {
      ex: wrap180(cam.yaw - yawC), ey: cam.pitch - pitchC,
      ax: Math.atan(RADS[0] / n) / RAD, ay: Math.atan(RADS[1] / n) / RAD, p,
    };
  }

  // Uma amostra por quadro, no maximo uma a cada 6 ms (144 Hz grava todo quadro; 240 Hz, um sim
  // um nao: gravar tudo enchia o armazenamento do navegador numa sessao inteira). O instante
  // do tiro sempre entra. [ms desde o alvo aparecer, ex, ey, giro da camera em yaw e pitch]
  function amostrar(a, tms, forcar) {
    const e = erroMira(a, tms);
    const ult = a.am.length ? a.am[a.am.length - 1][0] : -1e9;
    if (forcar || tms - ult >= 6) {
      a.am.push([Math.round(tms * 10) / 10, r3(e.ex), r3(e.ey),
        r3(wrap180(cam.yaw - a.cam0[0])), r3(cam.pitch - a.cam0[1])]);
    }
    if (a.ax0 == null) { a.ax0 = r3(e.ax); a.ay0 = r3(e.ay); }
    return e;
  }

  function posAlvo(a, tms) {
    const s = a.s;
    let dyr = 0, dpr = 0, dist = s.d;
    if (s.tr.length) {
      const f = Math.max(0, (tms / 1000) * perfil.traj_hz);
      const i = Math.min(Math.floor(f), s.tr.length - 1);
      const j = Math.min(i + 1, s.tr.length - 1);
      const fr = limita(f - i, 0, 1);
      dyr = s.tr[i][0] + (s.tr[j][0] - s.tr[i][0]) * fr;
      dpr = s.tr[i][1] + (s.tr[j][1] - s.tr[i][1]) * fr;
      if (s.ds.length) {
        const k = Math.min(i, s.ds.length - 1), l = Math.min(j, s.ds.length - 1);
        dist = s.ds[k] + (s.ds[l] - s.ds[k]) * fr;
      }
    }
    const yaw = a.yaw0 - a.m * dyr;
    const pitch = limita(a.pitch0 + dpr, -88, 88);
    const d = frente(yaw, pitch);
    const c = [d[0] * dist, d[1] * dist - ABAIXO, d[2] * dist];
    return { c, yaw, pitch, dist };
  }

  // distancia ate a cabeca pelo raio (ou -1 se nao pega)
  function raioCabeca(c, dir) {
    const o = [-c[0] / RADS[0], -c[1] / RADS[1], -c[2] / RADS[2]];
    const d = [dir[0] / RADS[0], dir[1] / RADS[1], dir[2] / RADS[2]];
    const a = dot(d, d), b = dot(o, d), cc = dot(o, o) - 1;
    const h = b * b - a * cc;
    if (h < 0) return -1;
    return (-b - Math.sqrt(h)) / a;
  }
  function acertou(c, dir) { return raioCabeca(c, dir) > 0; }

  // mesma conta do shader: capsula de pa a pb com raio ra, raio saindo do olho (origem)
  function raioCapsula(rd, pa, pb, ra) {
    const ba = [pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]];
    const oa = [-pa[0], -pa[1], -pa[2]];
    const baba = dot(ba, ba), bard = dot(ba, rd), baoa = dot(ba, oa);
    if (baba < 1e-6) {
      const b0 = dot(rd, oa), c0 = dot(oa, oa) - ra * ra, h0 = b0 * b0 - c0;
      return h0 > 0 ? -b0 - Math.sqrt(h0) : -1;
    }
    const rdoa = dot(rd, oa), oaoa = dot(oa, oa);
    const a = baba - bard * bard;
    let b = baba * rdoa - baoa * bard;
    let c = baba * oaoa - baoa * baoa - ra * ra * baba;
    let h = b * b - a * c;
    if (h >= 0) {
      const t = (-b - Math.sqrt(h)) / a;
      const y = baoa + t * bard;
      if (y > 0 && y < baba) return t;
      const oc = y <= 0 ? oa : [-pb[0], -pb[1], -pb[2]];
      b = dot(rd, oc);
      c = dot(oc, oc) - ra * ra;
      h = b * b - c;
      if (h > 0) return -b - Math.sqrt(h);
    }
    return -1;
  }

  // Qual parte do boneco a bala pega primeiro (a mais perto pelo raio), ou null.
  // No tronco, peito ou barriga sai da ALTURA do acerto, com a fronteira medida nas demos
  // (as duas capsulas se cruzam e a de baixo e 0,04 mais grossa: pela capsula, tiro logo
  // abaixo da cabeca viraria barriga, o que nao bate com os acertos reais).
  let ultimoZ = null;   // altura do ultimo acerto em relacao ao centro da cabeca (para o registro)
  function tiroNoBoneco(c, dir) {
    let melhor = Infinity, parte = null;
    ultimoZ = null;
    const tc = raioCabeca(c, dir);
    if (tc > 0) { melhor = tc; parte = 'cabeca'; }
    if (FORMAS) {
      const b = montarBoneco(c);
      for (let i = 0; i < b.nc; i++) {
        const t = raioCapsula(dir, [b.ca[4 * i], b.ca[4 * i + 1], b.ca[4 * i + 2]],
          [b.cb[4 * i], b.cb[4 * i + 1], b.cb[4 * i + 2]], b.ca[4 * i + 3]);
        if (t > 0 && t < melhor) { melhor = t; parte = PARTES_FORMA[i]; }
      }
      if (parte === 'peito' || parte === 'barriga') {
        const zRel = dir[1] * melhor - c[1];        // altura do acerto em relacao ao centro da cabeca
        parte = zRel >= JUNCAO_PEITO ? 'peito' : 'barriga';
      }
    }
    if (parte) ultimoZ = Math.round((dir[1] * melhor - c[1]) * 10) / 10;
    return parte;
  }

  function registrar(t, timeout) {
    const a = atual;
    resultados.push({
      slot: a.it.slot == null ? -1 : a.it.slot, sit: a.it.sit, e: a.it.e, adapt: !!a.it.adapt,
      espelho: a.m, v: a.s.v, t, timeout, tiros: a.tiros, rt: a.rt, over: a.over,
      theta0: +a.theta0.toFixed(3), ax0: a.ax0, ay0: a.ay0,
      vida: a.vida,     // vida que sobrou (0 = morreu)
      hs: !timeout && a.partes[1] > 0,   // kill com tiro na cabeca
      partes: a.partes, // acertos: [nada, cabeca, peito, barriga, braco, perna]
      am: a.am,   // trajetoria da mira em relacao a cabeca (x, y) quadro a quadro
      xy: a.xy,   // cada tiro: [ms, ex, ey, cabeca, velocidade da mira em graus/s, ax, ay, parte, dano, altura do acerto]
    });
    fila.shift();
    atual = null;
  }

  function atirar(ts) {
    if (!rodando || pausado || !atual || ts < atual.t0) return;
    if (ts - ultimoTiro < CICLO_AK) return;
    ultimoTiro = ts;
    atual.tiros++;
    const tms = ts - atual.t0;
    const ultimo = atual.am[atual.am.length - 1];
    let vel = 0;
    if (ultimo && tms - ultimo[0] > 0.5) {
      const dy = wrap180(cam.yaw - atual.cam0[0]) - ultimo[3], dp = (cam.pitch - atual.cam0[1]) - ultimo[4];
      vel = Math.hypot(dy, dp) / ((tms - ultimo[0]) / 1000);
    } else if (atual.am.length >= 2) {
      const a1 = atual.am[atual.am.length - 2], a2 = atual.am[atual.am.length - 1];
      vel = Math.hypot(a2[3] - a1[3], a2[4] - a1[4]) / Math.max(1e-3, (a2[0] - a1[0]) / 1000);
    }
    // amostra no instante exato do tiro (senao a trajetoria acaba um quadro antes da kill)
    const e = amostrar(atual, tms, true);
    const p = e.p;
    const parte = tiroNoBoneco(p.c, frente(cam.yaw, cam.pitch));
    let dano = 0;
    if (parte) {
      const d = danoAK(parte, p.dist, atual);
      dano = d.vida;
      atual.vida -= d.vida;
      atual.colete = Math.max(0, atual.colete - d.colete);
      atual.partes[PARTE[parte].cod]++;
    } else {
      atual.partes[0]++;
    }
    atual.xy.push([Math.round(tms * 10) / 10, r3(e.ex), r3(e.ey), parte === 'cabeca' ? 1 : 0,
      Math.round(vel * 10) / 10, r3(e.ax), r3(e.ay), parte ? PARTE[parte].cod : 0, dano, ultimoZ]);
    if (parte && atual.vida <= 0) {
      atual.vida = 0;
      registrar((ts - atual.t0) / 1000, false);
      som('kill');
      proxT = ts + ESPERA;
      if (!fila.length) terminarBloco();
    } else if (parte) {
      som('corpo');
      atual.flashAte = ts + 70;
    } else {
      som('erro');
    }
  }

  function terminarBloco() {
    rodando = false;
    const cb = aoFim;
    aoFim = null;
    if (cb) cb(resultados.slice());
  }

  function invalidarAtual() {
    if (atual) {
      fila.push(fila.shift());   // a mesma situacao volta no fim do bloco
      atual = null;
    }
  }

  // ---------- quadro ----------
  function quadro(ts) {
    requestAnimationFrame(quadro);
    passo(ts);
  }

  function passo(ts) {
    const ativo = rodando && !pausado && (travado || bot);
    if (ativo) {
      if (bot) passoBot(ts);
      if (!atual && fila.length && ts >= proxT) nascer(ts);
      if (atual) {
        const tms = ts - atual.t0;
        if (tms > LIMITE) {
          registrar(LIMITE / 1000, true);
          proxT = ts + ESPERA;
          if (!fila.length) terminarBloco();
        } else {
          const p = amostrar(atual, tms).p;
          const v = [wrap180(p.yaw - cam.yaw), p.pitch - cam.pitch];
          const raioAng = Math.atan(RADS[0] / p.dist) / RAD;
          if (atual.theta0 > 3 * raioAng) {
            const proj = (v[0] * atual.v0[0] + v[1] * atual.v0[1]) / atual.theta0;
            if (proj < -raioAng) atual.over = true;
          }
        }
      }
    }
    desenhar(ts);
  }

  // Boneco com as hitboxes do CS2 (boneco.js): formas em coordenadas do proprio boneco
  // (origem no centro da cabeca, x para a frente, y para a esquerda, z para cima), viradas
  // para a camera. Sem boneco.js, cai num corpo simples.
  let FORMAS = null, ESFERA_LOCAL = null, PARTES_FORMA = [], JUNCAO_PEITO = -16.4;
  const CA = new Float32Array(64), CB = new Float32Array(64);
  function prepararBoneco() {
    const B = global.BONECO;
    if (!B || !B.formas) return;
    if (B.barriga_peito_sobre_o_pe != null && B.altura_cabeca_sobre_o_pe != null) {
      JUNCAO_PEITO = B.barriga_peito_sobre_o_pe - B.altura_cabeca_sobre_o_pe;
    }
    const cab = B.formas.find((f) => f.nome === 'cabeca');
    if (cab) RADS = [cab.r, cab.r, cab.r];
    FORMAS = B.formas.filter((f) => f.nome !== 'cabeca').slice(0, 16);
    PARTES_FORMA = FORMAS.map((f) => parteDaForma(f.nome));
    const pts = FORMAS.flatMap((f) => [f.a, f.b]);
    const c = [0, 1, 2].map((k) => pts.reduce((s, p) => s + p[k], 0) / pts.length);
    let r = 0;
    for (const f of FORMAS) for (const p of [f.a, f.b]) r = Math.max(r, Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]) + f.r);
    ESFERA_LOCAL = { c, r: r + 1 };
  }
  function montarBoneco(c) {
    if (!FORMAS) {
      const b0 = [c[0], c[1] - RADS[1] - 2.5, c[2]], b1 = [c[0], c[1] - 52, c[2]];
      CA.set([...b0, 10], 0); CB.set([...b1, 0], 0);
      return { c, rad: RADS, ca: CA, cb: CB, nc: 1, bs: [c[0], c[1] - 27, c[2], 40] };
    }
    const h = Math.hypot(c[0], c[2]) || 1;
    const f = [-c[0] / h, 0, -c[2] / h];          // frente do boneco: para a camera
    const up = [0, 1, 0];
    const esq = cruz(f, up);                       // esquerda dele (o mundo aqui e de mao esquerda)
    const mundo = (p) => [c[0] + p[0] * f[0] + p[1] * esq[0], c[1] + p[2], c[2] + p[0] * f[2] + p[1] * esq[2]];
    FORMAS.forEach((fm, i) => {
      const a = mundo(fm.a), b = mundo(fm.b);
      CA[4 * i] = a[0]; CA[4 * i + 1] = a[1]; CA[4 * i + 2] = a[2]; CA[4 * i + 3] = fm.r;
      CB[4 * i] = b[0]; CB[4 * i + 1] = b[1]; CB[4 * i + 2] = b[2]; CB[4 * i + 3] = 0;
    });
    const bc = mundo(ESFERA_LOCAL.c);
    return { c, rad: RADS, ca: CA, cb: CB, nc: FORMAS.length, bs: [bc[0], bc[1], bc[2], ESFERA_LOCAL.r] };
  }

  function desenhar(ts) {
    const f = frente(cam.yaw, cam.pitch);
    const r = direita(cam.yaw);
    const u = cruz(f, r);
    let alvo = null, pos = null;
    let flash = 0;
    if (atual && rodando) {
      pos = posAlvo(atual, ts - atual.t0);
      alvo = montarBoneco(pos.c);
      if (ts < atual.flashAte) flash = 0.35;   // acertou o corpo: pisca rapido, como o sangue no jogo
    }
    rend.desenhar({ f, r, u, tanH: tanH(), tanV: TAN_V, alvo, flash });
    desenharHud(ts, f, r, u, pos);
  }

  function desenharHud(ts, f, r, u, pos) {
    const W = hud.width, H = hud.height, dpr = global.devicePixelRatio || 1;
    ctx.clearRect(0, 0, W, H);
    const cx = W / 2, cy = H / 2;
    const sx = fmt.esticado ? (tamanhoCanvas.w / tamanhoCanvas.h) / fmt.aspecto : 1;
    // mira estilo CS (estatica)
    const len = 5 * dpr, gap = 3 * dpr, esp = 1.6 * dpr;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(sx, 1);
    ctx.fillStyle = 'rgba(0,0,0,0.85)';
    const barras = [[gap, -esp / 2, len, esp], [-gap - len, -esp / 2, len, esp], [-esp / 2, gap, esp, len], [-esp / 2, -gap - len, esp, len]];
    for (const b of barras) ctx.fillRect(b[0] - dpr, b[1] - dpr, b[2] + 2 * dpr, b[3] + 2 * dpr);
    ctx.fillStyle = '#4dff6a';
    for (const b of barras) ctx.fillRect(b[0], b[1], b[2], b[3]);
    ctx.restore();
    // seta para alvo fora da tela e indicador de dano
    if (pos && atual) {
      const d = frente(pos.yaw, pos.pitch);
      const xc = dot(d, r), yc = dot(d, u), zc = dot(d, f);
      const ang = Math.atan2(-yc, xc);
      const fora = zc <= 0 || Math.abs(xc / zc) > tanH() || Math.abs(yc / zc) > TAN_V;
      if (atual.s.v === 1 && ts - atual.t0 < 900) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.strokeStyle = 'rgba(235,60,50,0.85)';
        ctx.lineWidth = 7 * dpr;
        ctx.beginPath();
        ctx.arc(0, 0, 110 * dpr, ang - 0.32, ang + 0.32);
        ctx.stroke();
        ctx.restore();
      }
      if (fora) {
        const rx = W * 0.44, ry = H * 0.42;
        const px = cx + Math.cos(ang) * rx, py = cy + Math.sin(ang) * ry;
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(ang);
        ctx.fillStyle = 'rgba(255,210,80,0.95)';
        ctx.beginPath();
        ctx.moveTo(18 * dpr, 0);
        ctx.lineTo(-10 * dpr, -11 * dpr);
        ctx.lineTo(-10 * dpr, 11 * dpr);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
    }
    // rotulo e progresso
    if (rotulo) {
      ctx.font = `${13 * dpr}px system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillStyle = 'rgba(230,232,235,0.75)';
      ctx.fillText(rotulo, cx, 22 * dpr);
      const bw = 220 * dpr;
      ctx.fillStyle = 'rgba(255,255,255,0.12)';
      ctx.fillRect(cx - bw / 2, 30 * dpr, bw, 3 * dpr);
      ctx.fillStyle = 'rgba(123,211,137,0.9)';
      ctx.fillRect(cx - bw / 2, 30 * dpr, bw * limita(progresso, 0, 1), 3 * dpr);
    }
    // sens do bloco no canto de baixo
    if (canto && rodando) {
      ctx.font = `600 ${15 * dpr}px system-ui, sans-serif`;
      ctx.textAlign = 'left';
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      const tw = ctx.measureText(canto).width;
      ctx.fillRect(14 * dpr, H - 40 * dpr, tw + 20 * dpr, 28 * dpr);
      ctx.fillStyle = 'rgba(230,232,235,0.92)';
      ctx.fillText(canto, 24 * dpr, H - 20 * dpr);
    }
  }

  // ---------- entrada ----------
  function aoMover(e) {
    if (!travado || bot) return;
    const mx = e.movementX || 0, my = e.movementY || 0;
    if (!mx && !my) return;
    cam.yaw = wrap180(cam.yaw + mx * sens * MYAW);
    cam.pitch = limita(cam.pitch + my * sens * MYAW, -89, 89);
    if (atual && atual.rt == null && Math.abs(mx) + Math.abs(my) >= 2 && e.timeStamp >= atual.t0) {
      atual.rt = (e.timeStamp - atual.t0) / 1000;
    }
  }

  function aoClicar(e) {
    if (e.button !== 0 || !travado || bot) return;
    atirar(e.timeStamp);
  }

  function ajustarTamanho() {
    const dpr = global.devicePixelRatio || 1;
    const W = global.innerWidth, H = global.innerHeight;
    hud.width = Math.round(W * dpr);
    hud.height = Math.round(H * dpr);
    let cw = W;
    if (fmt.barras) cw = Math.min(W, H * fmt.aspecto);
    gl.style.width = cw + 'px';
    gl.style.height = H + 'px';
    gl.style.left = ((W - cw) / 2) + 'px';
    gl.width = Math.round(cw * dpr);
    gl.height = Math.round(H * dpr);
    tamanhoCanvas = { w: W, h: H };
  }

  async function travar() {
    if (!somCtx) {
      try { somCtx = new (global.AudioContext || global.webkitAudioContext)(); } catch (e) { somCtx = null; }
    }
    if (somCtx && somCtx.state === 'suspended') somCtx.resume();
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
    } catch (e) { /* segue sem tela cheia */ }
    if (bot) { travado = true; return; }
    try {
      const p = gl.requestPointerLock({ unadjustedMovement: true });
      if (p && typeof p.then === 'function') {
        await p.catch((err) => {
          if (err && err.name === 'NotSupportedError') {
            semRaw = true;   // navegador sem raw input: cai para o movimento do Windows
            return gl.requestPointerLock();
          }
          return null;
        });
      }
    } catch (e) {
      semRaw = true;
      try { gl.requestPointerLock(); } catch (e2) { /* sem trava */ }
    }
  }

  // ---------- bot (so para testar o app sem mouse) ----------
  // Imita uma mira humana: reacao, flick com perfil de jerk minimo e ganho que cresce com
  // a sens (sens alta passa do alvo, sens baixa fica curta), depois correcoes.
  const gaussiana = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
  const jerkMinimo = (t) => t * t * t * (10 - 15 * t + 6 * t * t);
  function passoBot(ts) {
    if (!atual) return;
    const tms = ts - atual.t0;
    if (!atual.bot) atual.bot = { rt: bot.reacao + 30 * gaussiana(), g: 1 + 0.15 * Math.log(sens / 0.5) + 0.07 * gaussiana() };
    const b = atual.bot;
    if (tms < b.rt) return;
    const p = posAlvo(atual, tms);
    const raioAng = Math.atan(RADS[0] / p.dist) / RAD;
    if (!b.ini) {
      const dy = wrap180(p.yaw - cam.yaw), dp = p.pitch - cam.pitch;
      b.ini = { y0: cam.yaw, p0: cam.pitch, dy: dy * b.g, dp: dp * b.g, t0: tms,
        D: 110 + 55 * Math.log2(1 + Math.hypot(dy, dp) / raioAng) };
      if (atual.rt == null) atual.rt = tms / 1000;
    }
    const fase = (tms - b.ini.t0) / b.ini.D;
    if (fase < 1) {
      const f = jerkMinimo(fase);
      cam.yaw = wrap180(b.ini.y0 + b.ini.dy * f);
      cam.pitch = limita(b.ini.p0 + b.ini.dp * f, -89, 89);
    } else {
      const dy = wrap180(p.yaw - cam.yaw), dp = p.pitch - cam.pitch;
      cam.yaw = wrap180(cam.yaw + dy * bot.ganho + bot.ruido * gaussiana() * 0.5);
      cam.pitch = limita(cam.pitch + dp * bot.ganho + bot.ruido * gaussiana() * 0.5, -89, 89);
    }
    const err = Math.hypot(wrap180(p.yaw - cam.yaw), p.pitch - cam.pitch);
    if (err < raioAng * bot.tolerancia) atirar(ts);
  }

  // ---------- API ----------
  global.Jogo = {
    iniciar(opts) {
      gl = opts.gl;
      hud = opts.hud;
      perfil = opts.perfil;
      aoPausar = opts.aoPausar;
      ctx = hud.getContext('2d');
      rend = global.Render.criar(gl);
      RADS = [perfil.cabeca.meia_largura, perfil.cabeca.meia_altura, perfil.cabeca.meia_largura];
      ABAIXO = perfil.cabeca.centro_abaixo_do_olho;
      prepararBoneco();   // hitbox oficial: cabeca = esfera de raio 5 (troca a medida pelos tiros)
      document.addEventListener('mousemove', aoMover);
      document.addEventListener('mousedown', aoClicar);
      document.addEventListener('pointerlockchange', () => {
        travado = document.pointerLockElement === gl;
        if (!travado && rodando && !bot) {
          invalidarAtual();
          pausado = true;
          if (aoPausar) aoPausar('trava');
        }
      });
      global.addEventListener('resize', ajustarTamanho);
      document.addEventListener('fullscreenchange', ajustarTamanho);
      ajustarTamanho();
      requestAnimationFrame(quadro);
    },
    formato(f) { fmt = f; ajustarTamanho(); },
    travar,
    rodarBloco(lista, opts, cb) {
      fila = lista.slice();
      resultados = [];
      atual = null;
      sens = opts.sens;
      rotulo = opts.rotulo || '';
      progresso = opts.progresso || 0;
      canto = opts.canto || '';
      aoFim = cb;
      pausado = false;
      rodando = true;
      ultimoTiro = -1e9;
      proxT = performance.now() + 700;
    },
    continuar() { pausado = false; proxT = performance.now() + 700; },
    parar() { rodando = false; atual = null; fila = []; aoFim = null; },
    estado() { return { travado, semRaw, rodando, pausado, restam: fila.length }; },
    ativarBot(b) { bot = Object.assign({ reacao: 200, ganho: 0.22, ruido: 0.05, tolerancia: 0.8 }, b || {}); travado = true; },
    camera: cam,
    // ganchos de teste: avancar um quadro com relogio proprio e conferir o desenho do alvo
    _passo: passo,
    // raio do olho na direcao do centro da cabeca deslocado `abaixo` unidades: que parte pega
    _raio(c, abaixo) {
      const alvo = [c[0], c[1] - abaixo, c[2]];
      const n = Math.hypot(...alvo);
      const dir = alvo.map((v) => v / n);
      const b = montarBoneco(c);
      const ts = [];
      for (let i = 0; i < b.nc; i++) {
        ts.push([FORMAS[i].nome, +raioCapsula(dir, [b.ca[4 * i], b.ca[4 * i + 1], b.ca[4 * i + 2]],
          [b.cb[4 * i], b.cb[4 * i + 1], b.cb[4 * i + 2]], b.ca[4 * i + 3]).toFixed(2)]);
      }
      return { parte: tiroNoBoneco(c, dir), cabeca: +raioCabeca(c, dir).toFixed(2), capsulas: ts.filter((x) => x[1] > 0) };
    },
    _sonda(ts) {
      if (!atual) return { alvo: false };
      const p = posAlvo(atual, ts - atual.t0);
      const f = frente(cam.yaw, cam.pitch), r = direita(cam.yaw), u = cruz(f, r);
      const d = [p.c[0] / Math.hypot(...p.c), p.c[1] / Math.hypot(...p.c), p.c[2] / Math.hypot(...p.c)];
      const zc = dot(d, f);
      if (zc <= 0) return { alvo: true, naTela: false };
      const nx = dot(d, r) / zc / tanH(), ny = dot(d, u) / zc / TAN_V;
      if (Math.abs(nx) > 1 || Math.abs(ny) > 1) return { alvo: true, naTela: false, nx, ny };
      desenhar(ts);
      const g = gl.getContext('webgl2');
      const px = Math.round((nx + 1) / 2 * gl.width), py = Math.round((ny + 1) / 2 * gl.height);
      const cor = new Uint8Array(4);
      g.readPixels(px, py, 1, 1, g.RGBA, g.UNSIGNED_BYTE, cor);
      const fundo = new Uint8Array(4);
      g.readPixels(Math.min(gl.width - 1, px + 60), py, 1, 1, g.RGBA, g.UNSIGNED_BYTE, fundo);
      // ponto do peito: 22 unidades abaixo do centro da cabeca
      const pe = [p.c[0], p.c[1] - 22, p.c[2]];
      const npe = Math.hypot(...pe);
      const dpe = [pe[0] / npe, pe[1] / npe, pe[2] / npe];
      const zpe = dot(dpe, f);
      let peito = null;
      if (zpe > 0) {
        const qx = Math.round(((dot(dpe, r) / zpe / tanH()) + 1) / 2 * gl.width);
        const qy = Math.round(((dot(dpe, u) / zpe / TAN_V) + 1) / 2 * gl.height);
        if (qx >= 0 && qx < gl.width && qy >= 0 && qy < gl.height) {
          const cp = new Uint8Array(4);
          g.readPixels(qx, qy, 1, 1, g.RGBA, g.UNSIGNED_BYTE, cp);
          peito = [...cp];
        }
      }
      return { alvo: true, naTela: true, px, py, cor: [...cor], peito, fundo: [...fundo], dist: p.dist,
        theta: Math.hypot(wrap180(p.yaw - cam.yaw), p.pitch - cam.pitch) };
    },
  };
})(window);
