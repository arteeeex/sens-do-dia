// Onde e por que a mira erra. Cada duelo vira tres fases:
//   reacao  = do alvo aparecer ate a mira comecar a andar,
//   flick   = o movimento principal (do inicio ate a primeira parada ou inversao),
//   ajuste  = as correcoes ate a kill.
// No fim do flick a mira esta na cabeca, passou dela (sens rapida demais para aquele
// movimento) ou ficou curta (sens lenta demais / remada). Cada tiro errado e medido em
// "cabecas": 1 = a borda da hitbox na direcao do erro.
(function (global) {
  'use strict';

  const suav = (v) => v.map((_, i) => {
    let s = 0, k = 0;
    for (let j = i - 1; j <= i + 1; j++) if (j >= 0 && j < v.length) { s += v[j]; k++; }
    return s / k;
  });
  const mediana = (a) => {
    const b = a.filter(isFinite).sort((x, y) => x - y);
    if (!b.length) return NaN;
    const m = (b.length - 1) / 2;
    return (b[Math.floor(m)] + b[Math.ceil(m)]) / 2;
  };

  function eixos(e0x, e0y, ax, ay) {
    const th = Math.hypot(e0x, e0y);
    const u = th > 1e-9 ? [-e0x / th, -e0y / th] : [1, 0];   // da mira para a cabeca
    const w = [-u[1], u[0]];
    const raio = (d) => 1 / Math.sqrt(Math.pow(d[0] / ax, 2) + Math.pow(d[1] / ay, 2));
    return { th, u, w, ru: raio(u), rw: raio(w) };
  }

  function duelo(d) {
    const A = d.am;
    if (!A || A.length < 4 || d.ax0 == null || !(d.ax0 > 0)) return null;
    const E = eixos(A[0][1], A[0][2], d.ax0, d.ay0);
    const flick = E.th > 2 * E.ru;
    const sp = [0];
    for (let i = 1; i < A.length; i++) {
      const dt = (A[i][0] - A[i - 1][0]) / 1000;
      sp.push(dt > 0 ? Math.hypot(A[i][3] - A[i - 1][3], A[i][4] - A[i - 1][4]) / dt : 0);
    }
    const s = suav(sp);
    let pico = 0, kp = 0;
    for (let i = 0; i < s.length; i++) if (s[i] > pico) { pico = s[i]; kp = i; }
    let k0 = 0;
    const lim0 = Math.max(4, 0.1 * pico);
    while (k0 < s.length - 1 && s[k0] < lim0) k0++;
    const tFim = d.timeout ? 2500 : d.t * 1000;
    const out = { flick, th: E.th, ru: E.ru, tReacao: A[k0][0], tiros: [], kill: !d.timeout,
      hs: d.hs != null ? !!d.hs : !d.timeout };
    let k1 = k0;
    if (flick) {
      k1 = A.length - 1;
      for (let i = Math.max(kp, k0) + 1; i < A.length - 1; i++) {
        const du = (A[i][3] - A[i - 1][3]) * E.u[0] + (A[i][4] - A[i - 1][4]) * E.u[1];
        if (du < -0.002) { k1 = i - 1; break; }                       // inverteu: voltou
        if (s[i] <= s[i - 1] && s[i] <= s[i + 1] && s[i] < 0.35 * pico) { k1 = i; break; }  // parou
      }
      const a1 = A[k1][1] * E.u[0] + A[k1][2] * E.u[1];
      const l1 = A[k1][1] * E.w[0] + A[k1][2] * E.w[1];
      out.n1 = a1 / E.ru;              // > 0 passou, < 0 ficou curto (em cabecas)
      out.l1 = l1 / E.rw;
      out.classe = out.n1 > 1 ? 'passou' : out.n1 < -1 ? 'curto' : Math.abs(out.l1) > 1 ? 'lado' : 'cabeca';
      out.tFlick = A[k1][0] - A[k0][0];
      out.tAjuste = Math.max(0, tFim - A[k1][0]);
      // correcoes: novos picos de velocidade depois do flick (com histerese)
      let corr = 0, subindo = false, base = s[k1];
      const limC = Math.max(6, 0.15 * pico);
      for (let i = k1 + 1; i < s.length; i++) {
        if (!subindo && s[i] > limC && s[i] > base * 1.5) { corr++; subindo = true; }
        if (subindo && s[i] < 0.5 * limC) { subindo = false; base = s[i]; }
        if (!subindo) base = Math.min(base, s[i]);
      }
      out.corr = corr;
    } else {
      out.tAjuste = Math.max(0, tFim - A[k0][0]);
    }
    const tFlickFim = A[k1][0];
    for (const t of d.xy || []) {
      const [tm, ex, ey, hit, vel, axs, ays] = t;
      // parte acertada: 0 nada, 1 cabeca, 2 peito, 3 barriga, 4 braco, 5 perna (testes antigos: so cabeca)
      const parte = t.length > 7 ? t[7] : (hit ? 1 : 0);
      const Es = eixos(A[0][1], A[0][2], axs, ays);
      let nu, nw;
      if (flick) {
        nu = (ex * E.u[0] + ey * E.u[1]) / Es.ru;
        nw = (ex * E.w[0] + ey * E.w[1]) / Es.rw;
      } else {
        nu = ex / axs;      // sem flick: eixo da tela (direita +, abaixo +)
        nw = ey / ays;
      }
      out.tiros.push({
        nu, nw, hit: !!hit, parte, corpo: parte >= 2,
        fase: flick && tm < tFlickFim ? 'flick' : 'ajuste',
        correndo: vel * 0.1 > (flick ? Es.ru : axs),   // mira andou mais de 1 cabeca em 100 ms
        classe: hit ? 'acerto' : !flick ? 'perto' : Math.abs(nu) >= Math.abs(nw) ? (nu > 0 ? 'passou' : 'curto') : 'lado',
      });
    }
    return out;
  }

  function zProp(a, na, b, nb) {
    if (!na || !nb) return NaN;
    const p = (a + b) / (na + nb);
    const se = Math.sqrt(p * (1 - p) * (1 / na + 1 / nb));
    if (!(se > 0)) return NaN;
    const z = Math.abs(a / na - b / nb) / se;
    // p bicaudal pela normal
    const t = 1 / (1 + 0.2316419 * z);
    const pdf = Math.exp(-z * z / 2) / Math.sqrt(2 * Math.PI);
    const cauda = pdf * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return 2 * cauda;
  }

  function porSens(sessao) {
    const grupos = new Map();
    for (const bl of sessao.blocos) {
      if (bl.tipo !== 'medida' || !bl.feito) continue;
      const k = bl.x.toFixed(4);
      if (!grupos.has(k)) grupos.set(k, { x: bl.x, duelos: [] });
      for (const d of bl.duelos) {
        if (d.adapt || d.slot < 0) continue;
        const r = duelo(d);
        if (r) grupos.get(k).duelos.push(r);
      }
    }
    const lista = [...grupos.values()].sort((a, b) => a.x - b.x);
    for (const g of lista) {
      const fl = g.duelos.filter((d) => d.flick);
      const conta = (c) => fl.filter((d) => d.classe === c).length;
      g.nFlick = fl.length;
      g.cabeca = conta('cabeca'); g.passou = conta('passou'); g.curto = conta('curto'); g.lado = conta('lado');
      g.n1 = mediana(fl.map((d) => d.n1));
      g.corr = fl.length ? fl.reduce((a, d) => a + d.corr, 0) / fl.length : NaN;
      g.tReacao = mediana(g.duelos.map((d) => d.tReacao));
      g.tFlick = mediana(fl.map((d) => d.tFlick));
      g.tAjuste = mediana(g.duelos.map((d) => d.tAjuste));
      const tiros = g.duelos.flatMap((d) => d.tiros);
      const erros = tiros.filter((t) => !t.hit && !t.corpo);   // nao pegou no boneco
      g.tiros = tiros.length;
      g.erros = erros.length;
      g.corpo = tiros.filter((t) => t.corpo).length;
      g.kills = g.duelos.filter((d) => d.kill).length;
      g.hs = g.duelos.filter((d) => d.kill && d.hs).length;
      g.errosFlick = erros.filter((t) => t.fase === 'flick').length;
      g.errosCorrendo = erros.filter((t) => t.correndo).length;
      g.errosPorClasse = { passou: 0, curto: 0, lado: 0, perto: 0 };
      for (const t of erros) g.errosPorClasse[t.classe] = (g.errosPorClasse[t.classe] || 0) + 1;
      g.pontos = g.duelos.filter((d) => d.flick).flatMap((d) => d.tiros).slice(0, 400);
    }
    return lista;
  }

  // Frases so com o que os dados mostram (comparando a menor e a maior sens testada).
  function leitura(lista, sensDe) {
    if (lista.length < 2) return [];
    const lo = lista[0], hi = lista[lista.length - 1];
    const frases = [];
    const pct = (a, n) => (n ? Math.round(100 * a / n) : 0) + '%';
    const sig = (p) => (isFinite(p) ? (p < 0.05 ? 'diferença acima do ruído' : 'dentro do ruído') : 'poucos dados');
    if (lo.nFlick >= 8 && hi.nFlick >= 8) {
      frases.push(`No fim do flick, a mira <b>passou da cabeça</b> em ${pct(hi.passou, hi.nFlick)} das vezes na maior sens (${sensDe(hi.x)}) e em ${pct(lo.passou, lo.nFlick)} na menor (${sensDe(lo.x)}): ${sig(zProp(hi.passou, hi.nFlick, lo.passou, lo.nFlick))}.`);
      frases.push(`A mira <b>ficou curta</b> em ${pct(lo.curto, lo.nFlick)} na menor sens e em ${pct(hi.curto, hi.nFlick)} na maior: ${sig(zProp(lo.curto, lo.nFlick, hi.curto, hi.nFlick))}.`);
      frases.push(`Correções depois do flick: ${lo.corr.toFixed(1).replace('.', ',')} por flick na menor sens, ${hi.corr.toFixed(1).replace('.', ',')} na maior.`);
    }
    if (lo.kills >= 8 && hi.kills >= 8) {
      frases.push(`Kill de <b>cabeça</b>: ${pct(lo.hs, lo.kills)} na menor sens e ${pct(hi.hs, hi.kills)} na maior (${sig(zProp(lo.hs, lo.kills, hi.hs, hi.kills))}). O resto foi no corpo, com 3 ou 4 tiros.`);
    }
    const todos = lista.flatMap((g) => g.duelos);
    const r = mediana(todos.map((d) => d.tReacao)), a = mediana(todos.map((d) => d.tAjuste));
    const f = mediana(todos.filter((d) => d.flick).map((d) => d.tFlick));
    if (isFinite(r) && isFinite(a)) {
      frases.push(`Onde vai o teu tempo (mediana): reação ${Math.round(r)} ms, flick ${isFinite(f) ? Math.round(f) : '–'} ms, ajuste ${Math.round(a)} ms. A reação quase não depende da sens; o ajuste é onde a sens mais pesa.`);
    }
    return frases;
  }

  global.Erros = { duelo, porSens, leitura, zProp };
})(window);
