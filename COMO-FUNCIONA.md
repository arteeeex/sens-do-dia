# Sens do Dia — como funciona

Versão de 01/11/2026. Tu joga uns 12 minutos e o app acha, com um **PSA afinando**, a sens com que tu mata mais rápido **hoje**. Cada situação de mira pesa pelo quanto ela decide duelo nas tuas partidas. Só entram dados do dia. Não mede mousepad: se uma virada pede remada, o tempo da remada entra no cronômetro do jeito que acontece no jogo.

**Convenção:** sens com ponto (`0.500`), como no console do CS2. O resto com vírgula.

---

## 1. Como usar

1. Dois cliques em **`Abrir Sens do Dia.cmd`** (abre no Brave; precisa de navegador Chromium para o raw input do mouse).
2. Confere o DPI, a tua sens de hoje, o formato da imagem do CS2 (nativo, 4:3 esticado etc.) e a **duração** (8, 12, 16, 20, 25 ou 35 min; padrão 12). Cada duração tem os seus números exatos (seção 5): mais tempo = sens um pouco mais certa.
3. **Começar.** Tela cheia, mouse travado, Esc pausa. A sens de cada bloco aparece no canto.
4. No fim: a sens do dia, o ruído do método, a régua das rodadas e o comando `sensitivity X` para copiar.
5. **"Jogar mais uma rodada"** afina mais (4 blocos com o tamanho da última rodada).
6. Na tela inicial, **"Último teste"** reabre o resultado e exporta os dados (JSON).

Demos novas? Baixa no CS2 (Assistir → Tuas partidas) e roda **`Atualizar pesos com as demos.cmd`**.

---

## 2. De onde vêm as situações e os pesos

### 2.1 Os duelos

`analise/extrair_duelos.py` lê as 15 demos de partida (10/08/2025 a 25/09/2026) e acha todos os teus duelos:

- **De frente:** o inimigo entra no teu campo de visão (`approximate_spotted_by`) e, nos 2,5 s seguintes, alguém acerta alguém ou tu atira passando a menos de 4° da cabeça dele.
- **Virada:** o inimigo te acerta sem estar no teu campo de visão (o "visto" do CS2 só marca quem está na tua frente). O duelo começa no tiro dele.

Ficam de fora faca, granada, AWP e scout (luneta é outra sens). Sobram **702 duelos**. De cada um sai: onde a tua mira estava em relação à cabeça dele, a altura da tua mira (pitch) no começo, a distância, como ele andou na tua tela (até 2,5 s a 32 quadros por segundo, já somando o teu próprio movimento) e os tempos de cada um.

**Caminho do alvo até o fim (revisão de 01/11/2026).** O caminho real acaba quando alguém morre: em 65% dos duelos isso acontece antes de 1,5 s (mediana 0,72 s). Antes, se tu demorasse mais que o duelo real, o boneco congelava e ficava mais fácil que no jogo. Agora, quando o caminho real acaba, o boneco segue com o movimento de **outro inimigo real das tuas demos que ainda estava vivo naquele mesmo instante**. O doador estava na mesma faixa de distância (inimigo de perto não anda como inimigo de longe) e se movia na velocidade mais parecida (mesmo tipo de duelo). O passo é emendado em unidades do jogo, de lado e de aproximação, e o alvo nunca chega mais perto que o duelo mais perto das demos (50 unidades). Se o doador também acaba, entra outro, até 2,5 s (mediana de 1 emenda por situação, no máximo 7). É determinístico: a mesma situação sempre anda igual, então A e B veem o mesmo alvo.

Conferência da emenda: a velocidade em unidades do jogo bate com a real (mediana 96 contra 103 u/s, 90% abaixo de 239 contra 253). Em graus por segundo o trecho emendado é um pouco mais rápido (mediana 8,8 contra 7°/s) só porque os duelos que acabam cedo são os de perto (650 contra 1.030 unidades), e de perto o mesmo passo vira mais graus. Na mediana a emenda nem aproxima o alvo (fica em 96% da distância); só 10 de 702 situações passam de 100 unidades por causa dela. Velocidade do alvo real na tela: mediana 7°/s, 90% abaixo de 21°/s, 99% abaixo de 58°/s.

### 2.2 As situações e os pesos

| Situação | Regra | Duelos | Aparece | **Peso** | IC 95% |
|---|---|---|---|---|---|
| Mira já em cima | cabeça a menos de 1,5° | 208 | 29,6% | **24,9%** | 18,8–30,8% |
| Ajuste curto | 1,5° a 4° | 179 | 25,5% | **26,8%** | 21,0–33,1% |
| Flick curto | 4° a 10° | 114 | 16,2% | **17,8%** | 11,5–23,0% |
| Flick médio | 10° a 35° | 68 | 9,7% | **12,0%** | 7,2–17,9% |
| Virada | 35° ou mais | 60 | 8,5% | **4,2%** | 2,2–8,1% |
| Alvo rápido | cruzando a 20°/s ou mais | 73 | 10,4% | **14,3%** | 9,7–19,3% |

