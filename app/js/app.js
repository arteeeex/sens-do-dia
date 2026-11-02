// Protocolo do dia, telas e resultado.
(function () {
  'use strict';

  const P = window.PERFIL;
  const CHAVE = 'sens-do-dia/v1';
  const LN3 = Math.log(3);
  const url = new URLSearchParams(location.search);
  const RAPIDO = url.has('rapido');
  // Numeros exatos de cada duracao (quarta revisao, 02/11/2026): analise/otimizar_livre.py (descida
  // coordenada com os mesmos sorteios para todos os desenhos) e analise/polir_certificado.py (vizinhos
  // em 400 mil dias novos a cada volta ate nenhum ganhar alem do acaso). Gerado por duracoes_js.py.
  //   Ws   = largura (em ln) da faixa de cada rodada; as duas pontas sao as sondas
  //   ks   = passo de cada rodada: o centro anda forca x k x faixa
  //   gama = forca = diferenca / (gama x MDE de 95%), entre -1 e 1
  //   duelosPorRodada = alvos por bloco em cada rodada (numero de rodadas = tamanho da lista)
  //   adapt = 0: todos os alvos contam (ganhou de 1 em todos os cenarios de custo de troca)
  //   (testes antigos: W0, k e rho, faixa da rodada seguinte = faixa x rho)
  // Perda media em 300 mil dias novos (ruido incerto, com custo de troca de sens e aquecimento),
  // desenho anterior -> este: 8 min 0,2034 -> 0,1828%; 12 min 0,1814 -> 0,1651%; 16 min 0,1697 ->
  // 0,1513%; 20 min 0,1615 -> 0,1444%; 25 min 0,1535 -> 0,1366%; 35 min 0,1470 -> 0,1282%.
  const DURACOES = {
    '8': { nome: '8 minutos', Ws: [Math.log(3.23365), Math.log(2.93981), Math.log(2.94461), Math.log(2.90775), Math.log(2.92232)],
      ks: [0.19, 0.1075, 0.0875, 0.0775, 0.065], gama: 1.45, gl0: 22,
      duelosPorRodada: [29, 15, 14, 14, 13], adapt: 0, aquec: 0 },
    '12': { nome: '12 minutos (padrão)', Ws: [Math.log(3.03774), Math.log(2.81477), Math.log(2.75069), Math.log(2.72502), Math.log(2.71086), Math.log(2.69608)],
      ks: [0.185, 0.10625, 0.085, 0.07125, 0.0625, 0.05375], gama: 1.3875, gl0: 27,
      duelosPorRodada: [36, 22, 20, 19, 19, 18], adapt: 0, aquec: 0 },
    '16': { nome: '16 minutos', Ws: [Math.log(2.97015), Math.log(2.5788), Math.log(2.5588), Math.log(2.54613), Math.log(2.5391), Math.log(2.53619), Math.log(2.52341), Math.log(2.49968), Math.log(2.5248)],
      ks: [0.18862, 0.12218, 0.10288, 0.09002, 0.07716, 0.06859, 0.06216, 0.05787, 0.05144], gama: 1.57543, gl0: 27,
      duelosPorRodada: [41, 18, 18, 17, 17, 16, 17, 17, 16], adapt: 0, aquec: 0 },
    '20': { nome: '20 minutos', Ws: [Math.log(2.88237), Math.log(2.60472), Math.log(2.5588), Math.log(2.49571), Math.log(2.48882), Math.log(2.48597), Math.log(2.44883), Math.log(2.4258), Math.log(2.45018), Math.log(2.45018)],
      ks: [0.185, 0.1125, 0.09, 0.08, 0.07, 0.06, 0.0525, 0.0525, 0.045, 0.04], gama: 1.4875, gl0: 33,
      duelosPorRodada: [44, 24, 22, 21, 21, 20, 19, 20, 19, 18], adapt: 0, aquec: 0 },
    '25': { nome: '25 minutos', Ws: [Math.log(2.88237), Math.log(2.5018), Math.log(2.47643), Math.log(2.44145), Math.log(2.42034), Math.log(2.3998), Math.log(2.40286), Math.log(2.3807), Math.log(2.36854), Math.log(2.36556), Math.log(2.39491), Math.log(2.37108), Math.log(2.37108), Math.log(2.32413)],
      ks: [0.18312, 0.114, 0.095, 0.0855, 0.076, 0.0665, 0.057, 0.057, 0.04987, 0.04513, 0.04038, 0.038, 0.038, 0.03562], gama: 1.53187, gl0: 35,
      duelosPorRodada: [45, 21, 20, 20, 20, 18, 17, 18, 18, 17, 16, 15, 16, 16], adapt: 0, aquec: 0 },
    '35': { nome: '35 minutos (máximo)', Ws: [Math.log(2.75554), Math.log(2.48992), Math.log(2.42664), Math.log(2.38932), Math.log(2.36415), Math.log(2.35), Math.log(2.34598), Math.log(2.32798), Math.log(2.31881), Math.log(2.29472), Math.log(2.28975), Math.log(2.29182), Math.log(2.27758), Math.log(2.28088), Math.log(2.25818), Math.log(2.22456)],
      ks: [0.185, 0.11, 0.085, 0.08, 0.07, 0.06, 0.0525, 0.05, 0.045, 0.0425, 0.0375, 0.035, 0.035, 0.03, 0.03, 0.03], gama: 1.5, gl0: 43,
      duelosPorRodada: [52, 29, 24, 25, 25, 24, 23, 23, 23, 23, 22, 22, 23, 23, 23, 24], adapt: 0, aquec: 0 },
  };
  const DURACAO_PADRAO = '12';
  function protoDe(chave) {
    const d = DURACOES[chave] || DURACOES[DURACAO_PADRAO];
    const p = Object.assign({ chave: DURACOES[chave] ? chave : DURACAO_PADRAO }, d);
    p.duelosPorRodada = d.duelosPorRodada.slice();
    if (d.Ws) { p.Ws = d.Ws.slice(); p.ks = d.ks.slice(); p.W0 = d.Ws[0]; p.k = d.ks[0]; }
    if (RAPIDO) {   // so para testar o app: mesmas regras, poucos alvos
      p.duelosPorRodada = p.duelosPorRodada.map((n) => Math.max(2, Math.round(n / 6)));
      p.adapt = Math.min(p.adapt, 1);
      p.aquec = Math.min(p.aquec, 3);
    }
    p.duelosExtra = p.duelosPorRodada[p.duelosPorRodada.length - 1];   // rodada extra = tamanho da ultima
    p.rodadas = p.duelosPorRodada.length;
    p.deck = Math.max(...p.duelosPorRodada);                            // todo bloco cabe no deck
    return p;
  }
  let PROTO = protoDe(DURACAO_PADRAO);
  // tempo previsto: ~1,05 s por alvo (kill + espera) e ~6 s de pausa por bloco
  const minutosPrevistos = (ns, adapt, aquec) => ((aquec + ns.reduce((s, n) => s + 4 * (n + adapt), 0)) * 1.05 + ns.length * 4 * 6) / 60;
  // regras de uma sessao (testes antigos nao tinham isso gravado: valem as regras da epoca)
  const psaDa = (s) => s.psa || { W0: LN3, k: 0.25, rho: 0.5, gama: 1 };
  // faixa (largura em ln) da rodada n: forma livre (uma por rodada, quarta revisao; a rodada extra
  // repete a ultima) ou geometrica dos testes antigos (W0 na 1a, depois a anterior x rho)
  const faixaDa = (psa, n, ultW) => (psa.Ws ? psa.Ws[Math.min(n, psa.Ws.length) - 1] : (n === 1 ? psa.W0 : ultW * psa.rho));
  const listaFaixas = (psa, R) => {
    const out = [];
    let W = null;
    for (let n = 1; n <= R; n++) { W = faixaDa(psa, n, W); out.push('×' + num(Math.exp(W), 2)); }
    return out;
  };
  const protocoloDa = (s) => s.protocolo || { duelosPorRodada: [36, 36, 24, 12, 12], duelosExtra: 12, adapt: 3 };
  const pesos = Object.fromEntries(P.estratos.map((e) => [e.id, e.peso]));
  const ESTR = Object.fromEntries(P.estratos.map((e) => [e.id, e]));
  const FORMATOS = {
    'nativo': { id: 'nativo', aspecto: 16 / 9, esticado: false, barras: false, nome: 'nativo' },
    '4:3e': { id: '4:3e', aspecto: 4 / 3, esticado: true, barras: false, nome: '4:3 esticado' },
    '4:3b': { id: '4:3b', aspecto: 4 / 3, esticado: false, barras: true, nome: '4:3 com barras' },
    '16:10e': { id: '16:10e', aspecto: 16 / 10, esticado: true, barras: false, nome: '16:10 esticado' },
    '5:4e': { id: '5:4e', aspecto: 5 / 4, esticado: true, barras: false, nome: '5:4 esticado' },
  };

  const $ = (id) => document.getElementById(id);
  const fmt3 = (v) => (Math.round(v * 1000) / 1000).toFixed(3);
  const pct = (v, casas = 1) => (v * 100).toFixed(casas).replace('.', ',') + '%';
  const num = (v, casas = 1) => Number(v).toFixed(casas).replace('.', ',');
  // numero exato da otimizacao, sem zeros sobrando (0,10625; 0,185)
  const numx = (v) => Number(v).toFixed(5).replace(/0+$/, '').replace(/\.$/, '').replace('.', ',');
  const cm360 = (sens, dpi) => (360 / (0.022 * sens) / dpi) * 2.54;
  const hoje = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };

  // ---------- armazenamento ----------
  function carregar() {
    try {
      const d = JSON.parse(localStorage.getItem(CHAVE) || 'null');
      if (d && d.cfg) return d;
    } catch (e) { /* sem dados */ }
    return { cfg: { dpi: 1600, sens: 0.5, formato: 'nativo' }, sessao: null, historico: [] };
  }
  let dados = carregar();
  // Se o navegador ficar sem espaco, salva sem a trajetoria quadro a quadro ('am': so serve
  // para o diagnostico do flick; o PSA nao usa) e avisa no resultado para exportar o JSON.
  let estadoSalvar = 'ok';   // 'ok' | 'enxuto' | 'falhou'
  function salvar() {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(dados));
      return;
    } catch (e) { /* tenta enxuto */ }
    try {
      localStorage.setItem(CHAVE, JSON.stringify(dados, (k, v) => (k === 'am' ? undefined : v)));
      if (estadoSalvar === 'ok') estadoSalvar = 'enxuto';
    } catch (e2) {
      estadoSalvar = 'falhou';
      console.warn('nao deu para salvar no navegador', e2);
    }
  }

  // ---------- sorteios ----------
  function embaralhar(a, r) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1));
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function sortearDeck(r) {
    const ids = P.estratos.filter((e) => e.n > 0 && e.peso > 0).map((e) => e.id);
    const quotas = ids.map((id) => pesos[id] * PROTO.deck);
    const n = quotas.map((q) => Math.max(1, Math.floor(q)));
    let falta = PROTO.deck - n.reduce((a, b) => a + b, 0);
    const restos = quotas.map((q, i) => [q - Math.floor(q), i]).sort((a, b) => b[0] - a[0]);
    for (let k = 0; falta > 0; k = (k + 1) % restos.length) { n[restos[k][1]]++; falta--; }
    while (falta < 0) {
      let i = n.indexOf(Math.max(...n));
      n[i]--; falta++;
    }
    const deck = [];
    ids.forEach((id, i) => {
      const pool = [];
      P.situacoes.forEach((s, idx) => { if (s.e === id) pool.push(idx); });
      embaralhar(pool, r);
      for (let k = 0; k < n[i]; k++) deck.push({ sit: pool[k % pool.length], e: id });
    });
    return deck;
  }

  // situacoes soltas (aquecimento e adaptacao) na mesma mistura do peso, fora do deck
  function mistura(qtd, r, deck) {
    const noDeck = new Set(deck.map((d) => d.sit));
    const ids = P.estratos.filter((e) => e.n > 0 && e.peso > 0);
    const out = [];
    for (let k = 0; k < qtd; k++) {
      let u = r(), e = ids[ids.length - 1];
      for (const c of ids) { if (u < c.peso) { e = c; break; } u -= c.peso; }
      const pool = [];
      P.situacoes.forEach((s, idx) => { if (s.e === e.id && !noDeck.has(idx)) pool.push(idx); });
      const sit = pool.length ? pool[Math.floor(r() * pool.length)] : deck[0].sit;
      out.push({ sit, e: e.id, slot: -1, espelho: r() < 0.5 ? 1 : -1 });
    }
    return out;
  }

  // n situacoes do deck na mesma proporcao do peso (maior resto, pelo menos 1 por faixa
  // quando cabe). A rodada inteira usa as mesmas: A e B se comparam nos mesmos duelos.
  function subdeck(deck, n, r) {
    if (n >= deck.length) return deck.map((_, i) => i);
    const porFaixa = {};
    deck.forEach((d, i) => { (porFaixa[d.e] = porFaixa[d.e] || []).push(i); });
    const ids = Object.keys(porFaixa);
    const quotas = ids.map((e) => (porFaixa[e].length / deck.length) * n);
    const q = quotas.map((v) => Math.floor(v));
    let falta = n - q.reduce((a, b) => a + b, 0);
    const ordem = quotas.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
    for (let k = 0; falta > 0; k = (k + 1) % ordem.length, falta--) q[ordem[k][1]]++;
    const out = [];
    ids.forEach((e, i) => out.push(...embaralhar(porFaixa[e].slice(), r).slice(0, q[i])));
    return out;
  }

  // espelho = sorteado uma vez por situacao na rodada e igual nos 4 blocos: A e B veem
  // exatamente o mesmo alvo (lado incluso). Nas demos o alvo aparece 50% de cada lado.
  function blocoMedida(x, lado, rodada, deck, slotsRodada, espelhos, nAdapt, r) {
    const adapt = mistura(nAdapt, r, deck).map((d) => Object.assign(d, { adapt: true }));
    const slots = embaralhar(slotsRodada.slice(), r);
    const itens = slots.map((slot) => ({ sit: deck[slot].sit, e: deck[slot].e, slot, espelho: espelhos[slot] }));
    return { tipo: 'medida', x, lado, rodada, plano: adapt.concat(itens), duelos: [], feito: false };
  }

  function novaSessao(cfg, sementeFixa) {
    // simulacao (?sim, ?cobertura) passa a semente: deck e ordem iguais a cada vez que roda
    const semente = sementeFixa != null ? sementeFixa >>> 0 : (Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0;
    const r = Stats.rng(semente);
    const deck = sortearDeck(r);
    // aquecimento so existe se o protocolo tiver alvos para ele (o otimo exato de 12 min e 0)
    const blocos = PROTO.aquec > 0 ? [{ tipo: 'aquec', x: 0, plano: mistura(PROTO.aquec, r, deck), duelos: [], feito: false }] : [];
    const s = { id: semente, data: hoje(), sens0: cfg.sens, dpi: cfg.dpi, formato: cfg.formato, versao: 'psa',
      psa: PROTO.Ws ? { W0: PROTO.Ws[0], k: PROTO.ks[0], Ws: PROTO.Ws.slice(), ks: PROTO.ks.slice(), gama: PROTO.gama, gl0: PROTO.gl0 }
        : { W0: PROTO.W0, k: PROTO.k, rho: PROTO.rho, gama: PROTO.gama, gl0: PROTO.gl0 },
      protocolo: { duelosPorRodada: PROTO.duelosPorRodada.slice(), duelosExtra: PROTO.duelosExtra, adapt: PROTO.adapt },
      deck, blocos, rodadas: [], rodadasAlvo: PROTO.rodadas, atual: 0, feito: false, semRaw: false, inicio: Date.now() };
    planejarRodada(s);
    return s;
  }

  // Proxima rodada do PSA: parte do centro que a rodada anterior deixou, com metade da faixa.
  // Sondas nas duas pontas (A = de baixo, B = de cima); ordem A B B A nas rodadas impares e
  // B A A B nas pares, para o custo de trocar de sens nao virar evidencia.
  function planejarRodada(s) {
    const psa = psaDa(s), proto = protocoloDa(s);
    let centro = 0, W = faixaDa(psa, 1, null);
    if (s.rodadas.length) {
      const cam = Stats.caminho(s, pesos);
      const ult = s.rodadas[s.rodadas.length - 1];
      centro = cam.final;
      W = faixaDa(psa, s.rodadas.length + 1, ult.W);
    }
    const n = s.rodadas.length + 1;
    const r = Stats.rng((s.id ^ Math.imul(0x9e3779b9, n)) >>> 0);
    const a = centro - W / 2, b = centro + W / 2;
    const ordem = n % 2 === 1 ? [['A', a], ['B', b], ['B', b], ['A', a]] : [['B', b], ['A', a], ['A', a], ['B', b]];
    const nDuelos = proto.duelosPorRodada[n - 1] || proto.duelosExtra;
    const slots = subdeck(s.deck, nDuelos, r);
    const espelhos = {};
    for (const slot of slots) espelhos[slot] = r() < 0.5 ? 1 : -1;
    const idx = [];
    for (const [lado, x] of ordem) {
      idx.push(s.blocos.length);
      s.blocos.push(blocoMedida(+x.toFixed(5), lado, n, s.deck, slots, espelhos, proto.adapt, r));
    }
    s.rodadas.push({ n, centro, W, duelos: slots.length, blocos: idx });
  }

  // Mais uma rodada no mesmo dia: afina mais a faixa, sem misturar dias.
  function estender(s) {
    s.rodadasAlvo += 1;
    s.feito = false;
  }

  const totalMedidos = (s) => s.rodadasAlvo * 4;

  // ---------- tela inicial ----------
  function lerCfg() {
    const dpi = parseInt($('dpi').value, 10);
    const sens = parseFloat(String($('sens').value).replace(',', '.'));
    const formato = $('formato').value;
    const duracao = $('duracao').value || DURACAO_PADRAO;
    return { dpi, sens, formato, duracao, ok: dpi >= 100 && dpi <= 32000 && sens > 0.01 && sens < 20 };
  }

  // texto "Como funciona" escrito a partir dos numeros da duracao escolhida
  function explicarProtocolo() {
    const m = Math.exp(PROTO.W0 / 2);
    const faixas = listaFaixas(PROTO, PROTO.rodadas);
    $('como-1').innerHTML = PROTO.aquec > 0
      ? `1. <b>Aquecimento</b> de ${PROTO.aquec} alvos na tua sens (não conta).`
      : `1. <b>Sem aquecimento dentro do teste.</b> Na simulação duelo a duelo, aquecer só gasta tempo: 0 alvos deu a menor perda (20 alvos: +0,004 ponto; 60: +0,007), e mesmo começando 50% mais lento a diferença fica em ±0,01 ponto. Se quiser se sentir quente, aquece no CS antes: não muda a conta.`;
    $('como-2').innerHTML = `2. <b>${PROTO.rodadas} rodadas de PSA, 4 blocos cada.</b> A rodada joga as duas pontas da faixa (A e B) na ordem A B B A (B A A B na seguinte). ` +
      `A 1ª vai de ÷${num(m, 4)} a ×${num(m, 4)} da tua sens. O centro anda para o lado que rendeu mais, <b>na proporção da força da evidência</b>: ` +
      `força = diferença ÷ (${numx(PROTO.gama)} × MDE), entre −1 e 1, e o centro anda força × ` +
      (PROTO.Ws
        ? `o passo da rodada (${PROTO.ks.map(numx).join('; ')}) da faixa. A faixa de cada rodada é ${faixas.join(', ')}: ` +
          `a otimização achou as sondas longe uma da outra o teste todo (a diferença entre duas sens longe aparece mais que o ruído) e o passo do centro caindo rodada a rodada: grande no começo, pequeno no fim. Conferido também com o custo de trocar de sens. `
        : `${num(PROTO.k, 4)} da faixa. A faixa encolhe ×${num(PROTO.rho, 4)} por rodada (${faixas.join(', ')}): devagar, para um ruído no começo poder ser corrigido depois. `) +
      `Alvos por bloco em cada rodada: <b>${PROTO.duelosPorRodada.join(', ')}</b>. A sens de cada bloco aparece no canto.`;
    $('como-3').innerHTML = `3. Os 4 blocos de uma rodada repetem as <b>mesmas situações</b>, sorteadas das tuas partidas na proporção do peso, em ordem embaralhada e espelhadas ao acaso (o mesmo lado nos 4 blocos). ` +
      (PROTO.adapt === 0
        ? '<b>Todos os alvos contam.</b> Na simulação, separar um alvo por bloco para acostumar com a sens nova custa mais tempo do que ajuda, em todos os cenários testados, inclusive com os primeiros alvos depois da troca 25% mais lentos: a ordem A B B A já cancela quase todo o custo da troca.'
        : PROTO.adapt === 1 ? 'O primeiro alvo de cada bloco serve para acostumar e fica de fora.' : `Os ${PROTO.adapt} primeiros alvos de cada bloco servem para acostumar e ficam de fora.`);
  }

  function atualizarSetup() {
    const c = lerCfg();
    PROTO = protoDe(c.duracao);
    explicarProtocolo();
    $('tempo-info').textContent = `Leva uns ${Math.round(minutosPrevistos(PROTO.duelosPorRodada, PROTO.adapt, PROTO.aquec))} minutos: ` +
      `${PROTO.aquec ? PROTO.aquec + ' de aquecimento e ' : ''}${PROTO.rodadas} rodadas com ${PROTO.duelosPorRodada.join(', ')} alvos por bloco.`;
    $('setup-info').textContent = c.ok
      ? `cm/360: ${num(cm360(c.sens, c.dpi), 1)} · eDPI: ${Math.round(c.sens * c.dpi)} · 1ª rodada: ${fmt3(c.sens / Math.exp(PROTO.W0 / 2))} contra ${fmt3(c.sens * Math.exp(PROTO.W0 / 2))}, depois a faixa vai afinando (${PROTO.Ws ? listaFaixas(PROTO, PROTO.rodadas).slice(1).join(', ') : '×' + num(PROTO.rho, 4) + ' por rodada'})`
      : 'Confere o DPI e a sens.';
    $('btn-comecar').disabled = !c.ok;
  }

  function montarInicio() {
    $('duracao').innerHTML = Object.entries(DURACOES).map(([k, d]) => `<option value="${k}">${d.nome}</option>`).join('');
    $('duracao').value = DURACOES[dados.cfg.duracao] ? dados.cfg.duracao : DURACAO_PADRAO;
    $('dpi').value = dados.cfg.dpi;
    $('sens').value = fmt3(dados.cfg.sens);
    $('formato').value = dados.cfg.formato;
    ['dpi', 'sens', 'formato', 'duracao'].forEach((id) => $(id).addEventListener('input', atualizarSetup));
    atualizarSetup();
    const f = P.fonte;
    const cabOficial = window.BONECO && window.BONECO.formas.find((x) => x.nome === 'cabeca');
    $('fonte-info').textContent = `${f.duelos} duelos de ${f.demos} demos (${f.periodo[0].split('-').reverse().join('/')} a ${f.periodo[1].split('-').reverse().join('/')}). ` +
      (cabOficial
        ? `Boneco com as hitboxes oficiais do CS2 (agente FBI), na postura medida em ${window.BONECO.balas_medidas || 'milhares de'} acertos das tuas demos (pernas até ${num(window.BONECO.fim_da_barriga_sobre_o_pe || 28.7, 0)}, barriga até ${num(window.BONECO.barriga_peito_sobre_o_pe || 46, 0)}, depois peito). Cabeça = esfera de ${num(2 * cabOficial.r, 1)} de diâmetro; a medida pelos ${P.cabeca.n_tiros} tiros teus deu ${num(2 * P.cabeca.meia_largura, 1)} de largura. Dano da AK de verdade, com o boneco de colete e capacete.`
        : `Cabeça medida em ${P.cabeca.n_tiros} tiros: ${num(2 * P.cabeca.meia_largura, 1)} de largura por ${num(2 * P.cabeca.meia_altura, 1)} de altura (unidades do CS2).`);
    let h = '<tr><th>Situação</th><th>O que é</th><th class="num">Aparece</th><th class="num">Peso</th><th style="width:28%"></th></tr>';
    const maxP = Math.max(...P.estratos.map((e) => e.peso));
    for (const e of P.estratos) {
      h += `<tr><td>${e.nome}</td><td class="fraco">${e.desc}</td><td class="num">${pct(e.freq)}</td>
        <td class="num"><b>${pct(e.peso)}</b><div class="info">${pct(e.peso_ic[0], 0)}–${pct(e.peso_ic[1], 0)}</div></td>
        <td><div class="barra" style="width:${(100 * e.peso / maxP).toFixed(1)}%"></div></td></tr>`;
    }
    $('tab-pesos').innerHTML = h;
    const s = dados.sessao;
    if (s && !s.feito && s.data === hoje() && s.atual > 0 && s.versao === 'psa') {
      $('retomar').classList.remove('oculto');
      $('retomar-txt').textContent = `Começou às ${new Date(s.inicio).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })} com sens ${fmt3(s.sens0)}. Faltam ${s.blocos.filter((b) => b.tipo === 'aquec').length + totalMedidos(s) - s.atual} blocos.`;
    } else if (s && !s.feito) {
      dados.sessao = null;
      salvar();
    }
    if (s && s.feito && s.resultado && !s.resultado.erro) {
      const r = s.resultado;
      $('ultimo').classList.remove('oculto');
      $('ultimo-txt').innerHTML = `${s.data.split('-').reverse().join('/')} · começou em ${fmt3(s.sens0)} · sens do dia <b>${fmt3(r.sensDia)}</b> (faixa ${fmt3(r.ic[0])} a ${fmt3(r.ic[1])})`;
    }
    montarHistorico();
  }

  function montarHistorico() {
    const hs = dados.historico || [];
    if (!hs.length) return;
    $('historico').classList.remove('oculto');
    let h = '<tr><th>Dia</th><th class="num">Sens de partida</th><th class="num">Sens do dia</th><th class="num">Faixa 95%</th><th class="num">Rodadas</th></tr>';
    for (const r of hs.slice().reverse().slice(0, 30)) {
      if (!r.ic) continue;
      h += `<tr><td>${r.data.split('-').reverse().join('/')}</td><td class="num">${fmt3(r.sens0)}</td><td class="num"><b>${fmt3(r.sensDia)}</b></td>
        <td class="num">${fmt3(r.ic[0])}–${fmt3(r.ic[1])}</td><td class="num">${r.rodadas || 'grade antiga'}</td></tr>`;
    }
    $('tab-hist').innerHTML = h;
  }

  // ---------- teste ----------
  function mostrar(tela) {
    ['inicio', 'teste', 'resultado'].forEach((id) => $(id).classList.toggle('oculto', id !== tela));
  }

  let esperandoEspaco = null;
  function pausa(titulo, txt, acao, aoContinuar) {
    $('pausa-titulo').textContent = titulo;
    $('pausa-txt').innerHTML = txt;
    $('pausa-acao').innerHTML = acao;
    $('pausa').classList.remove('oculto');
    esperandoEspaco = aoContinuar;
  }
  function tirarPausa() { $('pausa').classList.add('oculto'); esperandoEspaco = null; }

  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && esperandoEspaco && Jogo.estado().travado) {
      e.preventDefault();
      const f = esperandoEspaco;
      tirarPausa();
      f();
    }
  });
  $('pausa').addEventListener('click', () => {
    if (!Jogo.estado().travado) Jogo.travar();
  });

  function aoPerderTrava() {
    pausa('Pausado', 'O alvo que estava na tela volta no fim do bloco.', 'Clica aqui para voltar e aperta <span class="tecla">Espaço</span>.', () => Jogo.continuar());
  }

  function proximoBloco() {
    const s = dados.sessao;
    if (s.atual >= s.blocos.length) {
      if (s.rodadas.length < s.rodadasAlvo) { planejarRodada(s); salvar(); } else { finalizar(); return; }
    }
    const bl = s.blocos[s.atual];
    if (!bl.plano.length) {           // bloco sem alvo (aquecimento zerado): pula
      bl.feito = true;
      s.atual++;
      salvar();
      proximoBloco();
      return;
    }
    const n = totalMedidos(s);
    const idx = s.blocos.slice(0, s.atual + 1).filter((b) => b.tipo === 'medida').length;   // numero do bloco medido
    const nAdapt = bl.plano.filter((p) => p.adapt).length;
    const titulo = bl.tipo === 'aquec' ? 'Aquecimento'
      : `Rodada ${bl.rodada} de ${s.rodadasAlvo} · bloco ${idx} de ${n}`;
    const sensBloco = s.sens0 * Math.exp(bl.x);
    const canto = `sens ${fmt3(sensBloco)} · ${num(cm360(sensBloco, s.dpi), 1)} cm/360`;
    const txt = bl.tipo === 'aquec'
      ? `${bl.plano.length} alvos na tua sens (${fmt3(sensBloco)}). Não conta para a nota.`
      : `Este bloco: <b>sens ${fmt3(sensBloco)}</b> (${num(cm360(sensBloco, s.dpi), 1)} cm/360). ` +
        (idx === 1 ? (nAdapt === 0 ? 'Todos os alvos do bloco contam.' : nAdapt === 1 ? 'O primeiro alvo de cada bloco serve para acostumar e não conta.' : `Os ${nAdapt} primeiros alvos de cada bloco servem para acostumar e não contam.`)
          : 'Solta o mouse, reposiciona, respira.');
    pausa(titulo, txt, 'Aperta <span class="tecla">Espaço</span> para começar' + (Jogo.estado().travado ? '' : ' (clica antes para travar o mouse)'), () => {
      Jogo.rodarBloco(bl.plano, { sens: sensBloco, rotulo: titulo, progresso: idx / n, canto }, (res) => {
        bl.duelos = res;
        bl.feito = true;
        s.atual++;
        if (Jogo.estado().semRaw) s.semRaw = true;
        salvar();
        proximoBloco();
      });
    });
  }

  async function comecar(continuar) {
    const c = lerCfg();
    if (!continuar) {
      if (!c.ok) return;
      dados.cfg = { dpi: c.dpi, sens: c.sens, formato: c.formato, duracao: c.duracao };
      PROTO = protoDe(c.duracao);
      dados.sessao = novaSessao(dados.cfg);
      salvar();
    }
    const s = dados.sessao;
    Jogo.formato(FORMATOS[s.formato] || FORMATOS.nativo);
    mostrar('teste');
    await Jogo.travar();
    proximoBloco();
  }

  function finalizar() {
    const s = dados.sessao;
    Jogo.parar();
    if (document.pointerLockElement) document.exitPointerLock();
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    s.feito = true;
    s.resultado = resumoParaSalvar(s);
    dados.historico = (dados.historico || []).filter((h) => h.id !== s.id);
    dados.historico.push(s.resultado);
    salvar();
    mostrarResultado(s);
  }

  function resumoParaSalvar(s) {
    const cam = Stats.caminho(s, pesos);
    return { id: s.id, data: s.data, sens0: s.sens0, dpi: s.dpi, rodadas: cam.rodadas.length,
      sensDia: s.sens0 * Math.exp(cam.final), ic: cam.faixa.map((x) => s.sens0 * Math.exp(x)), andou: cam.andou };
  }

  // ---------- resultado ----------
  function diagnostico(s) {
    const grupos = new Map();
    for (const bl of s.blocos) {
      if (bl.tipo !== 'medida' || !bl.feito) continue;
      const k = bl.x.toFixed(4);
      if (!grupos.has(k)) grupos.set(k, { x: bl.x, blocos: 0, ts: [], tiros: 0, mortes: 0, over: 0, flicks: 0, timeouts: 0, rts: [] });
      const g = grupos.get(k);
      g.blocos++;
      for (const d of bl.duelos) {
        if (d.adapt || d.slot < 0) continue;
        g.ts.push(d.t);
        g.tiros += d.tiros;
        if (!d.timeout) g.mortes++; else g.timeouts++;
        if (d.over) g.over++;
        if (d.theta0 > 2) g.flicks++;
        if (d.rt != null) g.rts.push(d.rt);
      }
    }
    return [...grupos.values()].sort((a, b) => a.x - b.x);
  }

  function grafico(s, res) {
    const W = 900, H = 330, m = { l: 56, r: 18, t: 18, b: 46 };
    const lo = res.lo - 0.06, hi = res.hi + 0.06;
    const f0 = Stats.curva(res.coef, 0);
    const perf = (S) => 100 * (Math.exp(f0 - S) - 1);
    const pts = res.xs.map((x, i) => ({ x, p: perf(res.S[i]), a: perf(res.S[i] + 1.96 * res.seG[i]), b: perf(res.S[i] - 1.96 * res.seG[i]) }));
    const curva = [];
    for (let i = 0; i <= 120; i++) { const x = res.lo + (res.hi - res.lo) * i / 120; curva.push({ x, p: perf(Stats.curva(res.coef, x)) }); }
    const ys = pts.flatMap((p) => [p.a, p.b]).concat(curva.map((c) => c.p)).filter(isFinite);
    let ymin = Math.min(...ys), ymax = Math.max(...ys);
    const pad = Math.max(1, (ymax - ymin) * 0.12);
    ymin -= pad; ymax += pad;
    const X = (x) => m.l + (x - lo) / (hi - lo) * (W - m.l - m.r);
    const Y = (y) => m.t + (ymax - y) / (ymax - ymin) * (H - m.t - m.b);
    let g = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Desempenho por sens">`;
    // faixa de 95% da sens do dia
    g += `<rect x="${X(res.ic[0])}" y="${m.t}" width="${Math.max(2, X(res.ic[1]) - X(res.ic[0]))}" height="${H - m.t - m.b}" fill="rgba(123,211,137,0.12)"/>`;
    // eixo y
    const passoY = (ymax - ymin) > 30 ? 10 : (ymax - ymin) > 12 ? 5 : 2;
    for (let y = Math.ceil(ymin / passoY) * passoY; y <= ymax; y += passoY) {
      g += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(y)}" y2="${Y(y)}" stroke="#2a2f3a" stroke-width="1"/>`;
      g += `<text x="${m.l - 8}" y="${Y(y) + 4}" text-anchor="end">${y > 0 ? '+' : ''}${y}%</text>`;
    }
    // linha da tua sens
    g += `<line x1="${X(0)}" x2="${X(0)}" y1="${m.t}" y2="${H - m.b}" stroke="#98a1ac" stroke-dasharray="4 4"/>`;
    // curva
    g += `<polyline fill="none" stroke="#7bd389" stroke-width="2.5" points="${curva.map((c) => `${X(c.x).toFixed(1)},${Y(c.p).toFixed(1)}`).join(' ')}"/>`;
    // pontos medidos
    for (const p of pts) {
      g += `<line x1="${X(p.x)}" x2="${X(p.x)}" y1="${Y(p.a)}" y2="${Y(p.b)}" stroke="#e7e9ec" stroke-width="1.5"/>`;
      g += `<circle cx="${X(p.x)}" cy="${Y(p.p)}" r="4.5" fill="#e7e9ec"/>`;
    }
    // sens do dia
    g += `<line x1="${X(res.xhat)}" x2="${X(res.xhat)}" y1="${m.t}" y2="${H - m.b}" stroke="#7bd389" stroke-width="2"/>`;
    // eixo x: sens testadas
    const vistos = new Set();
    for (const x of res.xs) {
      const k = fmt3(s.sens0 * Math.exp(x));
      if (vistos.has(k)) continue;
      vistos.add(k);
      g += `<text x="${X(x)}" y="${H - m.b + 18}" text-anchor="middle">${k}</text>`;
    }
    g += `<text x="${(m.l + W - m.r) / 2}" y="${H - 6}" text-anchor="middle">sens (escala log) · linha tracejada = tua sens de hoje · faixa verde = 95% da sens do dia</text>`;
    g += '</svg>';
    return g;
  }

  function exportar(s) {
    const blob = new Blob([JSON.stringify({ sessao: s, resultado: s.resultado }, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `sens-do-dia-${s.data}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // Tiros de um sens em "cabecas": x = sentido do movimento (direita = passou), y = de lado.
  function dispersao(g, rotulo) {
    const W = 250, C = 125, U = 26, lim = 4.6;
    const pts = g.pontos || [];
    let s = `<svg viewBox="0 0 ${W} ${W + 34}" width="250" role="img" aria-label="Tiros na sens ${rotulo}">`;
    s += `<rect x="0.5" y="0.5" width="${W - 1}" height="${W - 1}" fill="#12151b" stroke="#2a2f3a"/>`;
    s += `<line x1="0" x2="${W}" y1="${C}" y2="${C}" stroke="#262b35"/><line y1="0" y2="${W}" x1="${C}" x2="${C}" stroke="#262b35"/>`;
    for (const r of [2, 3, 4]) s += `<circle cx="${C}" cy="${C}" r="${r * U}" fill="none" stroke="#262b35"/>`;
    s += `<circle cx="${C}" cy="${C}" r="${U}" fill="rgba(123,211,137,0.08)" stroke="#7bd389" stroke-width="1.6"/>`;
    for (const p of pts) {
      const x = (C + Math.max(-lim, Math.min(lim, p.nu)) * U).toFixed(1);
      const y = (C + Math.max(-lim, Math.min(lim, p.nw)) * U).toFixed(1);
      s += p.hit ? `<circle cx="${x}" cy="${y}" r="2" fill="rgba(123,211,137,0.5)"/>`
        : p.corpo ? `<circle cx="${x}" cy="${y}" r="2.4" fill="rgba(242,177,52,0.85)"/>`
          : `<circle cx="${x}" cy="${y}" r="2.7" fill="rgba(239,107,107,0.9)"/>`;
    }
    s += `<text x="6" y="${C - 6}">curto</text><text x="${W - 6}" y="${C - 6}" text-anchor="end">passou</text>`;
    s += `<text x="${W / 2}" y="${W + 16}" text-anchor="middle" style="fill:#e7e9ec;font-weight:700">sens ${rotulo}</text>`;
    const cab = pts.filter((p) => p.hit).length, corpo = pts.filter((p) => p.corpo).length;
    s += `<text x="${W / 2}" y="${W + 30}" text-anchor="middle">${cab} cabeça · ${corpo} corpo · ${pts.length - cab - corpo} fora</text>`;
    return s + '</svg>';
  }

  // Regua das rodadas: cada linha e uma rodada (faixa, sondas A e B, a mais rapida em verde,
  // seta do centro andando). Embaixo, onde o centro parou e o ruido do metodo.
  function regua(s, cam) {
    const R = cam.rodadas;
    const W = 900, esq = 210, dir = 24, alt = 50, topo = 30;
    const H = topo + alt * R.length + 70;
    const xs = R.flatMap((r) => [r.a, r.b]).concat([cam.faixa[0], cam.faixa[1], 0, cam.final]);
    const lo = Math.min(...xs) - 0.04, hi = Math.max(...xs) + 0.04;
    const X = (x) => esq + (x - lo) / (hi - lo) * (W - esq - dir);
    const sv = (x) => fmt3(s.sens0 * Math.exp(x));
    let g = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Rodadas afinando a faixa">`;
    g += '<defs><marker id="seta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#f2b134"/></marker></defs>';
    g += `<line x1="${X(0)}" x2="${X(0)}" y1="${topo - 14}" y2="${H - 40}" stroke="#98a1ac" stroke-dasharray="4 4"/>`;
    g += `<text x="${X(0)}" y="${topo - 18}" text-anchor="middle">tua sens ${sv(0)}</text>`;
    R.forEach((r, i) => {
      const y = topo + 22 + i * alt;
      const aGanha = r.delta > 0;
      g += `<text x="8" y="${y + 4}" style="fill:#e7e9ec;font-weight:700">Rodada ${r.n}</text>`;
      g += `<text x="88" y="${y + 4}">${r.veredito}</text>`;
      g += `<line x1="${X(r.a)}" x2="${X(r.b)}" y1="${y}" y2="${y}" stroke="#2f3541" stroke-width="12" stroke-linecap="round"/>`;
      g += `<circle cx="${X(r.a)}" cy="${y}" r="7" fill="${aGanha ? '#7bd389' : '#5b6370'}"/>`;
      g += `<circle cx="${X(r.b)}" cy="${y}" r="7" fill="${aGanha ? '#5b6370' : '#7bd389'}"/>`;
      g += `<text x="${X(r.a)}" y="${y + 24}" text-anchor="middle">${sv(r.a)}</text>`;
      g += `<text x="${X(r.b)}" y="${y + 24}" text-anchor="middle">${sv(r.b)}</text>`;
      if (Math.abs(X(r.centroNovo) - X(r.centro)) > 3) {
        g += `<line x1="${X(r.centro)}" x2="${X(r.centroNovo)}" y1="${y}" y2="${y}" stroke="#f2b134" stroke-width="2.5" marker-end="url(#seta)"/>`;
      } else {
        g += `<circle cx="${X(r.centro)}" cy="${y}" r="3" fill="#f2b134"/>`;
      }
    });
    const yf = topo + 22 + R.length * alt + 6;
    g += `<text x="8" y="${yf + 4}" style="fill:#e7e9ec;font-weight:700">Sens do dia</text>`;
    g += `<rect x="${X(cam.faixa[0])}" y="${yf - 9}" width="${Math.max(2, X(cam.faixa[1]) - X(cam.faixa[0]))}" height="18" rx="9" fill="rgba(123,211,137,0.18)"/>`;
    g += `<line x1="${X(cam.final)}" x2="${X(cam.final)}" y1="${yf - 13}" y2="${yf + 13}" stroke="#7bd389" stroke-width="3"/>`;
    g += `<text x="${X(cam.final)}" y="${yf + 30}" text-anchor="middle" style="fill:#7bd389;font-weight:700">${sv(cam.final)}</text>`;
    g += `<text x="${X(cam.faixa[0])}" y="${yf + 30}" text-anchor="middle">${sv(cam.faixa[0])}</text>`;
    g += `<text x="${X(cam.faixa[1])}" y="${yf + 30}" text-anchor="middle">${sv(cam.faixa[1])}</text>`;
    return g + '</svg>';
  }

  function mostrarResultado(s) {
    mostrar('resultado');
    const el = $('resultado');
    const psa = Array.isArray(s.rodadas);
    // teste antigo (grade): curva com bootstrap; PSA: so o caminho e as comparacoes pareadas
    const res = psa ? { faixas: Stats.inclinacoesPareadas(s) } : Stats.analisar(s, pesos, { B: 800 });
    if (!psa && res.erro) {
      el.innerHTML = `<h1>Não deu para calcular</h1><p>${res.erro}</p><div class="linha-botoes"><button id="btn-voltar">Voltar</button></div>`;
      $('btn-voltar').onclick = () => location.reload();
      return;
    }
    const cam = psa ? Stats.caminho(s, pesos) : null;
    const xDia = psa ? cam.final : res.xhat;
    const faixaX = psa ? cam.faixa : res.ic;
    const sensDia = s.sens0 * Math.exp(xDia);
    const ic = faixaX.map((x) => s.sens0 * Math.exp(x));
    const andouPct = Math.exp(xDia) - 1;
    const ganhoTxt = psa
      ? (cam.andou
        ? `Andou <b>${andouPct > 0 ? '+' : ''}${pct(andouPct)}</b> desde a tua sens de partida (${fmt3(s.sens0)}), mais do que o puro acaso consegue mover o centro (±${pct(Math.exp(1.96 * cam.sigmaCaminho) - 1, 0)}).`
        : `Andou ${andouPct > 0 ? '+' : ''}${pct(andouPct)} desde a tua sens de partida (${fmt3(s.sens0)}), dentro do que o puro acaso consegue mover o centro (±${pct(Math.exp(1.96 * cam.sigmaCaminho) - 1, 0)}): hoje a tua sens de partida rende igual.`)
      : 'Teste feito na versão antiga (grade com parábola).';
    const semRaw = (s.semRaw ? '<div class="aviso">O navegador não liberou o raw input: o movimento passou pelo Windows. Deixa "Aumentar precisão do ponteiro" desligado e a velocidade do ponteiro no 6/11.</div>' : '')
      + (estadoSalvar === 'enxuto' ? '<div class="aviso">O navegador ficou sem espaço: o teste foi salvo sem a trajetória da mira quadro a quadro (a sens do dia não muda). Exporta o JSON agora para guardar tudo.</div>' : '')
      + (estadoSalvar === 'falhou' ? '<div class="aviso">Não deu para salvar este teste no navegador. Exporta o JSON agora, senão ele some quando fechar a página.</div>' : '');
    let rodadasHtml = '';
    if (psa) {
      let tr = `<tr><th>Rodada</th><th class="num">A (sens)</th><th class="num">B (sens)</th><th class="num">Tempo A</th><th class="num">Tempo B</th>
        <th class="num">Diferença</th><th class="num">MDE</th><th class="num">Força</th><th>Veredito</th><th class="num">Centro</th></tr>`;
      for (const r of cam.rodadas) {
        const dif = Math.exp(r.delta) - 1;
        tr += `<tr><td>${r.n}${r.duelos ? `<div class="info">${r.duelos} duelos/bloco</div>` : ''}</td><td class="num">${fmt3(s.sens0 * Math.exp(r.a))}</td><td class="num">${fmt3(s.sens0 * Math.exp(r.b))}</td>
          <td class="num">${num(r.tempoA * 1000, 0)} ms</td><td class="num">${num(r.tempoB * 1000, 0)} ms</td>
          <td class="num">${dif > 0 ? 'A ' + pct(dif) + ' mais rápida' : 'B ' + pct(-dif / (1 + dif)) + ' mais rápida'}</td>
          <td class="num">±${pct(Math.exp(r.mde) - 1)}</td><td class="num">${num(r.w, 2)}</td><td>${r.veredito}</td>
          <td class="num">${fmt3(s.sens0 * Math.exp(r.centro))} → <b>${fmt3(s.sens0 * Math.exp(r.centroNovo))}</b></td></tr>`;
      }
      const ru = Stats.ruidoDoDia(s, pesos);
      rodadasHtml = `
      <h2>Rodadas afinando</h2>
      <div class="painel">${regua(s, cam)}
        <p class="info">Cada linha é uma rodada: as duas pontas da faixa jogadas em A B B A (ou B A A B), a que rendeu mais em verde. A seta laranja é quanto o centro andou: <b>força × ${psaDa(s).ks ? 'o passo da rodada (' + psaDa(s).ks.map(numx).join('; ') + ')' : num(psaDa(s).k, 4)} da faixa</b>, e a força é a diferença dividida por ${psaDa(s).gama === 1 ? 'MDE' : numx(psaDa(s).gama) + ' × MDE'} (MDE = o menor tamanho que separa do acaso com 95%), entre −1 e 1. ${psaDa(s).Ws ? 'A faixa de cada rodada vem do protocolo (' + listaFaixas(psaDa(s), psaDa(s).Ws.length).join(', ') + ').' : 'Depois a faixa é multiplicada por ' + num(psaDa(s).rho, 4) + '.'} Nenhum resultado é jogado fora: rodada empatada mexe pouco, rodada decidida mexe muito.</p>
      </div>
      <div class="painel" style="margin-top:12px;overflow-x:auto"><table>${tr}</table>
        <p class="info" style="margin-top:8px">Diferença e MDE em tempo até matar, com o peso de cada situação. O ruído é medido no próprio dia (as duas vezes que cada sonda foi jogada em cada rodada): ${num(100 * ru.sigma, 1)}% por bloco, com ${ru.gl} graus de liberdade (${ru.medidos} pares medidos + ${ru.gl0} de partida). Ruído do método = até onde o puro acaso levaria o centro, somando as rodadas.</p></div>`;
    }

    // tabela por situacao
    let tf = '<tr><th>Situação</th><th class="num">Peso</th><th class="num">Efeito de +10% de sens no tempo</th><th>Hoje pede</th></tr>';
    for (const e of P.estratos) {
      const fx = res.faixas && res.faixas[e.id];
      if (!fx) continue;
      const ef = Math.exp(fx.inclinacao * Math.log(1.1)) - 1;
      const efA = Math.exp(fx.ic[0] * Math.log(1.1)) - 1, efB = Math.exp(fx.ic[1] * Math.log(1.1)) - 1;
      let chip = '<span class="chip neutro">tanto faz (dentro do ruído)</span>';
      if (fx.ic[0] > 0) chip = '<span class="chip baixo">sens mais baixa</span>';
      if (fx.ic[1] < 0) chip = '<span class="chip cima">sens mais alta</span>';
      const qtd = fx.pares != null ? `${fx.situacoes} situações, ${fx.pares} pares A×B` : `${fx.situacoes} situações no deck`;
      tf += `<tr><td>${e.nome}<div class="info">${qtd}</div></td><td class="num">${pct(e.peso)}</td>
        <td class="num">${ef > 0 ? '+' : ''}${pct(ef)}<div class="info">${pct(efA)} a ${pct(efB)}</div></td><td>${chip}</td></tr>`;
    }

    // diagnostico por sens: tempo, acerto e onde a mira errou (x, y de cada tiro)
    const dg = diagnostico(s);
    const er = Erros.porSens(s);
    const erPorX = new Map(er.map((g) => [g.x.toFixed(4), g]));
    const p0 = (a, n) => (n ? Math.round(100 * a / n) + '%' : '–');
    let td = `<tr><th class="num">Sens</th><th class="num">cm/360</th><th class="num">Tempo mediano</th><th class="num">Tiros fora por kill</th>
      <th class="num">Kill de cabeça</th><th class="num">Flick na cabeça</th><th class="num">Passou</th><th class="num">Curto</th><th class="num">Correções por flick</th>
      <th class="num">Reação · flick · ajuste</th><th class="num">Perdidos</th></tr>`;
    for (const g of dg) {
      const sv = s.sens0 * Math.exp(g.x);
      const med = Stats.quantil(g.ts, 0.5);
      const e = erPorX.get(g.x.toFixed(4)) || {};
      td += `<tr><td class="num"><b>${fmt3(sv)}</b></td><td class="num">${num(cm360(sv, s.dpi), 1)}</td>
        <td class="num">${num(med * 1000, 0)} ms</td>
        <td class="num">${e.kills ? num(e.erros / e.kills, 2) : '–'}</td>
        <td class="num">${p0(e.hs, e.kills)}</td>
        <td class="num">${p0(e.cabeca, e.nFlick)}</td><td class="num">${p0(e.passou, e.nFlick)}</td><td class="num">${p0(e.curto, e.nFlick)}</td>
        <td class="num">${isFinite(e.corr) ? num(e.corr, 1) : '–'}</td>
        <td class="num">${[e.tReacao, e.tFlick, e.tAjuste].map((v) => (isFinite(v) ? Math.round(v) : '–')).join(' · ')} ms</td>
        <td class="num">${g.timeouts}</td></tr>`;
    }
    const temXY = er.some((g) => g.duelos.length > 0);
    const frases = temXY ? Erros.leitura(er, (x) => fmt3(s.sens0 * Math.exp(x)))
      : ['Esse teste foi gravado antes de o app guardar o x/y de cada tiro. O próximo já mostra onde e por que tu erra.'];
    // tres paineis de dispersao: menor sens, a mais perto da tua, maior sens
    const escolhidos = er.length && temXY ? [er[0], er.reduce((a, b) => (Math.abs(b.x) < Math.abs(a.x) ? b : a)), er[er.length - 1]] : [];
    const vistosX = new Set();
    const paineis = escolhidos.filter((g) => { const k = g.x.toFixed(4); if (vistosX.has(k)) return false; vistosX.add(k); return true; })
      .map((g) => dispersao(g, fmt3(s.sens0 * Math.exp(g.x)))).join('');
    const nDuelos = s.blocos.filter((b) => b.tipo === 'medida').reduce((a, b) => a + b.duelos.filter((d) => !d.adapt).length, 0);
    el.innerHTML = `
      <h1>Sens do dia</h1>
      <p class="fraco">${s.data.split('-').reverse().join('/')} · ${nDuelos} duelos medidos · ${FORMATOS[s.formato] ? FORMATOS[s.formato].nome : s.formato} · ${s.dpi} DPI</p>
      <div class="painel" style="margin-top:16px">
        <div class="grade g2" style="align-items:center">
          <div>
            <div class="grande">${fmt3(sensDia)}</div>
            <p class="fraco" style="margin-top:8px">cm/360: ${num(cm360(sensDia, s.dpi), 1)} · eDPI: ${Math.round(sensDia * s.dpi)}${psa ? ` · ${cam.rodadas.length} rodadas` : ''}</p>
            <p>${psa ? 'Ruído do método (95%)' : 'Faixa de 95%'}: <b>${fmt3(ic[0])}</b> a <b>${fmt3(ic[1])}</b></p>
          </div>
          <div>
            <p>No console do CS2:</p>
            <p><code id="cmd">sensitivity ${fmt3(sensDia)}</code> <button id="btn-copiar">Copiar</button></p>
            <p class="info">${ganhoTxt}</p>
          </div>
        </div>
      </div>
      ${semRaw}
      ${psa ? rodadasHtml : `<h2>Desempenho por sens</h2><div class="painel">${grafico(s, res)}</div>`}
      <h2>Cada situação, hoje</h2>
      <div class="painel"><table>${tf}</table>
        <p class="info" style="margin-top:8px">Efeito positivo: com 10% a mais de sens tu demora mais nessa situação, então ela puxa a sens para baixo. Só entram comparações pareadas: a mesma situação jogada nas duas pontas da mesma rodada. A sens do dia é o melhor ponto da soma de todas, cada uma com o seu peso.</p></div>
      <h2>Onde e por que tu erra</h2>
      <div class="painel">
        ${frases.map((f) => `<p>${f}</p>`).join('')}
        <div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:12px">${paineis}</div>
        <p class="info" style="margin-top:8px">Cada ponto é um tiro nos duelos com flick (alvo a mais de 2 cabeças da mira), medido em cabeças: o círculo é a borda da hitbox da cabeça. Para a direita = a mira passou da cabeça no sentido do movimento (sens rápida para aquele movimento); para a esquerda = ficou curta; para cima e para baixo = errou de lado. Verde = cabeça, amarelo = pegou no corpo (dano de AK com colete), vermelho = não pegou no boneco.</p>
      </div>
      <h2>Detalhe por sens</h2>
      <div class="painel" style="overflow-x:auto"><table>${td}</table>
        <p class="info" style="margin-top:8px">Flick = o movimento principal até a primeira parada ou volta da mira, nos duelos que começam a mais de 2 cabeças. "Na cabeça" = a mira parou dentro da hitbox; "passou" = parou além dela (mais de 1 cabeça); "curto" = parou antes. Correções = novos movimentos depois do flick. Os tempos são medianas.</p></div>
      <div class="painel" style="margin-top:22px">
        <h3>Quer afinar mais?</h3>
        <p>Mais uma rodada (4 blocos de ${protocoloDa(s).duelosExtra} alvos, uns ${num(minutosPrevistos([protocoloDa(s).duelosExtra], protocoloDa(s).adapt, 0), 1)} minutos): as duas pontas de uma faixa ${psaDa(s).Ws ? 'do mesmo tamanho da última' : num(psaDa(s).rho, 3) + ' vezes a última'}, em volta de ${fmt3(sensDia)}. O resultado continua sendo só de hoje.</p>
        <div class="linha-botoes"><button id="btn-estender"${psa ? '' : ' disabled'}>Jogar mais uma rodada</button></div>
      </div>
      <div class="linha-botoes">
        <button class="principal" id="btn-voltar">Voltar ao início</button>
        <button id="btn-exportar">Exportar os dados de hoje (JSON)</button>
      </div>`;
    $('btn-voltar').onclick = () => location.reload();
    const btnE = $('btn-estender');
    if (btnE) {
      if (url.has('sim') || s.data !== hoje()) btnE.disabled = true;
      btnE.onclick = () => {
        estender(s);
        dados.sessao = s;
        salvar();
        comecar(true);
      };
    }
    $('btn-copiar').onclick = async () => {
      const t = $('cmd').textContent;
      try { await navigator.clipboard.writeText(t); } catch (e) {
        const i = document.createElement('textarea'); i.value = t; document.body.appendChild(i); i.select(); document.execCommand('copy'); i.remove();
      }
      $('btn-copiar').textContent = 'Copiado';
    };
    $('btn-exportar').onclick = () => exportar(s);
  }

  // ---------- simulacao (para conferir a matematica com resposta conhecida) ----------
  // ?sim=0.2 simula um jogador cujo melhor fica em sens x e^0.2 e mostra o resultado.
  // ?cobertura=200 roda 200 dias simulados e conta quantas vezes a faixa de 95% pega o certo.
  const MU = { fino: -1.25, curto: -0.95, flick: -0.75, medio: -0.45, virada: 0.05, rapido: -0.7 };
  function simularDuelo(it, x, alvo, r, efBloco, curv) {
    const e = it.e;
    const desloc = alvo.desloc ? (alvo.desloc[e] || 0) : 0;
    const gauss = () => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r());
    const y = MU[e] + curv[e] * Math.pow(x - alvo.x - desloc, 2) + efBloco + 0.38 * gauss();
    const t = Math.min(2.5, Math.exp(y));
    return { slot: it.slot, sit: it.sit, e, adapt: !!it.adapt, espelho: it.espelho, v: 0, t, timeout: t >= 2.5,
      tiros: 1 + Math.floor(r() * 2), rt: 0.2, over: false, theta0: 3 };
  }
  function simularSessao(alvo, semente) {
    const cfg = { dpi: 1600, sens: 0.5, formato: 'nativo' };
    const s = novaSessao(cfg, Math.imul(semente, 0x9e3779b1) ^ 0x5bd1e995);
    const r = Stats.rng(semente);
    const curv = { fino: 0.30, curto: 0.32, flick: 0.28, medio: 0.25, virada: 0.15, rapido: 0.25 };
    while (true) {
      if (s.atual >= s.blocos.length) { if (s.rodadas.length < s.rodadasAlvo) planejarRodada(s); else break; }
      const bl = s.blocos[s.atual];
      const ef = 0.04 * (Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r()));
      bl.duelos = bl.plano.map((it) => simularDuelo(it, bl.x, alvo, r, ef, curv));
      bl.feito = true;
      s.atual++;
    }
    s.feito = true;
    // verdade da mistura: argmin de soma W*curv*(x - x_h)^2
    let num_ = 0, den = 0;
    for (const e of Object.keys(pesos)) {
      const xh = alvo.x + (alvo.desloc ? (alvo.desloc[e] || 0) : 0);
      num_ += pesos[e] * curv[e] * xh; den += pesos[e] * curv[e];
    }
    return { s, verdade: num_ / den };
  }

  function rodarSimulacao() {
    if (url.has('sim')) {
      const x = parseFloat(url.get('sim')) || 0;
      const { s, verdade } = simularSessao({ x, desloc: { virada: 0.3, rapido: 0.2, fino: -0.1 } }, 99);
      const cam = Stats.caminho(s, pesos);
      console.log('simulacao: verdade', verdade, 'estimado', cam.final, 'faixa', cam.faixa);
      s.resultado = resumoParaSalvar(s);
      mostrarResultado(s);
      const nota = document.createElement('div');
      nota.className = 'aviso';
      nota.textContent = `SIMULAÇÃO: melhor de verdade em sens ${fmt3(0.5 * Math.exp(verdade))}; o PSA parou em ${fmt3(0.5 * Math.exp(cam.final))}; ruído do método ${fmt3(0.5 * Math.exp(cam.faixa[0]))} a ${fmt3(0.5 * Math.exp(cam.faixa[1]))}.`;
      $('resultado').prepend(nota);
      return true;
    }
    if (url.has('cobertura')) {
      const N = parseInt(url.get('cobertura'), 10) || 100;
      mostrar('resultado');
      const el = $('resultado');
      el.innerHTML = '<h1>Cobertura da faixa de 95%</h1><p id="cob">rodando…</p>';
      let pega = 0, erros = [], larg = [], feitos = 0;
      const r = Stats.rng(5);
      const passo = () => {
        for (let k = 0; k < 5 && feitos < N; k++, feitos++) {
          const x = (r() - 0.5) * 0.8;
          const { s, verdade } = simularSessao({ x, desloc: { virada: 0.3, rapido: 0.2, fino: -0.1 } }, 1000 + feitos);
          const cam = Stats.caminho(s, pesos);
          if (verdade >= cam.faixa[0] && verdade <= cam.faixa[1]) pega++;
          erros.push(cam.final - verdade);
          larg.push(cam.faixa[1] - cam.faixa[0]);
        }
        const rms = Math.sqrt(erros.reduce((a, b) => a + b * b, 0) / erros.length);
        $('cob').textContent = `${feitos}/${N} dias: a faixa pegou o certo em ${pct(pega / feitos)} · erro típico ${pct(Math.exp(rms) - 1)} na sens · largura mediana da faixa ×${num(Math.exp(Stats.quantil(larg, 0.5)), 2)}`;
        if (feitos < N) setTimeout(passo, 0);
        else console.log('cobertura', pega / feitos, 'rms', rms);
      };
      passo();
      return true;
    }
    return false;
  }

  // ---------- inicio ----------
  Jogo.iniciar({ gl: $('gl'), hud: $('hud'), perfil: P, aoPausar: aoPerderTrava });
  if (url.has('bot')) Jogo.ativarBot({ tolerancia: parseFloat(url.get('bot')) || 0.8 });
  if (!rodarSimulacao()) {
    montarInicio();
    $('btn-comecar').onclick = () => comecar(false);
    $('btn-continuar').onclick = () => comecar(true);
    $('btn-descartar').onclick = () => { dados.sessao = null; salvar(); location.reload(); };
    $('btn-ver-ultimo').onclick = () => mostrarResultado(dados.sessao);
    $('btn-exportar-ultimo').onclick = () => exportar(dados.sessao);
  }
})();
