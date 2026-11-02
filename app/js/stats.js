// Matematica da sens do dia. Tudo com os dados do dia; nada vem de sessoes antigas.
//
// Nota de cada sens:   S(x) = soma_h  W_h * media_{situacoes da faixa h} ln(tempo)
//   x = ln(sens / tua sens), W_h = peso da situacao h (medido nas tuas demos),
//   tempo = segundos ate matar, limitado entre 0,05 s e 2,5 s (janela do duelo).
// Curva: quadratica em x por minimos quadrados ponderados (peso = 1 / variancia de S).
// Sens do dia: o minimo da curva dentro da faixa testada.
// Incerteza: bootstrap em dois estagios (sorteia situacoes dentro de cada faixa e blocos
// dentro de cada sens), 2000 repeticoes, intervalo de 95% por percentil.
(function (global) {
  'use strict';

  const T_MIN = 0.05;
  const T_MAX = 2.5;

  function rng(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function solve3(A, b) {
    const M = A.map((r, i) => r.concat([b[i]]));
    for (let c = 0; c < 3; c++) {
      let p = c;
      for (let r = c + 1; r < 3; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      if (Math.abs(M[p][c]) < 1e-12) return null;
      const tmp = M[c]; M[c] = M[p]; M[p] = tmp;
      for (let r = 0; r < 3; r++) {
        if (r === c) continue;
        const f = M[r][c] / M[c][c];
        for (let k = c; k < 4; k++) M[r][k] -= f * M[c][k];
      }
    }
    return [M[0][3] / M[0][0], M[1][3] / M[1][1], M[2][3] / M[2][2]];
  }

  function ajusteQuad(xs, ys, ws) {
    const S = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    const v = [0, 0, 0];
    for (let i = 0; i < xs.length; i++) {
      if (!isFinite(ys[i])) continue;
      const f = [1, xs[i], xs[i] * xs[i]];
      for (let a = 0; a < 3; a++) {
        v[a] += ws[i] * f[a] * ys[i];
        for (let b = 0; b < 3; b++) S[a][b] += ws[i] * f[a] * f[b];
      }
    }
    return solve3(S, v);
  }

  function ajusteLinear(xs, ys, ws) {
    let sw = 0, sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (let i = 0; i < xs.length; i++) {
      if (!isFinite(ys[i])) continue;
      const w = ws[i];
      sw += w; sx += w * xs[i]; sy += w * ys[i];
      sxx += w * xs[i] * xs[i]; sxy += w * xs[i] * ys[i];
    }
    const d = sw * sxx - sx * sx;
    if (Math.abs(d) < 1e-12) return [sy / (sw || 1), 0];
    const b1 = (sw * sxy - sx * sy) / d;
    return [(sy - b1 * sx) / sw, b1];
  }

  const curva = (b, x) => b[0] + b[1] * x + b[2] * x * x;

  function minimoNoIntervalo(b, lo, hi) {
    let melhor = curva(b, lo) <= curva(b, hi) ? lo : hi;
    if (b[2] > 1e-9) {
      const xv = -b[1] / (2 * b[2]);
      if (xv > lo && xv < hi && curva(b, xv) < curva(b, melhor)) melhor = xv;
    }
    return melhor;
  }

  function quantil(arr, p) {
    const a = arr.filter(isFinite).sort((x, y) => x - y);
    if (!a.length) return NaN;
    const i = (a.length - 1) * p;
    const lo = Math.floor(i), hi = Math.ceil(i);
    return a[lo] + (a[hi] - a[lo]) * (i - lo);
  }

  function media(a) {
    const b = a.filter(isFinite);
    return b.length ? b.reduce((s, v) => s + v, 0) / b.length : NaN;
  }

  function variancia(a) {
    const b = a.filter(isFinite);
    if (b.length < 2) return NaN;
    const m = media(b);
    return b.reduce((s, v) => s + (v - m) * (v - m), 0) / (b.length - 1);
  }

  function gammaln(x) {
    const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
      -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6,
      1.5056327351493116e-7];
    if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * x)) - gammaln(1 - x);
    x -= 1;
    let a = c[0];
    const t = x + 7.5;
    for (let i = 1; i < 9; i++) a += c[i] / (x + i);
    return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
  }

  function gammaP(a, x) {
    if (x <= 0) return 0;
    if (x < a + 1) {
      let s = 1 / a, termo = s;
      for (let n = 1; n < 1000; n++) {
        termo *= x / (a + n);
        s += termo;
        if (Math.abs(termo) < Math.abs(s) * 1e-15) break;
      }
      return s * Math.exp(-x + a * Math.log(x) - gammaln(a));
    }
    let b = x + 1 - a, c = 1e300, d = 1 / b, h = d;
    for (let i = 1; i < 1000; i++) {
      const an = -i * (i - a);
      b += 2;
      d = an * d + b; if (Math.abs(d) < 1e-300) d = 1e-300;
      c = b + an / c; if (Math.abs(c) < 1e-300) c = 1e-300;
      d = 1 / d;
      const del = d * c;
      h *= del;
      if (Math.abs(del - 1) < 1e-15) break;
    }
    return 1 - Math.exp(-x + a * Math.log(x) - gammaln(a)) * h;
  }

  const chi2p = (x, k) => (k > 0 ? 1 - gammaP(k / 2, x / 2) : NaN);

  const tempoLimitado = (t) => Math.min(T_MAX, Math.max(T_MIN, t));

  // Agrupa os blocos medidos por sens (x) e guarda ln(tempo) por situacao do deck.
  function preparar(sessao) {
    const grupos = new Map();
    for (const bl of sessao.blocos) {
      if (bl.tipo !== 'medida' || !bl.feito) continue;
      const k = bl.x.toFixed(4);
      if (!grupos.has(k)) grupos.set(k, { x: bl.x, blocos: [] });
      const ys = new Map();
      for (const d of bl.duelos) {
        if (d.adapt || d.slot < 0 || d.invalido || d.t == null) continue;
        ys.set(d.slot, Math.log(tempoLimitado(d.t)));
      }
      grupos.get(k).blocos.push(ys);
    }
    const G = [...grupos.values()].sort((a, b) => a.x - b.x);
    const estratos = {};
    sessao.deck.forEach((s, slot) => { (estratos[s.e] = estratos[s.e] || []).push(slot); });
    return { G, estratos };
  }

  // Nota S de cada sens + media por faixa, para uma escolha de situacoes e de blocos.
  function notas(G, amostra, escolha, pesos) {
    const S = [];
    const porFaixa = {};
    for (const e of Object.keys(amostra)) porFaixa[e] = [];
    G.forEach((g, gi) => {
      const blocos = escolha ? escolha[gi].map((i) => g.blocos[i]) : g.blocos;
      let soma = 0, somaW = 0;
      for (const [e, slots] of Object.entries(amostra)) {
        let s = 0, n = 0;
        for (const slot of slots) {
          let sy = 0, ny = 0;
          for (const b of blocos) {
            const y = b.get(slot);
            if (y !== undefined) { sy += y; ny++; }
          }
          if (ny) { s += sy / ny; n++; }
        }
        const m = n ? s / n : NaN;
        porFaixa[e].push(m);
        const W = pesos[e] || 0;
        if (n && W > 0) { soma += W * m; somaW += W; }
      }
      S.push(somaW ? soma / somaW : NaN);
    });
    return { S, porFaixa };
  }

  function analisar(sessao, pesos, opts) {
    opts = opts || {};
    const B = opts.B || 2000;
    const { G, estratos } = preparar(sessao);
    if (G.length < 3) return { erro: 'Precisa de pelo menos 3 sens medidas.' };
    const xs = G.map((g) => g.x);
    const lo = Math.min(...xs), hi = Math.max(...xs);
    const base = notas(G, estratos, null, pesos);
    const r = rng(opts.seed || 20261101);
    const reps = [];
    for (let b = 0; b < B; b++) {
      const amostra = {};
      for (const [e, slots] of Object.entries(estratos)) {
        amostra[e] = slots.map(() => slots[Math.floor(r() * slots.length)]);
      }
      const escolha = G.map((g) => g.blocos.map(() => Math.floor(r() * g.blocos.length)));
      reps.push(notas(G, amostra, escolha, pesos));
    }
    const varG = xs.map((_, gi) => variancia(reps.map((rp) => rp.S[gi])));
    const ws = varG.map((v) => 1 / Math.max(isFinite(v) ? v : 1, 1e-6));
    const coef = ajusteQuad(xs, base.S, ws);
    if (!coef) return { erro: 'Nao deu para ajustar a curva.' };
    const xhat = minimoNoIntervalo(coef, lo, hi);
    const xstar = [];
    const ganho = [];
    const repsCoef = [];
    for (const rp of reps) {
      const bb = ajusteQuad(xs, rp.S, ws);
      if (!bb) continue;
      repsCoef.push(bb);
      xstar.push(minimoNoIntervalo(bb, lo, hi));
      // ganho de trocar para a sens do dia, avaliado no x escolhido (sem reotimizar)
      ganho.push(Math.exp(curva(bb, 0) - curva(bb, xhat)) - 1);
    }
    // qualidade do ajuste: a quadratica explica os pontos dentro do ruido?
    let chi2 = 0;
    xs.forEach((x, i) => { if (isFinite(base.S[i])) chi2 += ws[i] * Math.pow(base.S[i] - curva(coef, x), 2); });
    const glAjuste = xs.length - 3;
    // inclinacao de cada faixa: ln(tempo) por unidade de ln(sens). >0 = sens baixa ajuda
    const faixas = {};
    for (const e of Object.keys(estratos)) {
      const nb = G.map((g) => g.blocos.length);
      const lin = ajusteLinear(xs, base.porFaixa[e], nb);
      const boot = reps.map((rp) => ajusteLinear(xs, rp.porFaixa[e], nb)[1]);
      faixas[e] = {
        inclinacao: lin[1],
        ic: [quantil(boot, 0.025), quantil(boot, 0.975)],
        situacoes: estratos[e].length,
        porSens: base.porFaixa[e],
      };
    }
    const seG = varG.map((v) => Math.sqrt(isFinite(v) ? v : NaN));
    return {
      xs, S: base.S, seG, coef, xhat,
      ic: [quantil(xstar, 0.025), quantil(xstar, 0.975)],
      ganho: Math.exp(curva(coef, 0) - curva(coef, xhat)) - 1,
      ganhoIc: [quantil(ganho, 0.025), quantil(ganho, 0.975)],
      noBorda: xstar.filter((v) => Math.abs(v - lo) < 1e-9 || Math.abs(v - hi) < 1e-9).length / Math.max(1, xstar.length),
      chi2, glAjuste, pAjuste: chi2p(chi2, glAjuste),
      lo, hi, faixas, nBlocos: G.map((g) => g.blocos.length), repsCoef,
    };
  }

  // Ponto central da fase 2 so com a estimativa pontual (sem bootstrap).
  function centroRapido(sessao, pesos) {
    const { G, estratos } = preparar(sessao);
    if (G.length < 3) return 0;
    const xs = G.map((g) => g.x);
    const base = notas(G, estratos, null, pesos);
    const coef = ajusteQuad(xs, base.S, G.map((g) => g.blocos.length));
    if (!coef) return 0;
    return minimoNoIntervalo(coef, Math.min(...xs), Math.max(...xs));
  }

  // ---------------- PSA do dia ----------------
  // Cada rodada compara A (ponta de baixo da faixa) e B (ponta de cima), 2 blocos cada,
  // na ordem A B B A ou B A A B. O centro anda w x W/4 com w = diferenca / MDE (entre
  // -1 e 1) e a faixa cai pela metade. Igual a calibracao da bancada PSA v3, com as
  // sondas nas pontas (simulacao: erro tipico 11,8% contra 18,4% com sondas a 25/75%).

  const SIGMA0 = 0.088;   // ruido de partida de uma nota de bloco (vale como 6 graus de liberdade)
  const GL0 = 6;

  // quantil 97,5% da t de Student (expansao de Cornish-Fisher, erro < 0,01 para gl >= 3)
  function t975(gl) {
    const z = 1.959964;
    const z3 = z * z * z, z5 = z3 * z * z, z7 = z5 * z * z;
    return z + (z3 + z) / (4 * gl) + (5 * z5 + 16 * z3 + 3 * z) / (96 * gl * gl)
      + (3 * z7 + 19 * z5 + 17 * z3 - 15 * z) / (384 * gl * gl * gl);
  }

  // nota de um bloco: media ponderada (peso da situacao) de ln(tempo) nas situacoes do deck
  function notaBloco(bl, deck, pesos) {
    const porFaixa = {};
    for (const d of bl.duelos) {
      if (d.adapt || d.slot < 0 || d.invalido || d.t == null) continue;
      const e = deck[d.slot].e;
      (porFaixa[e] = porFaixa[e] || []).push(Math.log(tempoLimitado(d.t)));
    }
    let s = 0, sw = 0;
    for (const [e, ys] of Object.entries(porFaixa)) {
      const W = pesos[e] || 0;
      if (!W) continue;
      s += W * media(ys);
      sw += W;
    }
    return sw ? s / sw : NaN;
  }

  const duelosMedidos = (bl) => bl.duelos.filter((d) => !d.adapt && d.slot >= 0 && !d.invalido && d.t != null).length;

  // ruido medido no dia: as duas notas da mesma sonda na mesma rodada (mesmos duelos).
  // Blocos de tamanhos diferentes vao para a escala de um bloco de 24 (ruido cai com a raiz
  // do numero de duelos); sigma e sempre "de um bloco de 24".
  function ruidoDoDia(sessao, pesos, ateRodada) {
    // quanto confiar no ruido de partida: graus de liberdade gravados na sessao (otimo: 10);
    // testes antigos usavam 6
    const gl0 = sessao.psa && sessao.psa.gl0 != null ? sessao.psa.gl0 : GL0;
    let soma = 0, n = 0;
    for (const r of sessao.rodadas || []) {
      if (ateRodada != null && r.n > ateRodada) break;
      for (const lado of ['A', 'B']) {
        const bls = r.blocos.map((i) => sessao.blocos[i]).filter((b) => b.lado === lado && b.feito);
        const ns = bls.map((b) => notaBloco(b, sessao.deck, pesos));
        if (ns.length === 2 && ns.every(isFinite)) {
          const nd = (duelosMedidos(bls[0]) + duelosMedidos(bls[1])) / 2;
          soma += (Math.pow(ns[0] - ns[1], 2) / 2) * (nd / 24);
          n += 1;
        }
      }
    }
    const gl = n + gl0;
    return { sigma: Math.sqrt((soma + gl0 * SIGMA0 * SIGMA0) / gl), gl, medidos: n, gl0 };
  }

  // regras do PSA gravadas na sessao (testes antigos: passo 1/4 da faixa, faixa x 1/2, gama 1)
  function regras(sessao) {
    const p = sessao.psa || {};
    return { k: p.k != null ? p.k : 0.25, rho: p.rho != null ? p.rho : 0.5, gama: p.gama != null ? p.gama : 1, ks: p.ks || null };
  }

  function avaliarRodada(sessao, r, pesos) {
    const { k: k0, ks, gama } = regras(sessao);
    // passo da rodada: um por rodada (forma livre; a rodada extra repete o ultimo) ou o mesmo em todas
    const k = ks ? ks[Math.min(r.n, ks.length) - 1] : k0;
    const notas = { A: [], B: [] }, tempos = { A: [], B: [] };
    let somaN = 0, nb = 0;
    for (const i of r.blocos) {
      const bl = sessao.blocos[i];
      if (!bl.feito) continue;
      notas[bl.lado].push(notaBloco(bl, sessao.deck, pesos));
      somaN += duelosMedidos(bl); nb++;
      for (const d of bl.duelos) if (!d.adapt && d.slot >= 0 && d.t != null) tempos[bl.lado].push(d.t);
    }
    const SA = media(notas.A), SB = media(notas.B);
    const ru = ruidoDoDia(sessao, pesos, r.n);
    const nDuelos = nb ? somaN / nb : 24;
    const se = ru.sigma * Math.sqrt(24 / Math.max(1, nDuelos))
      * Math.sqrt(1 / Math.max(1, notas.A.length) + 1 / Math.max(1, notas.B.length));
    const mde = gama * t975(ru.gl) * se;     // forca exigida: gama x MDE de 95% (gama otimizado)
    const delta = SB - SA;                    // > 0: A (sens menor) foi mais rapida
    const w = Math.max(-1, Math.min(1, delta / mde));
    const forca = Math.abs(w);
    const quem = w > 0 ? 'A' : 'B';
    const veredito = forca >= 1 ? `vence ${quem}` : forca >= 0.5 ? `puxão forte para ${quem}` : forca >= 0.2 ? `puxão fraco para ${quem}` : 'empate';
    // tempo "da nota": media geometrica do tempo ate matar, com o peso de cada situacao
    return { SA, SB, delta, mde, w, t: t975(ru.gl), sigma: ru.sigma, gl: ru.gl, veredito,
      tempoA: Math.exp(SA), tempoB: Math.exp(SB),
      medianaA: quantil(tempos.A, 0.5), medianaB: quantil(tempos.B, 0.5),
      centroNovo: r.centro - w * k * r.W, k, gama };
  }

  // t de Student 97,5% exata para poucos graus de liberdade (Cornish-Fisher erra abaixo de 3)
  const tPequeno = (gl) => (gl <= 1 ? 12.706 : gl === 2 ? 4.303 : t975(gl));

  // Efeito da sens em cada situacao so com comparacoes PAREADAS: dentro de cada rodada, a
  // mesma situacao jogada nas duas pontas (A e B). Inclinacao = quanto ln(tempo) muda por
  // unidade de ln(sens), minimos quadrados pela origem nos pares; IC pela t dos residuos.
  // (Comparar sens de rodadas diferentes misturaria o efeito da sens com a diferenca entre
  // as situacoes de cada rodada.)
  function inclinacoesPareadas(sessao) {
    const por = {};
    for (const r of sessao.rodadas || []) {
      const bls = r.blocos.map((i) => sessao.blocos[i]);
      if (!bls.every((b) => b.feito)) continue;
      const bA = bls.find((b) => b.lado === 'A'), bB = bls.find((b) => b.lado === 'B');
      if (!bA || !bB) continue;
      const dx = bB.x - bA.x;
      const ys = { A: new Map(), B: new Map() };
      for (const b of bls) {
        for (const d of b.duelos) {
          if (d.adapt || d.slot < 0 || d.invalido || d.t == null) continue;
          const m = ys[b.lado];
          if (!m.has(d.slot)) m.set(d.slot, []);
          m.get(d.slot).push(Math.log(tempoLimitado(d.t)));
        }
      }
      for (const [slot, ya] of ys.A) {
        const yb = ys.B.get(slot);
        if (!yb) continue;
        const e = sessao.deck[slot].e;
        (por[e] = por[e] || { obs: [], slots: new Set() }).obs.push([dx, media(yb) - media(ya)]);
        por[e].slots.add(slot);
      }
    }
    const out = {};
    for (const [e, { obs, slots }] of Object.entries(por)) {
      const sxx = obs.reduce((s, o) => s + o[0] * o[0], 0);
      const sxy = obs.reduce((s, o) => s + o[0] * o[1], 0);
      const b = sxx > 0 ? sxy / sxx : 0;
      const n = obs.length;
      const res2 = obs.reduce((s, o) => s + Math.pow(o[1] - b * o[0], 2), 0);
      const se = n > 1 && sxx > 0 ? Math.sqrt(res2 / (n - 1) / sxx) : NaN;
      const tq = n > 1 ? tPequeno(n - 1) : NaN;
      out[e] = { inclinacao: b, ic: isFinite(se) ? [b - tq * se, b + tq * se] : [-Infinity, Infinity],
        situacoes: slots.size, pares: n };
    }
    return out;
  }

  // caminho inteiro: rodadas fechadas, centro final e ruido do metodo (95%)
  function caminho(sessao, pesos) {
    const out = [];
    let somaVar = 0;
    for (const r of sessao.rodadas || []) {
      if (!r.blocos.every((i) => sessao.blocos[i].feito)) break;
      const av = avaliarRodada(sessao, r, pesos);
      // quanto o puro acaso move o centro: so ruido -> w ~ N(0, 1/(gama t)^2) -> passo k W w
      somaVar += Math.pow(av.k * r.W / (av.gama * av.t), 2);
      out.push(Object.assign({ n: r.n, centro: r.centro, W: r.W, duelos: r.duelos, a: r.centro - r.W / 2, b: r.centro + r.W / 2 }, av));
    }
    const final = out.length ? out[out.length - 1].centroNovo : 0;
    const sigmaCaminho = Math.sqrt(somaVar);
    return { rodadas: out, final, sigmaCaminho, faixa: [final - 1.96 * sigmaCaminho, final + 1.96 * sigmaCaminho],
      andou: Math.abs(final) > 1.96 * sigmaCaminho };
  }

  global.Stats = { analisar, centroRapido, curva, quantil, media, variancia, rng, chi2p, tempoLimitado, T_MIN, T_MAX,
    t975, notaBloco, ruidoDoDia, avaliarRodada, caminho, inclinacoesPareadas, regras };
})(window);