Os cortes (1,5°, 4°, 10°, 35°, 20°/s) são só rótulos para agrupar duelos parecidos: cortes 25% menores mudariam a sens final em 0,44%, 33% maiores em 0,16%, e cortes em tamanhos de cabeça (lei de Fitts) em 0,84% (`analise/cortes_robustez.py`). Não há número exato a otimizar ali.

O peso mede **quanto 1% de tempo vale em duelos ganhos** naquela situação:

```
S(t) = chance de o inimigo ainda não ter te acertado no instante t
       (Kaplan-Meier PRÓPRIO de cada situação e tipo; censura quando tu matou antes ou ele sumiu)
f(t) = -dS/dt, suavizada (núcleo gaussiano; largura de Silverman, uma por tipo de duelo,
       calculada com todos os eventos daquele tipo: sem constante chutada)
valor do duelo i = f(t_i) × t_i        t_i = teu tempo até o primeiro dano nele
peso da situação = soma dos valores dela ÷ soma de todos
```

O intervalo vem de 1000 reamostragens dos duelos, refazendo o Kaplan-Meier em cada uma.

**Revisão de 01/11/2026:** antes havia um Kaplan-Meier só para todas as situações. Com um por situação, o "mira já em cima" caiu de 28,7% para 24,5%: com a mira já na cabeça, o inimigo quase sempre ainda não te viu e tu ganha de qualquer jeito. O "flick médio" subiu de 8,1% para 12,1%, porque nele o inimigo costuma ser rápido e cada milissegundo decide.

### 2.3 Os pesos aguentam erro? (`analise/pesos_robustez.py`)

Nenhum peso é 100% certo. O que dá para medir é quanto um erro nele mexe na sens. Calculei de quatro jeitos objetivos e sorteei 1000 vezes as demos:

| Jeito | fino | curto | flick | médio | virada | rápido |
|---|---|---|---|---|---|---|
| **A) atual: corrida pelo 1º dano, curva por situação** | **24,9** | **26,8** | **17,8** | **12,0** | **4,2** | **14,3** |
| B) corrida pela kill | 26,4 | 15,5 | 18,1 | 12,0 | 6,5 | 21,5 |
| C) curva do inimigo única | 28,7 | 30,5 | 16,8 | 8,1 | 3,5 | 12,4 |
| D) só frequência (média simples) | 29,6 | 25,5 | 16,2 | 9,7 | 8,5 | 10,4 |

Efeito na sens, supondo que o melhor ponto de cada situação varia 20% entre elas: trocar A por B muda a sens em **2,9%** (típico) e custa **0,023%** de desempenho. A incerteza do próprio A (1000 sorteios) mexe **1,15%** e custa 0,004%. O ruído do próprio teste (erro típico de 7,7% no desenho de 12 min) custa **~0,16%**, 7 a 40 vezes mais. Fica o A: a faixa de incerteza dele é pouco mais da metade da do B (10,2 contra 18,0 pontos), e nas tuas demos quem dá o primeiro dano ganha **76%** dos duelos decididos (87% quando és tu).

### 2.4 Cabeça, corpo e dano

**Hitboxes oficiais.** Extraídas da tua instalação com o Source 2 Viewer 20.1 (`agents/models/ctm_fbi`, grupo `physics_group_playerflesh`, 35 peças: cápsulas e esferas nas juntas). Script: `analise/hitboxes_cs2.py`. O boneco que aparece é essa hitbox, não o modelo visual: por isso parece um boneco de massinha e não o agente do jogo.

- **Cabeça: esfera de raio 5,0** (10 de diâmetro). A medida independente pelos 85 tiros na cabeça nas tuas demos (vítimas paradas) deu meia-largura **5,01**.
- **Postura do jogo medida nas demos** (`analise/medir_regioes.py` → `regioes.json`). O arquivo vem em pé reto e de braços abertos. Para achar a postura de jogo, peguei **4.901 balas** de todo mundo nas 15 demos que acertaram alguém em pé, sem atravessar parede. O ponto do acerto é o olho do atirador + a direção da bala × a distância percorrida, e a parte do corpo vem do `player_hurt`. A posição na demo tem um erro de ~4 unidades de altura (compensação de lag), então a fronteira entre duas partes sai por máxima verossimilhança com esse borrão no modelo:

| Fronteira (altura acima do pé) | Medida |
|---|---|
| pernas → barriga | **28,8** (os dois métodos dão 29,3 no jeito de medir das demos) |
| barriga → peito | **45,7** (45,0 pelo probit simples, 47,5 tirando o borrão; fica no meio. Só decide 3 ou 4 tiros a menos de ~16 m) |
| centro da cabeça | **62,3** (1,28 abaixo do olho em pé, 63,6) |

  As alturas das demos são medidas com o olho do atirador a 64,06; o app usa 63,6, por isso tudo desce ~0,5 na conversão. O ajuste sem borrão tem incerteza larga (±3 ou mais) porque só a altura não separa bem o borrão da forma da distribuição dos tiros. Por isso as duas medidas aparecem lado a lado.

  O boneco (`analise/boneco.py` → `app/boneco.js`) usa os raios oficiais. A barriga e a ponta de baixo do peito vão para essas alturas, e as pernas encolhem para 82% na vertical (joelho dobrado) até o quadril ficar no lugar medido. Os braços seguram a arma; braço leva o mesmo dano do peito com colete, então a posição exata dele não muda a conta. Antes eu tinha chutado pernas 30% mais curtas, o que deixava a barriga 5 unidades baixa demais. Prévias: `analise/boneco_frente.png` e `boneco_lado.png`.
- **Dano da AK-47** (`analise/medir_dano.py` → `dano.json`), conferido em 449 acertos de AK nas demos com a vítima de vida cheia. A conta do CS2 bate **exata em 85%**; o resto é bala atravessando parede:

```
dano = 36 × parte × 0,98^(distância ÷ 500)
parte: cabeça 4 · peito 1 · barriga 1,25 · braço 1 · perna 0,75 (pescoço conta como peito)
colete (peito, barriga, braço) e capacete (cabeça): a vida perde 77,5% do dano, arredondado para baixo
```

| Parte | Dano no boneco de colete e capacete | Tiros para matar |
|---|---|---|
| Cabeça | 104–111 | 1 (até ~69 m) |
| Peito, braço | 26–27 | 4 |
| Barriga | 32–34 | 3 até ~16 m, 4 depois |
| Perna (sem proteção) | 25–27 | 4 |

  O boneco vem **de colete e capacete** porque nos teus duelos de rifle 92% dos inimigos tinham colete e 84% capacete. Peito ou barriga sai da altura do acerto, pela fronteira medida. As duas cápsulas do tronco se cruzam e a de baixo é 0,04 mais grossa, então pela cápsula um tiro logo abaixo da cabeça viraria barriga, o que não bate com os acertos reais.
- **Sem recuo (spray).** É um tiro por clique, até 10 por segundo, e cada tiro vai onde a mira está. Nas tuas demos, depois do primeiro acerto no corpo a kill veio em **406 ms** (mediana; 297 a 500 ms). No teste, o mínimo é 300 ms (3 tiros a mais). Dá para comparar quando tu exportar um teste.

---

## 3. O teste

### 3.1 A conta do CS2

- Graus por contagem do mouse = sens × 0,022 (`m_yaw` e `m_pitch` padrão).
- FOV vertical fixo de 73,74° (tangente 0,75); horizontal pelo formato (106,26° no 16:9, 90° no 4:3; esticado = imagem 4:3 esticada na tela toda).
- Raw input (`requestPointerLock` com `unadjustedMovement`).

### 3.2 Um duelo

1. 450 ms depois da kill anterior, a mira vertical volta para a **altura que ela tinha no duelo real** (pitch do começo do duelo; mediana 0,4°, 90% entre −8° e +12°) e o boneco aparece **onde o inimigo apareceu**, em relação à tua mira, na mesma distância. Sem essa volta, a mira acumulava desvio: em média o inimigo aparece 1° acima da mira, e depois de centenas de alvos o duelo acontecia olhando para o céu (o bot de teste chegou a −83°).
2. Ele **se move como o inimigo se moveu** na tua tela, até 2,5 s (o real e, quando ele acaba, a emenda de 2.1).
3. Nas viradas aparece o indicador vermelho de dano e o som de tiro levado; alvo fora da tela ganha uma seta.
4. Um clique = um tiro de AK, no máximo 10 por segundo, sem recuo. Dano do CS2 com o boneco de colete e capacete (2.4): cabeça mata com 1 tiro, corpo com 3 ou 4. Acerto no corpo faz um som curto e o boneco pisca.
5. Nota do duelo = tempo até a kill. Passou de 2,5 s, conta como perdido com 2,5 s.

Cada situação aparece espelhada (esquerda ↔ direita) ao acaso, sorteado uma vez por rodada e **igual nos 4 blocos**, então A e B veem o mesmo alvo do mesmo lado. Nas demos o alvo aparece 50% de cada lado (49% nos flicks), então espelhar não muda a mistura.

### 3.3 O PSA do dia

| Parte | O que é |
|---|---|
| Duração | Tu escolhe na tela inicial (8, 12, 16, 20, 25 ou 35 minutos); cada uma tem os seus números exatos, saídos da otimização (seção 5). Padrão: 12 |
| Aquecimento | **0** (o ótimo exato: aquecer dentro do teste só gasta tempo; ver 5) |
| Rodada | Sondas nas **duas pontas** da faixa: A (de baixo) e B (de cima), 2 blocos cada, na ordem **A B B A** (rodadas ímpares) ou **B A A B** (pares) |
| Faixa | 1ª rodada: ÷e^(W0/2) a ×e^(W0/2) da tua sens; depois a faixa é multiplicada por ρ a cada rodada |
| Alvos por bloco | Um número exato por rodada; a rodada extra repete o tamanho da última |
| Bloco | **1** alvo de adaptação (fora da conta) + as situações da rodada, embaralhadas |
| Situações | Deck do tamanho do maior bloco, sorteado das tuas demos na proporção do peso; cada rodada usa um sorteio proporcional dele, **o mesmo nos 4 blocos**, então A e B se comparam nos mesmos duelos |

---

## 4. A conta

### 4.1 Nota de um bloco

```
nota = Σ_h  W_h × média, nas situações da faixa h, de ln(tempo até a kill)
       tempo limitado entre 0,05 s e 2,5 s;  W_h = peso da situação
```

O logaritmo faz cada duelo contar pelo **ganho relativo**, que é a escala do peso.

### 4.2 Uma rodada

```
Δ    = nota média de B − nota média de A          (> 0: A, a sens menor, foi mais rápida)
σ    = ruído de um bloco de 24, medido no dia:
       pares da mesma sonda na mesma rodada + GL0 graus de liberdade de partida em 0,088;
       blocos de outro tamanho entram na escala de 24 (o ruído cai com a raiz dos duelos)
erro = σ × √(24 ÷ duelos) × √(1/n_A + 1/n_B)
MDE  = t(97,5%, gl) × erro                          (menor diferença que separa do acaso)
w    = Δ ÷ (γ × MDE), limitado entre −1 e 1         (força da evidência)
centro novo = centro − w × k × faixa
faixa nova  = faixa × ρ
```

Os números k, ρ, γ, W0 e GL0 de cada duração estão na seção 5; cada teste guarda os seus, então um teste antigo é sempre recalculado com as regras com que foi jogado (os de antes desta revisão: k = ¼, ρ = ½, γ = 1, GL0 = 6, 36/36/24/12/12, 3 de adaptação, 20 de aquecimento).

Veredito: |w| ≥ 1 vence; ≥ 0,5 puxão forte; ≥ 0,2 puxão fraco; abaixo, empate (só rótulo). **Nada é jogado fora:** rodada empatada mexe pouco, rodada decidida mexe muito, e cada rodada parte de onde a anterior deixou.

### 4.3 Sens do dia e ruído do método

- **Sens do dia** = o centro depois da última rodada.
- **Ruído do método (95%)** = até onde o puro acaso levaria o centro: `±1,96 × √Σ (k × faixa_r ÷ (γ × t_r))²`. É o pior caso (curva plana), por isso é conservador.
- "Andou" = o centro saiu mais do que esse ruído desde a tua sens de partida.

### 4.4 O resto do resultado

- **Régua das rodadas:** cada rodada numa linha, a sonda que rendeu mais em verde, a seta do centro andando, e embaixo a sens do dia com o ruído do método.
- **Tabela das rodadas:** sens A e B, tempo da nota de cada uma, diferença, MDE, força, veredito, centro antes e depois.
- **Cada situação:** inclinação de ln(tempo) contra ln(sens) (o efeito de +10% de sens no tempo daquela situação), só com **pares**: a mesma situação jogada na ponta A e na ponta B da mesma rodada. Mínimos quadrados pela origem nos pares, intervalo pela t dos resíduos. Positivo = puxa para sens mais baixa. Antes a conta comparava sens de rodadas diferentes, e as rodadas 3 a 5 usam só parte das situações, então a diferença entre situações se misturava com o efeito da sens.
- **Onde e por que tu erra (x, y):** ver 4.5.

### 4.5 Onde e por que tu erra (x, y)

Cada quadro (no máximo um a cada 6 ms) guarda onde a mira está em relação ao centro da cabeça, em graus, e cada tiro guarda o x, y no instante do clique. `app/js/erros.js` divide o duelo em **reação** (até a mira andar), **flick** (até a primeira parada ou volta) e **ajuste** (até a kill). No fim do flick, medido em cabeças no sentido do movimento: **passou** (sens rápida para aquele movimento), **curto** (sens lenta ou remada), **de lado** ou **na cabeça**. As frases comparam a menor e a maior sens com teste de duas proporções. Conferido com trajetórias montadas com resposta conhecida.

---

## 5. Por que esse desenho (simulação)

### 5.1 Números exatos (revisão de 01/11/2026)

Os números agora saem de uma **otimização** (`analise/otimizar_exato.py`, `otimizar_adapt.py`, `otimizar_gl0.py`), e não de uma grade de números redondos:

- **Modelo de um dia:** nota do bloco = curva(sens) + ruído; ruído = √(0,38² ÷ alvos + 0,04²) em ln(tempo), com cansaço (+10% no ruído do alvo e +0,02 no do bloco a cada 10 min de teste). O ruído verdadeiro de cada dia é sorteado entre ×0,5 e ×2 (log-uniforme), porque o teu ainda não foi medido. Três formatos de curva (pico, fundo chato com paredes, torta com perda 4× mais rápida na sens alta), melhor sens sorteada entre −40% e +40% da de partida. Tempo: 1,05 s por alvo (kill + 0,45 s de espera) e 6 s de pausa por bloco.
- **Objetivo:** perda média de desempenho (tempo até matar) por não estar na melhor sens.
- **Busca:** descida coordenada, um número de cada vez: alvos de cada rodada (inteiros, de 1 em 1, passando alvos de uma rodada para outra), número de rodadas, W0, k, ρ, γ e GL0, sem passar do tempo da duração. **Os mesmos sorteios para todos os desenhos comparados** (números aleatórios comuns), então a diferença entre dois desenhos sai quase sem ruído de simulação. Refino final com 100 a 200 mil dias por avaliação e conferência com sorteios novos.
- **Aquecimento e adaptação:** simulação duelo a duelo, com aquecimento e custo de troca de sens (25 cenários, de nenhum efeito até 25% mais lento).

**Números finais de cada duração** (`analise/otimo_orcamento_*_final.json`; perda conferida em 300 mil dias novos, com o ruído incerto; o desenho antigo dá 0,2797% nessa mesma conta):

| Duração | Alvos por bloco em cada rodada | Faixa inicial (W0) | Passo k | Encolhe ρ | γ | GL0 | Perda | Erro típico de sens |
|---|---|---|---|---|---|---|---|---|
| 8 min (7,97) | 18, 19, 24, 26 | ×3,7382 | 0,1950 | 0,9050 | 2,6125 | 16 | 0,2037% | 12,6% |
| **12 min (11,78)** | **21, 17, 20, 22, 24, 24** | **×3,7010** | **0,1275** | **0,9150** | **1,9000** | **16** | **0,1820%** | **12,1%** |
| 16 min (15,94) | 18, 18, 21, 23, 23, 24, 24, 23 | ×3,7758 | 0,1500 | 0,9200 | 2,6000 | 16 | 0,1701% | 11,8% |
| 20 min (19,96) | 16, 16, 20, 22, 23, 25, 25, 24, 24, 23 | ×3,7758 | 0,1350 | 0,9300 | 2,6000 | 17 | 0,1617% | 11,5% |
| 25 min (24,98) | 27, 19, 23, 25, 27, 27, 29, 28, 27, 26, 25 | ×3,7010 | 0,1200 | 0,9300 | 2,4375 | 17 | 0,1552% | 11,4% |
| 35 min (35,00) | 31, 20, 24, 27, 29, 30, 33, 31, 32, 31, 30, 28, 30, 30 | ×3,7758 | 0,1050 | 0,9350 | 2,5000 | 18 | 0,1479% | 11,2% |

Em todas: **aquecimento 0**, **1 alvo de adaptação** por bloco, rodada extra com o tamanho da última. W0 é a razão entre as duas pontas da 1ª rodada (×3,7010 = de ÷1,9238 a ×1,9238 da tua sens).

O que o ótimo ensina: **afinar devagar** (a faixa encolhe só 6–10% por rodada, não pela metade), **passo pequeno** e **exigir ~2 a 2,6 vezes a MDE** para dar o passo inteiro. Assim um bloco ruim no começo não leva o centro para longe sem volta: as rodadas seguintes corrigem. As sondas ficam longe do centro até o fim, de propósito: a diferença entre duas sens distantes é bem maior que o ruído, então cada rodada mede a direção com mais certeza, e o resultado é o centro, entre elas.

**Robustez** (`analise/robustez_desenho.py`, 100 mil dias por linha; perda média):

| Cenário | Desenho antigo | Ótimo de 12 min |
|---|---|---|
| modelo (com cansaço) | 0,2538% | 0,1687% |
| sem cansaço | 0,2353% | 0,1573% |
| curvas que o otimizador nunca viu (vira reta / fica íngreme longe do ótimo) | 0,4354% | 0,2753% |
| ruído ×0,5 / ×1,5 / ×2 | 0,1380% / 0,3903% / 0,5336% | 0,1250% / 0,2254% / 0,2897% |
| curva ×0,5 (mais plana) / ×2 (mais funda) | 0,2308% / 0,3507% | 0,1564% / 0,2677% |
| melhor sens até ±60% da de partida | 0,3965% | 0,2352% |

O de 12 min ganha do antigo em todos. No app (300 dias simulados com `?cobertura=300`): **erro típico de 7,9%** na sens (o antigo dava 10,8%), e o ruído do método pegou a sens certa em 97,7% dos dias.

**Aquecimento e adaptação** (`analise/otimizar_adapt.py`, duelo a duelo, 25 cenários): adaptação 0 a 3 empatam (0,1727–0,1730%), 1 é o mínimo; aquecimento só piora (0: 0,1727%, 20: 0,1764%, 60: 0,1799%), inclusive no pior cenário. Com 50% de lentidão no começo, 0 contra 20 fica em ±0,01 ponto (ajuda se tu esquenta devagar, atrapalha se esquenta rápido).

**Ruído de partida** (`analise/otimizar_gl0.py`, ruído de cada dia entre ×0,5 e ×2): GL0 10 já ganhava de 6 (0,1920% contra 0,1932%); no refino final, com tudo junto, o ótimo ficou em 16 a 18. O valor de partida 0,088 é o melhor.

**O que não sai da otimização:** o limite de 2,5 s por alvo (é a definição de duelo dos pesos; o teto muda a nota menos de 0,1%) e a espera de 450 ms entre alvos (para a simulação menor é sempre melhor; o limite é humano e tuas demos não têm casos para medir; ver seção 8).

### 5.2 Desenho antigo (histórico)

Simulação bloco a bloco: ruído de 0,38 em ln(tempo) por duelo e 0,04 por bloco, aquecimento e cansaço ao longo do teste, três formatos de curva (pico, fundo chato com paredes, torta com perda 4× mais rápida na sens alta). Scripts em `analise/`. Esta tabela levou ao desenho antigo (5 rodadas, 36/36/24/12/12, ½, ¼); a otimização exata de 5.1 achou um desenho melhor.

| Pergunta | Resultado | Decisão |
|---|---|---|
| Sondas a 25/75% da faixa ou nas pontas? | erro típico 18,4% × **11,8%** | pontas |
| Refazer uma curva no fim com todos os blocos? | parábola 17,2%, diferenças 16,2%, **passo-a-passo 11,8%** | passo-a-passo |
| Quantas rodadas? (blocos de 24) | 3: 14,2% · 5: 14,0% · 8: 14,1% | quase não muda: a informação está nas primeiras rodadas (cresce com o quadrado da distância entre as sondas) |
| 4 ou 8 blocos por rodada? | 4 (A B B A): 14,3% · 8: 14,5% | 4 |
| Onde pôr os duelos (mesmo tempo, 11,8 min)? | 24 em todas: perda 0,33% · **36, 36, 24, 12, 12: perda 0,27%** | mais duelos no começo; as duas últimas rodadas ficam curtas e põem jogo a ~3% da resposta |
| Quanto a faixa encolhe e o tamanho do passo? | ×0,5 com passo de ¼ da faixa é o melhor; passo maior piora (17–24%) | ×0,5, ¼ |
| Faixa inicial | ×2,5: 15,3% · **×3: 14,3%** · ×4: 16,2% | ×3 |
| Quantos alvos de aquecimento? (duelo a duelo, 50 cenários: tu até 20% mais lento no começo, sumindo em 15 a 100 alvos, e custo de 10–25% nos primeiros alvos depois de trocar de sens) | perda média: **20: 0,228%** · 40: 0,230% · 60: 0,232% · 100: 0,233% · sem efeito nenhum: 0,228% | 20. A 1ª rodada compara pontas tão longe (×3) que esquentar não troca o lado, e A B B A cancela a melhora em linha reta |
| Mais alvos de adaptação por bloco (6 em vez de 3)? | 0,228% · igual | 3 |
| Sortear a ordem da 1ª rodada, ou 8 blocos (A B B A B A A B) nas rodadas 1–2? | 0,234% · 0,224%, dentro do ruído da simulação, e 8 blocos custam +1,6 min | mantém A B B A / B A A B |
| Quantos alvos no total? (tudo multiplicado; `otimizar_psa.py tamanho`) | ×0,5 (7,6 min): 0,287% · ×0,75: 0,254% · **×1 (11,8 min): 0,236%** · ×1,5 (16 min): 0,222% · ×2 (20 min): 0,210% · ×3 (29 min): 0,206%. Com um pouco de cansaço (ruído crescendo com o tempo): ×1: 0,253% · ×1,5: 0,244% · ×2: 0,248% · ×3: 0,269% | ×1. Dobrar ganha 0,03 ponto e, com cansaço, piora. A perda que sobra (~0,2%) é do formato do método, não da quantidade de alvos |
| Uma 6ª rodada de 12? | 0,243% · igual | não |

No app completo (300 dias simulados): **erro típico de 10,8%**, ruído do método pegou a sens certa em 99,3% dos dias. A perda média de desempenho por não estar na sens ideal fica em ~0,3% do tempo até matar: nesse ponto o método está perto do teto. O que ainda dá ganho é o realismo do teste (seção 6).

---

## 6. O que falta (medido nas demos) e limitações

- **Spray com recuo: fora, por escolha.** O dano no corpo entrou (2.4), mas sem recuo os tiros seguintes vão exatos onde a mira está. Nas tuas demos, depois do primeiro acerto no corpo a kill levou 406 ms (mediana); no teste o mínimo é 300 ms. O recuo da AK por bala já está medido (`analise/medir_spray.py`) se um dia quiser pôr.
- **Dois inimigos em seguida:** 11% dos duelos tiveram outro inimigo a menos de 1 s (8% das kills). Cada duelo entra sozinho, com a posição real da mira em relação a ele; o que não entra é os dois na tela ao mesmo tempo.
- **Inimigo atrás de cobertura:** o boneco aparece inteiro. Nas tuas demos, 4% dos acertos foram na perna, porque tu mira alto, então esconder as pernas mudaria pouco.
- **Tu não anda** (sem contra-strafe nem peek). É habilidade de teclado, não de sens.
- **Curva torta:** se o desempenho cai mais rápido de um lado, o PSA puxa ~10% para o lado suave. Esse é o lado que custa menos (perda média 0,4%).
- **O navegador tem um pouco mais de atraso que o CS2.** Pesa igual em todas as sens.
- **Um dia só tem o ruído de um dia.** Em zona plana a sens do dia varia de um dia para o outro: isso é o resultado, não falha.
- **O peso supõe** que o duelo é de quem acerta primeiro (vale em 76% dos duelos decididos) e que o tempo do inimigo não depende do teu. Trocar pelo "quem mata primeiro" mexe a sens em 2,6% (2.3).

---

## 7. Arquivos

| Arquivo | O que é |
|---|---|
| `Abrir Sens do Dia.cmd` | Abre o app no Brave |
| `Atualizar pesos com as demos.cmd` | Refaz duelos, cabeça, alturas do corpo, boneco, pesos e caminhos dos alvos |
| `app/index.html`, `app/js/app.js` | Telas, protocolo do PSA, simulação (`?sim=0.25`, `?cobertura=300`, `?bot=1.4`) |
| `app/js/stats.js` | Nota do bloco, ruído do dia, rodada, caminho, ruído do método e efeito pareado por situação |
| `app/js/jogo.js` | Câmera, boneco, tiro e dano da AK por parte, mira, som, x/y (gancho de teste `Jogo._raio`) |
| `app/js/render.js` | Desenho por raio (WebGL2) |
| `app/js/erros.js` | Reação, flick, ajuste; passou, curto, de lado |
| `app/perfil.js` | Pesos e as 702 situações com caminho de 2,5 s e altura da mira (gerado) |
| `app/boneco.js` | Boneco com as hitboxes do CS2 na postura medida (gerado) |
| `analise/extrair_duelos.py`, `perfil.py`, `medir_cabeca.py` | Demos → duelos → pesos e caminhos; medida da cabeça |
| `analise/hitboxes_cs2.py`, `medir_regioes.py`, `boneco.py`, `ler_glb.py` | Hitboxes oficiais + alturas medidas → boneco |
| `analise/medir_dano.py` | Dano da AK por parte, colete e capacete nas demos (`dano.json`) |
| `analise/pesos_robustez.py` | Pesos de 4 jeitos e o efeito na sens |
| `analise/medir_spray.py`, `revisar_situacoes.py` | Spray, dois inimigos, pesos por situação |
| `analise/otimizar_exato.py` (`orcamento`, `polir`), `otimizar_adapt.py`, `otimizar_gl0.py`, `robustez_desenho.py` | Números exatos de cada duração e a robustez deles (`otimo_orcamento_*_final.json`) |
| `analise/medir_tempos.py`, `cortes_robustez.py`, `sensibilidade_extracao.py` | Limite por alvo e espera (demos), cortes das situações, números que definem um duelo |
| `analise/comparar_*.py`, `otimizar_psa.py` (`frente`, `aquecimento`, `tamanho`) | Simulações do desenho antigo (histórico) |
| Source 2 Viewer CLI 20.1 | Usado uma vez para tirar as hitboxes (resultado salvo em `analise/hitboxes_cs2.json`). A pasta `ferramentas/` foi apagada na limpeza; para re-extrair as hitboxes, baixar de novo do GitHub do ValveResourceFormat |

Os dados ficam no navegador (`localStorage`, chave `sens-do-dia/v1`). O histórico é só consulta. A mira é gravada no máximo a cada 6 ms (144 Hz grava todo quadro, 240 Hz um sim e um não): uma sessão inteira dá ~1,6 milhão de caracteres. Se o navegador ficar sem espaço, o app salva sem a trajetória quadro a quadro (a sens do dia não muda) e avisa no resultado para exportar o JSON.

---

## 8. Revisão do zero (01/11/2026): perguntas e respostas

| Pergunta | Resposta (com o dado) | Mudou algo? |
|---|---|---|
| As situações são os meus duelos de verdade? | Sim: 702 duelos das 15 demos, com ângulo, distância, altura da mira e caminho reais. Lado: 50% esquerda, 50% direita. Arma: 55% rifle, 25% pistola (a sens é a mesma para todas). Repetidos: 1 de 702 | não |
| O boneco anda na velocidade certa? | Anda o caminho real; quando ele acaba, emenda com outro inimigo real na mesma faixa de distância e velocidade. Velocidade em unidades bate (96 contra 103 u/s) | doador agora na mesma faixa de distância e nunca mais perto que 50 |
| A mira vertical fica realista o teste todo? | Agora sim: cada alvo nasce na altura de mira do duelo real (só 1,7% dos duelos com mira além de 30°) | sim (antes ia ~1° para cima por alvo) |
| Cabeça e corpo estão no lugar e no tamanho do jogo? | Hitbox oficial (cabeça raio 5, medida 5,01); alturas do corpo medidas em 4.901 acertos; dano da AK conferido em 449 acertos (85% exato) | não |
| E inimigo agachado? | 16% dos acertos. A cabeça já fica na altura certa (o duelo usa o olho real dele); só a perna dobrada não entra, e perna é 4% dos teus acertos | não (limitação) |
| Os pesos estão certos? | 4 jeitos objetivos + 1000 sorteios: a sens mexe no máximo ~2,6%, custando 0,02%; o ruído do teste custa 0,31% | não |
| Aquecimento de 20 basta? | 20 = 40 = 60 = 100 na simulação duelo a duelo | não |
| Quantos alvos por bloco? | Para aquele desenho, 36, 36, 24, 12, 12 estava no ponto (dobrar ganhava 0,03 ponto e com cansaço piorava). **Superado na segunda revisão**: otimizando o desenho inteiro, os números mudaram (abaixo e seção 5) | depois, sim |
| 2,5 s de limite e 450 ms entre alvos? | 2,5 s = janela dos duelos das demos. 450 ms pesa igual em todas as sens; 300 ms renderia só ~0,04 ponto e deixaria menos tempo para se preparar | não |
| A e B veem exatamente o mesmo alvo? | Agora sim: o lado (espelho) é sorteado uma vez por rodada e fica igual nos 4 blocos | sim |
| A tabela "cada situação, hoje" é justa? | Agora sim: só compara a mesma situação nas duas pontas da mesma rodada | sim |
| O teste cabe no navegador? | Sessão inteira ~1,6 milhão de caracteres; se faltar espaço salva sem a trajetória e avisa | sim |
| Teste inteiro funciona do começo ao fim? | Sessão completa com o bot (aquecimento, 20 blocos, 5 rodadas, resultado) a 144 e 240 Hz, sem erro | — |
| Deck fixo de 36 situações representa as 702? | O deck é estratificado pelo peso; o que sobra é a variação dentro de cada faixa (~1,7% na sens), pequena perto dos 11% do ruído do teste | não |
| O que fica de fora? | Recuo (escolha tua), dois inimigos na tela ao mesmo tempo, cobertura, perna dobrada do agachado. E o ruído real do teu teste: só sai quando tu exportar um JSON | — |

### Segunda revisão (números exatos)

| Pergunta | Resposta (com o dado) | Mudou algo? |
|---|---|---|
| Os números do protocolo (36, 36, 24, 12, 12; ½; ¼; ×3; 20; 3) eram os melhores? | Não: eram o melhor de uma grade grossa (múltiplos de 12, passos de 0,05). Otimizando tudo junto, um número de cada vez, com os mesmos sorteios para todos os desenhos, a perda no mesmo tempo caiu de 0,253% para ~0,17% (seção 5) | sim |
| Qual o melhor tamanho do teste? | Sem cansaço, mais alvos sempre ajudam; com cansaço, o ótimo fica perto de 33 min, mas cada minuto depois de 12 compra pouco (12→16 min: −0,011 ponto; 25→35: −0,003). O tamanho depende do tempo que tu topa: virou escolha na tela inicial, cada duração com os seus números exatos | sim |
| Aquecimento e adaptação? | Duelo a duelo, 25 cenários: aquecimento **0** (cada 20 alvos de aquecimento custam +0,004 ponto) e **1** alvo de adaptação por bloco (0 a 3 empatam). Com 50% de lentidão no começo, a diferença fica em ±0,01 ponto | sim |
| Quanto confiar no ruído de partida? | Com o ruído verdadeiro de cada dia sorteado entre ×0,5 e ×2, 10 graus de liberdade já ganhavam de 6 (0,1920% contra 0,1932%); otimizando junto com o resto, ficou em **16 a 18** conforme a duração. O valor 0,088 já era o melhor | sim |
| O otimizador sabia o meu ruído exato? | Não, e não devia supor: o refino final sorteia o ruído de cada dia entre ×0,5 e ×2 | sim |
| Limite de 2,5 s por alvo? | É a definição de duelo dos pesos. Nas demos, 5,8% do valor acontece depois de 2,5 s (tu demorou porque o inimigo se escondeu); no teste isso quase não acontece, e o teto muda a nota menos de 0,1% mesmo na sens mais baixa nas viradas | não |
| 450 ms entre alvos? | Para a simulação, menor é sempre melhor (só gasta tempo); o limite é humano (reação ao próximo alvo logo depois de terminar a ação). As demos têm só 8 duelos com inimigo aparecendo até 0,5 s depois de uma kill: não dá para medir em ti | não (espera teus dados) |
| Os cortes das situações importam? | 0,16% a 0,84% na sens (2.2) | não |
| Os números que definem um duelo nas demos importam? (tiro conta como "nele" a menos de 4° da cabeça; piscada do "visto" de até 4 ticks é o mesmo duelo; `analise/sensibilidade_extracao.py`) | 2° ou 8°: 688 ou 710 duelos, sens muda 0,19% / 0,29%. 2 ou 8 ticks: nada muda (0,00%) | não |
| A largura da suavização tinha número chutado? | Tinha (0,15 s fixo e piso de 0,03 s). Agora é Silverman, uma por tipo de duelo; pesos quase iguais, faixas mais estreitas | sim |
| Teste sem aquecimento funciona? | Não funcionava: um bloco de aquecimento vazio nunca terminava. Agora o bloco nem é criado, e bloco sem alvo é pulado; a contagem "bloco X de Y" também foi corrigida | sim |
