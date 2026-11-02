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

**Caminho do alvo até o fim (revisão de 01/11/2026).** O caminho real acaba quando alguém morre: em 65% dos duelos isso acontece antes de 1,5 s (mediana 0,72 s). Antes, se tu demorasse mais que o duelo real, o boneco congelava e ficava mais fácil que no jogo. Agora, quando o caminho real acaba, o boneco segue com o movimento de **outro inimigo real das tuas demos que ainda estava vivo naquele mesmo instante**. O doador estava na mesma faixa de distância (inimigo de perto não anda como inimigo de longe), no mesmo tipo de duelo, e é aquele cujo **próximo passo mais parece o último passo real do alvo** (em unidades por segundo), para a costura não aparecer. O passo é emendado em unidades do jogo, de lado e de aproximação, e o alvo nunca chega mais perto que o duelo mais perto das demos (50 unidades). Se o doador também acaba, entra outro, até 2,5 s (mediana de 1 emenda por situação, no máximo 8). É determinístico: a mesma situação sempre anda igual, então A e B veem o mesmo alvo.

Conferência da emenda: a velocidade em unidades do jogo bate com a real (mediana 93 contra 103 u/s, 90% abaixo de 244 contra 253). Em graus por segundo o trecho emendado é um pouco mais rápido (mediana 8,3 contra 7°/s) só porque os duelos que acabam cedo são os de perto (651 contra 1.032 unidades), e de perto o mesmo passo vira mais graus. Na mediana a emenda não aproxima o alvo (fica em 100% da distância); 15 de 702 situações passam de 100 unidades por causa dela e encostam no piso de 50 (o alvo para de chegar perto). Na costura, a velocidade pula 1,0°/s (mediana; entre duas amostras reais seguidas: 1,1). Velocidade do alvo real na tela: mediana 7°/s, 90% abaixo de 21°/s, 99% abaixo de 58°/s. No trecho emendado, 1,7% das amostras passam de 100°/s (no real, 0,25%), mas por faixa de distância a emenda anda igual ao real (de 300 a 600 unidades: mediana 11,6 e 99% abaixo de 47,7°/s, contra 12,2 e 47,9 no real; de 600 a 1.200: 6,4 / 31,0 contra 6,5 / 27,8): a diferença vem de os duelos que acabam cedo, e por isso ganham emenda, serem os de perto.

**O boneco é rápido demais? (quarta revisão, `analise/movimento_proprio.py`).** O caminho é o inimigo visto do teu olho, com os dois andando: entra o movimento do teu corpo (teclado), não o da tua mira. O caminho refeito das demos bate com o gravado (diferença máxima 0,0005°), e o app toca a 32 amostras por segundo, igual à gravação (demos de 64 ticks). Separando as duas partes:

| Velocidade na tela (°/s) | mediana | 90% | 99% |
|---|---|---|---|
| **Relativo (o que o app usa)** | 7,1 | 20,7 | 58,0 |
| Só o inimigo andando (teu olho parado onde estava) | 4,8 | 15,0 | 37,7 |
| Só tu andando | 4,4 | 14,3 | 43,9 |

No chão, o inimigo anda como no CS (mediana 91 u/s, 99% abaixo de 248; correndo é 250). Mas em 47% dos teus duelos mais da metade do movimento na tela era teu, e no teste tu fica parado: o teu passo vira o passo do boneco, que parece 1,5× mais rápido que o inimigo. Ficou o relativo porque o teu próprio movimento deixa os duelos mais lentos de verdade: nos 316 duelos de frente com o teu primeiro dano, dobrar a velocidade que vem de ti aumenta o teu tempo em ~19% (coeficiente +0,246 ± 0,059 em ln(tempo) por ln(velocidade), t = 4,2), mais que dobrar a do inimigo, ~13% (+0,176 ± 0,067, t = 2,6), com ângulo e distância fixos; e o relativo explica o teu tempo melhor que só o inimigo (R² 0,153 contra 0,145). Tu quase sempre para antes de atirar (mediana de 49 u/s no primeiro tiro; abaixo de 85 u/s em 75% dos duelos), e o caminho também tem essa parada. No jogo, quando tu anda, o mundo inteiro desliza; aqui só o boneco se mexe, por isso parece mais rápido.

**Concorrentes da continuação (terceira revisão, `analise/concorrentes_caminho.py`).** Corta os caminhos reais dos inimigos que ficaram vivos os 2,5 s (199 caminhos, cortes de 0,25 a 1,5 s), esconde o resto e deixa cada método continuar por 0,75 s. O que conta é o jeito do movimento (a dificuldade), não acertar o ponto: compara com o futuro de verdade pela distância de Kolmogorov-Smirnov (0 = igual, 1 = nada a ver) em velocidade na tela, deslocamento em 0,5 s, tranco (mudança de velocidade entre amostras: o zigue-zague) e salto de velocidade na costura.

| Método | Velocidade | Deslocamento | Tranco | Salto | **Média** |
|---|---|---|---|---|---|
| **Emenda casando o próximo passo (atual)** | 0,063 | 0,103 | 0,020 | 0,100 | **0,071** |
| Emenda casando o próximo passo e a velocidade média | 0,065 | 0,098 | 0,057 | 0,090 | 0,077 |
| Emenda misturando o passo nas 2 primeiras amostras | 0,063 | 0,095 | 0,016 | 0,144 | 0,080 |
| Emenda antiga (velocidade média dos 2 últimos passos) | 0,065 | 0,090 | 0,023 | 0,268 | 0,112 |
| Mistura de 4 / 8 amostras | — | — | — | — | 0,126 / 0,177 |
| Processo aleatório que volta a zero (OU, ajustado nos caminhos) | 0,079 | 0,077 | 0,326 | 0,363 | 0,211 |
| Doador sorteado (sem casar o movimento) | 0,056 | 0,087 | 0,023 | 0,752 | 0,230 |
| Segue com a velocidade caindo (melhor meia-vida: 1 s) | 0,143 | 0,037 | 0,705 | 0,250 | 0,284 |
| Congela | 0,995 | 1,000 | 0,995 | 0,644 | 0,909 |

Sorteando os caminhos 300 vezes, a emenda nova ganha da antiga em 100% dos sorteios (diferença de 0,021 a 0,060); as duas seguintes empatam com ela dentro do sorteio e ficam atrás na média. Quem só segue a velocidade acerta melhor o ponto, mas anda liso demais (sem zigue-zague): fica fácil. Para a distância (`concorrentes_radial.py`, 1.449 cortes, entrando os alvos de perto), chegar perto **em unidades** (atual) ganha de chegar perto **em proporção** em 99% dos sorteios, inclusive abaixo de 500 unidades.

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

Nenhum peso é 100% certo. O que dá para medir é quanto um erro nele mexe na sens. Calculei de cinco jeitos objetivos (o E entrou na terceira revisão), mexi na suavização e sorteei 1000 vezes as demos:

| Jeito | fino | curto | flick | médio | virada | rápido |
|---|---|---|---|---|---|---|
| **A) atual: corrida pelo 1º dano, curva por situação** | **24,9** | **26,8** | **17,8** | **12,0** | **4,2** | **14,3** |
| B) corrida pela kill | 26,4 | 15,5 | 18,1 | 12,0 | 6,5 | 21,5 |
| C) curva do inimigo única | 28,7 | 30,5 | 16,8 | 8,1 | 3,5 | 12,4 |
| D) só frequência (média simples) | 29,6 | 25,5 | 16,2 | 9,7 | 8,5 | 10,4 |
| E) impacto no round (WPA, `analise/pesos_wpa.py`) | 25,9 | 24,8 | 17,1 | 12,1 | 3,9 | 16,2 |
| A com a suavização pela metade / em dobro | 26,2 / 23,4 | 26,1 / 27,3 | 17,3 / 18,2 | 11,9 / 11,8 | 4,3 / 4,7 | 14,1 / 14,5 |

Efeito na sens, supondo que o melhor ponto de cada situação varia 20% entre elas: trocar A por B muda a sens em **2,9%** (típico) e custa **0,023%** de desempenho. A largura da suavização (Silverman) pela metade ou em dobro muda a sens só **0,34%** (0,0003%), um terço do sorteio do próprio A: qualquer regra de largura dá a mesma resposta. A incerteza do próprio A (1000 sorteios) mexe **1,15%** e custa 0,004%. O ruído do próprio teste (erro típico de 7,7% no desenho de 12 min) custa **~0,16%**, 7 a 40 vezes mais. Fica o A: a faixa de incerteza dele é pouco mais da metade da do B (10,2 contra 18,0 pontos), e nas tuas demos quem dá o primeiro dano ganha **76%** dos duelos decididos (87% quando és tu).

**E) Impacto no round (terceira revisão).** O objetivo de verdade é ganhar round, não duelo: vencer um 1x1 vale o round inteiro, um 5x5 no começo vale menos. O E multiplica o valor de cada duelo pela diferença na chance de ganhar o round entre vencer e perder aquele duelo, pelos vivos de cada lado e a bomba no momento. A chance sai de uma logística ajustada nos **4.904 estados de round** das tuas 15 demos, os dois times (exemplos, lado CT sem bomba: 5x5 56%, 5x4 77%, 4x5 34%, 2x1 90%, 1x2 15%). Resultado: cada situação mexe no round quase o mesmo tanto (média de 0,31 no ajuste curto a 0,37 na virada), então os pesos ficam dentro do sorteio do A (toda diferença tem intervalo passando por zero). Se o certo for o E e o app usar o A, a sens muda 0,62% e custa 0,0011%; o E é mais ruidoso (1,28% contra 1,10%). Perda esperada contra o objetivo do round: **A 0,0044%** (viés + sorteio) contra **E 0,0045%** (só sorteio). Empate, e o A fica: é o mais simples e já mira o round certo.

### 2.4 Cabeça, corpo e dano

**Hitboxes oficiais.** Extraídas da tua instalação com o Source 2 Viewer 20.1 (`agents/models/ctm_fbi`, grupo `physics_group_playerflesh`, 35 peças: cápsulas e esferas nas juntas). Script: `analise/hitboxes_cs2.py`. O boneco que aparece é essa hitbox, não o modelo visual: por isso parece um boneco de massinha e não o agente do jogo.

- **Cabeça: esfera de raio 5,0** (10 de diâmetro). A medida independente pelos 85 tiros na cabeça nas tuas demos (vítimas paradas) deu meia-largura **5,01**.
- **Postura do jogo medida nas demos** (`analise/medir_regioes.py` → `regioes.json`). O arquivo vem em pé reto e de braços abertos. Para achar a postura de jogo, peguei **4.901 balas** de todo mundo nas 15 demos que acertaram alguém em pé, sem atravessar parede. O ponto do acerto é o olho do atirador + a direção da bala × a distância percorrida, e a parte do corpo vem do `player_hurt`. A posição na demo tem um erro de ~3,5 unidades de altura (compensação de lag). Esse borrão empurra o ponto de 50% (probit) para o lado da parte com menos tiros, então a fronteira sai do **probit corrigido pela inclinação da densidade dos tiros** (fórmula de Tweedie, terceira revisão): se perto da fronteira o log da densidade dos tiros sobe b por unidade, o ponto de 50% cai b × s² abaixo dela, com s = o borrão, que o próprio probit mede pela largura. Fronteira = ponto de 50% + b × s²; o b sai de todos os tiros numa janela em volta da fronteira:

| Fronteira (altura acima do pé) | Medida |
|---|---|
| pernas → barriga | **29,71** (30,27 no jeito de medir das demos, IC 95% 29,57–31,56; o ponto de 50% sem correção dá 29,33. Antes: 28,77) |
| barriga → peito | **45,32** (45,88 nas demos, IC 95% 45,32–46,40; sem correção 45,02. Antes: 45,71, o meio entre 45,0 e 47,5. Só decide 3 ou 4 tiros a menos de ~16 m) |
| centro da cabeça | **62,3** (1,28 abaixo do olho em pé, 63,6) |

  As alturas das demos são medidas com o olho do atirador a 64,06; o app usa 63,6, por isso tudo desce ~0,5 na conversão.

  **Concorrentes da fronteira (terceira revisão, `analise/concorrentes_regioes.py`).** Simulação com a fronteira verdadeira conhecida (sorteada a ±2 da medida), o mesmo número de balas perto do eixo (1.361), densidade de tiros tirada das demos (alisada ou desborrada) e 4 tipos de borrão (normal 4,5; normal 3; cauda pesada; borrão variando de 2 a 7 por bala). 8 cenários × 40 sorteios. Erro típico, em unidades de altura:

| Método | pernas → barriga | barriga → peito | peito → cabeça | média |
|---|---|---|---|---|
| **Probit corrigido (Tweedie, janela ±6)** | **0,93** | **0,41** | **0,43** | **0,59** |
| Probit sem correção | 1,19 | 1,14 | 0,71 | 1,01 |
| Meio a meio probit e EM (o que valia na barriga → peito) | 1,19 | 1,12 | 0,82 | 1,04 |
| Máxima verossimilhança com densidade livre (EM; o que valia na pernas → barriga) | 1,45 | 1,42 | 1,23 | 1,37 |
| O mesmo EM com todos os candidatos nas mesmas iterações | 3,21 | 2,76 | 2,55 | 2,84 |
| **Probit corrigido com a janela otimizada (30 / 12,75 / 19,25), sorteios que não escolheram a janela** | **0,82** | **0,31** | **0,28** | **0,47** |

  O probit sem correção erra para o lado com menos tiros (viés de −1 a −1,4 na barriga → peito em todos os cenários); o corrigido fica a ±0,2 dela. O EM tem a verossimilhança quase chata (IC de ±3 ou mais): só a altura não separa bem o borrão da forma da distribuição, e com cauda pesada ele desaba. No `regioes.json` o probit e o EM continuam saindo, só para comparar.

  **Janela da inclinação (número exato).** O b sai de todos os tiros numa janela de ±w em volta da fronteira. O w foi otimizado na mesma simulação, com sorteios próprios (`concorrentes_regioes.py janela`, w de 2 a 30, de 0,25 em 0,25): **pernas → barriga 30** (o erro cai até a janela encostar no pé, que é o limite físico: essa fronteira fica a ~30 do chão), **barriga → peito 12,75** (empata a menos de 1% de 12,75 a 13,5) e **peito → cabeça 19,25** (16 a 20,25). Conferido nos sorteios da comparação, que não foram usados para escolher (`validar`): erro 0,82 / 0,31 / 0,28 contra 0,93 / 0,41 / 0,43 com ±6. Nas demos, apertar ou alargar em 3 as janelas do probit ou trocar o corte do eixo do corpo (2,5 a 4,5) mexe a barriga → peito no máximo 0,43 e a pernas → barriga até 1,22 (só 73 tiros de perna perto do eixo), sempre dentro do IC.

  O boneco (`analise/boneco.py` → `app/boneco.js`) usa os raios oficiais. A barriga e a ponta de baixo do peito vão para essas alturas, e as pernas encolhem para 85% na vertical (joelho dobrado) até o quadril ficar no lugar medido. Os braços seguram a arma; braço leva o mesmo dano do peito com colete, então a posição exata dele não muda a conta. Antes eu tinha chutado pernas 30% mais curtas, o que deixava a barriga 5 unidades baixa demais. Prévias: `analise/boneco_frente.png` e `boneco_lado.png`.
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
| Faixa | Cada rodada tem a **sua** largura (W1, W2, …), saída da otimização (quarta revisão): a 1ª vai de ÷e^(W1/2) a ×e^(W1/2) da tua sens, em volta do centro. Uma rodada extra repete a largura da última. (Testes de antes: a faixa era multiplicada por ρ a cada rodada.) |
| Alvos por bloco | Um número exato por rodada (a 1ª é a maior, de 29 a 52 alvos conforme a duração); a rodada extra repete o tamanho da última |
| Bloco | As situações da rodada, embaralhadas; **todos os alvos contam** (quarta revisão: separar 1 alvo para acostumar com a sens nova custa mais do que ajuda em todos os cenários de custo de troca testados; testes de antes tinham 1 a 3 alvos de adaptação) |
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
centro novo = centro − w × k_r × faixa_r      (k_r e faixa_r: o passo e a largura da rodada r)
faixa da rodada seguinte = a do protocolo (testes de antes: faixa × ρ)
```

As larguras e os passos de cada rodada, γ e GL0 de cada duração estão na seção 5; cada teste guarda os seus, então um teste antigo é sempre recalculado com as regras com que foi jogado (os de antes desta revisão: k = ¼, ρ = ½, γ = 1, GL0 = 6, 36/36/24/12/12, 3 de adaptação, 20 de aquecimento).

Veredito: |w| ≥ 1 vence; ≥ 0,5 puxão forte; ≥ 0,2 puxão fraco; abaixo, empate (só rótulo). **Nada é jogado fora:** rodada empatada mexe pouco, rodada decidida mexe muito, e cada rodada parte de onde a anterior deixou.

### 4.3 Sens do dia e ruído do método

- **Sens do dia** = o centro depois da última rodada.
- **Ruído do método (95%)** = até onde o puro acaso levaria o centro: `±1,96 × √Σ (k_r × faixa_r ÷ (γ × t_r))²`. É o pior caso (curva plana), por isso é conservador.
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

### 5.1 Faixa e passo de cada rodada (quarta revisão, 02/11/2026)

O mesmo modelo de 5.2: ruído de cada dia sorteado entre ×0,5 e ×2, cansaço, três formatos de curva, melhor sens entre −40% e +40%. Mas com duas mudanças que a quarta revisão achou:
- **cada rodada tem a sua faixa e o seu passo**, em vez de faixa × ρ e passo fixo;
- **nenhum alvo de adaptação**.

Como os números saíram:

1. **Otimização** (`analise/otimizar_livre.py`). Descida coordenada com os mesmos sorteios para todos os desenhos. Ela mexe nos alvos de cada rodada (inclusive passando alvos de uma rodada para outra), na faixa e no passo de cada rodada, no γ, no GL0 e no número de rodadas, sem passar do tempo. Partiu do desenho de 5.2. Em 20 min, partiu também do desenho vizinho, porque a primeira partida tinha parado num ótimo pior (0,1503% contra 0,1444%).
2. **Descida pelo certificado** (`analise/polir_certificado.py`). A cada volta, 400 mil dias novos, nunca usados antes, medem todos os vizinhos do desenho:
   - cada número um passo para cima e para baixo;
   - um alvo passado de uma rodada para outra;
   - uma rodada a mais ou a menos;
   - o desenho inteiro de uma vez: γ com todos os passos, todos os passos, todas as faixas.

   Só mexe se um vizinho ganha além do acaso, contando todos os vizinhos juntos (Bonferroni). Os vizinhos que mexem em números diferentes entram juntos na mesma volta. Para quando nenhum ganha: aí é **ótimo local certificado** em dias que a escolha não viu.
3. **Conferência** com o custo de trocar de sens e o aquecimento (os 25 cenários, um por dia) e nos 9 ataques. O desenho novo ganha do de 5.2 em todos os ataques, em todas as durações.

| Duração | Rodadas | Alvos por bloco em cada rodada | γ | GL0 | Perda (5.2 → novo) | Erro típico de sens | Com a melhor a +20%, termina em |
|---|---|---|---|---|---|---|---|
| 8 min (7,95) | 5 | 29, 15, 14, 14, 13 | 1,45 | 22 | 0,2034% → **0,1828%** | 12,5% → 11,9% | +14,3% → +15,7% |
| **12 min (11,78)** | **6** | **36, 22, 20, 19, 19, 18** | **1,3875** | **27** | **0,1814% → 0,1651%** | **12,0% → 11,4%** | **+15,2% → +16,3%** |
| 16 min (15,99) | 9 | 41, 18, 18, 17, 17, 16, 17, 17, 16 | 1,57543 | 27 | 0,1697% → **0,1513%** | 11,7% → 11,1% | +15,4% → +16,4% |
| 20 min (19,96) | 10 | 44, 24, 22, 21, 21, 20, 19, 20, 19, 18 | 1,4875 | 33 | 0,1615% → **0,1444%** | 11,5% → 10,9% | +15,6% → +16,7% |
| 25 min (24,99) | 14 | 45, 21, 20, 20, 20, 18, 17, 18, 18, 17, 16, 15, 16, 16 | 1,53187 | 35 | 0,1535% → **0,1366%** | 11,3% → 10,7% | +15,9% → +16,9% |
| 35 min (34,96) | 16 | 52, 29, 24, 25, 25, 24, 23, 23, 23, 23, 22, 22, 23, 23, 23, 24 | 1,5 | 43 | 0,1470% → **0,1282%** | 11,1% → 10,5% | +16,1% → +17,2% |

Perda e erro em 300 mil dias novos, com o ruído incerto e o custo de troca (`analise/resumo_livre.py`). Em todas as durações a perda cai 9% a 13%.

Faixa (razão entre as duas pontas) e passo de cada rodada:

- **8 min:** faixas ×3,23365 · 2,93981 · 2,94461 · 2,90775 · 2,92232; passos 0,19 · 0,1075 · 0,0875 · 0,0775 · 0,065
- **12 min:** faixas ×3,03774 · 2,81477 · 2,75069 · 2,72502 · 2,71086 · 2,69608; passos 0,185 · 0,10625 · 0,085 · 0,07125 · 0,0625 · 0,05375
- **16 min:** faixas ×2,97015 · 2,5788 · 2,5588 · 2,54613 · 2,5391 · 2,53619 · 2,52341 · 2,49968 · 2,5248; passos 0,18862 · 0,12218 · 0,10288 · 0,09002 · 0,07716 · 0,06859 · 0,06216 · 0,05787 · 0,05144
- **20 min:** faixas ×2,88237 · 2,60472 · 2,5588 · 2,49571 · 2,48882 · 2,48597 · 2,44883 · 2,4258 · 2,45018 · 2,45018; passos 0,185 · 0,1125 · 0,09 · 0,08 · 0,07 · 0,06 · 0,0525 · 0,0525 · 0,045 · 0,04
- **25 min:** faixas ×2,88237 · 2,5018 · 2,47643 · 2,44145 · 2,42034 · 2,3998 · 2,40286 · 2,3807 · 2,36854 · 2,36556 · 2,39491 · 2,37108 · 2,37108 · 2,32413; passos 0,18312 · 0,114 · 0,095 · 0,0855 · 0,076 · 0,0665 · 0,057 · 0,057 · 0,04987 · 0,04513 · 0,04038 · 0,038 · 0,038 · 0,03562
- **35 min:** faixas ×2,75554 · 2,48992 · 2,42664 · 2,38932 · 2,36415 · 2,35 · 2,34598 · 2,32798 · 2,31881 · 2,29472 · 2,28975 · 2,29182 · 2,27758 · 2,28088 · 2,25818 · 2,22456; passos 0,185 · 0,11 · 0,085 · 0,08 · 0,07 · 0,06 · 0,0525 · 0,05 · 0,045 · 0,0425 · 0,0375 · 0,035 · 0,035 · 0,03 · 0,03 · 0,03

O que o ótimo ensina agora:
- **As sondas ficam longe uma da outra o teste todo.** A faixa começa em ×2,8 a 3,2 e termina em ×2,2 a 2,9, porque a diferença entre duas sens distantes aparece mais que o ruído.
- **Quem afina é o passo do centro**, que cai rodada a rodada (de ~0,19 para 0,03 a 0,07).
- **A 1ª rodada é a maior** (29 a 52 alvos por bloco): ela decide a direção com bastante evidência, e as seguintes corrigem.
- Para o passo inteiro, exige ~1,4 a 1,6 vezes a MDE.
- **Sondas mais perto em todas as rodadas perdem**, mesmo re-otimizando o resto (seção 8).

No app (`?cobertura=300`, 12 min): **erro típico de 7,1%** na sens (o desenho de 5.2 dava 7,9%), e o ruído do método pegou a sens certa em 99,3% dos dias (antes 97,7%).

### 5.2 Números exatos da segunda revisão (faixa encolhendo ×ρ; histórico)

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

**Aquecimento e adaptação** (`analise/otimizar_adapt.py`, duelo a duelo, 25 cenários): adaptação 0 a 3 empatam (0,1727–0,1730%), 1 é o mínimo (com o desenho novo da quarta revisão, 0 passou a ganhar de 1 em todos os cenários: seção 8); aquecimento só piora (0: 0,1727%, 20: 0,1764%, 60: 0,1799%), inclusive no pior cenário. Com 50% de lentidão no começo, 0 contra 20 fica em ±0,01 ponto (ajuda se tu esquenta devagar, atrapalha se esquenta rápido).

**Ruído de partida** (`analise/otimizar_gl0.py`, ruído de cada dia entre ×0,5 e ×2): GL0 10 já ganhava de 6 (0,1920% contra 0,1932%); no refino final, com tudo junto, o ótimo ficou em 16 a 18. O valor de partida 0,088 é o melhor.

**O que não sai da otimização:** o limite de 2,5 s por alvo (é a definição de duelo dos pesos; o teto muda a nota menos de 0,1%) e a espera de 450 ms entre alvos (para a simulação menor é sempre melhor; o limite é humano e tuas demos não têm casos para medir; ver seção 8).

### 5.3 Desenho antigo (histórico)

Simulação bloco a bloco: ruído de 0,38 em ln(tempo) por duelo e 0,04 por bloco, aquecimento e cansaço ao longo do teste, três formatos de curva (pico, fundo chato com paredes, torta com perda 4× mais rápida na sens alta). Scripts em `analise/`. Esta tabela levou ao desenho antigo (5 rodadas, 36/36/24/12/12, ½, ¼); a otimização exata de 5.2 achou um desenho melhor, e a de 5.1 um melhor ainda.

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
| `analise/concorrentes_final.py`, `concorrente_bayes.py`, `concorrente_aurea.py`, `concorrentes_nota.py` | Métodos concorrentes (terceira revisão): conta final da sens, PSA bayesiano, seção áurea, nota do bloco |
| `analise/concorrentes_caminho.py`, `concorrentes_radial.py` | Concorrentes da continuação do caminho do alvo (tela e distância), contra o futuro real escondido |
| `analise/concorrentes_regioes.py` | Concorrentes da medida das fronteiras do corpo (simulação com a fronteira conhecida) |
| `analise/pesos_wpa.py` | Pesos pelo impacto no round (`pesos_wpa.json`) |
| `analise/otimizar_livre.py`, `polir_certificado.py`, `certificado_livre.py` | Quarta revisão: faixa e passo de cada rodada otimizados por duração; descida pelo certificado (vizinhos em 400 mil dias novos a cada volta, só mexe além do acaso) até nada ganhar (`otimo_livre_*_semcusto_adapt0.json`) |
| `analise/concorrentes_rodada.py`, `concorrentes_rodada_gama.py`, `concorrentes_rodada_v2.py` | Corridas da regra da rodada: livre, Kesten, momento, sondas mais perto, afinar mais rápido, com e sem custo de troca de sens; e a corrida contra o desenho novo |
| `analise/robustez_livre.py`, `conferir_adapt_livre.py`, `conferir_adapt_cenarios.py` | Os 9 ataques de cada desenho novo (com custo de troca); alvos de adaptação 0 a 3 |
| `analise/resposta_centro.py`, `movimento_proprio.py`, `resumo_livre.py`, `duracoes_js.py` | Quanto o centro anda; quanto do movimento do boneco é teu; resumo dos desenhos finais; bloco DURACOES do app gerado dos arquivos |
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

### Terceira revisão (métodos concorrentes)

As revisões anteriores otimizaram os **números** de cada método. Esta põe **outros métodos** contra os atuais, área por área, no mesmo critério e com os mesmos sorteios (ou os mesmos dados). Fica o que ganhar; empate fica o mais simples.

| Área | Concorrentes | Resultado | Mudou? |
|---|---|---|---|
| Conta final da sens (`concorrentes_final.py`; 200 mil dias por cenário, 4 cenários) | centro depois da última rodada (atual); média dos centros a partir da rodada 2, 3, 4 ou 5 (Polyak-Ruppert); média ponderada pela rodada; parábola com os 24 blocos; reta das inclinações; meio a meio com a parábola | perda média: **atual 0,2558%**; o melhor concorrente (média das rodadas 5–6) 0,2596%; parábola 0,4847%. A média ajuda só com ruído ×2, por 0,001 ponto | não |
| Método da rodada (`concorrente_bayes.py`, `concorrente_aurea.py`; 20 mil dias novos por cenário) | PSA (atual); PSA bayesiano: guarda a chance de cada (melhor sens, curvatura de cada lado), joga as pontas em volta da mediana, decide no fim pelo menor prejuízo esperado (18 ajustes); busca pela seção áurea, dura e com teste (24 ajustes) | perda média nos 4 cenários: **PSA 0,2564%**, bayesiano 0,3178%, seção áurea 1,4369%. O bayesiano só ganha (−0,007 ponto) com a melhor sens muito longe e perde muito com ruído ×2 (+0,18): ele confia no formato de curva que supôs. A seção áurea sonda perto do centro (sinal fraco) e um corte errado não volta | não |
| Nota do bloco (`concorrentes_nota.py`; duelo a duelo, 5 tipos de ruído: normal, cauda pesada, 5% e 15% de alvos perdidos por azar, alvos perdidos por causa da sens) | média de ln(tempo) (atual); média aparada 10% e 20%; mediana; média do tempo sem log; média da velocidade (1/tempo) | **atual 0,1761%**; aparada 10% +0,0016 ± 0,0003; aparada 20% +0,0029; velocidade +0,0073; mediana +0,0213; tempo sem log +0,0359. A aparada só ganha com cauda pesada e a velocidade só com muitos alvos perdidos; na média, todos perdem | não |
| Pesos (`pesos_wpa.py`, 2.3) | impacto no duelo (atual) contra impacto no round (WPA) | cada situação mexe no round quase o mesmo tanto (0,31 a 0,37); perda esperada contra o objetivo do round: atual 0,0044%, WPA 0,0045% | não |
| Suavização da curva do inimigo (`pesos_robustez.py`, 2.3) | Silverman (atual) contra a metade e o dobro da largura | a sens muda 0,34%, um terço do sorteio dos próprios pesos | não |
| Continuação do caminho do alvo (`concorrentes_caminho.py`, 2.1) | 12 jeitos: emendas com 6 regras de casar o doador, processo aleatório ajustado, velocidade caindo (8 meias-vidas), congelar | **emenda casando o próximo passo: 0,071** contra 0,112 da antiga (ganha em 100% dos sorteios); a costura deixou de aparecer (salto 2,9 → 1,0°/s) | **sim** |
| Aproximação do alvo na continuação (`concorrentes_radial.py`) | em unidades (atual) contra em proporção | unidades ganha em 99% dos sorteios, inclusive de perto | não |
| Fronteiras do corpo (`concorrentes_regioes.py`, 2.4; 8 cenários × 40 sorteios com a fronteira conhecida) | probit sem correção; probit corrigido pela inclinação (Tweedie); máxima verossimilhança com densidade livre (EM) e a versão com iterações iguais; meio a meio probit e EM | erro típico médio: **Tweedie 0,59**, com a janela otimizada **0,47**; probit 1,01; meio a meio (o que valia no peito) 1,04; EM (o que valia na perna) 1,37 | **sim**: barriga → peito 45,71 → 45,32 e fim da barriga 28,77 → 29,71 (IC de ±0,5 a ±1, contra ±3 do EM) |

O que não tem concorrente para medir: a definição do duelo (já variada na segunda revisão), o limite de 2,5 s e a espera de 450 ms (seção 5), e o que depende do teu teste exportado (ruído real, cansaço real).

**Ataques refeitos depois das duas mudanças:** sessão inteira de 12 min com o bot (24 blocos, 6 rodadas, 512 duelos, resultado na tela, nenhum erro); raios no boneco trocando de parte exatamente nas alturas novas; cobertura no app igual (`?cobertura=300`: 97,7%, erro típico 7,9%); ataque estatístico do desenho de 12 min igual (ganha do antigo nos 8 cenários); caminhos novos com a parte real idêntica nas 702 situações; pipeline inteiro refeito do zero a partir das demos dando os mesmos arquivos. O desenho de 12 min e o código do app não mudaram, então o certificado de ótimo local continua valendo.

### Quarta revisão (a sens quase não muda? o boneco é rápido? as sondas estão longe demais?)

| Pergunta | Resposta (com o dado) | Mudou algo? |
|---|---|---|
| O boneco anda na velocidade do CS? | O app toca o caminho na mesma velocidade da gravação (32 amostras/s de demos de 64 ticks). Mas o caminho é o inimigo visto do teu olho com os dois andando: 1,5× mais rápido que o inimigo sozinho (mediana 7,1 contra 4,8°/s), porque em 47% dos duelos mais da metade do movimento era teu. Fica assim: o teu movimento deixa os duelos mais lentos de verdade (t = 4,2) e o relativo explica melhor o teu tempo (seção 2.1) | não |
| A sens quase não muda: falta teste? | Com a melhor sens a +20%, o teste de 12 min da segunda revisão terminava em média a +15% (80% dos dias entre +7% e +24%; fundo chato: +17%), e o desenho novo vai a +16,3%. Mais tempo quase não muda isso (desenho novo: 8 min +15,7%; 35 min +17,2%), só aperta a faixa. Se para ti e teus amigos a sens fica parada, o mais provável é a melhor de hoje estar perto da que vocês usam (quem joga anos com uma sens fica adaptado a ela) ou o desempenho ser quase igual numa faixa larga. Um teste exportado (botão Exportar) mostra o ruído medido e o tamanho da diferença entre as pontas: aí dá para separar os dois casos (`analise/resposta_centro.py`) | não |
| Sondas mais perto? Afinar mais rápido? | Sondas mais perto em todas as rodadas perdem, mesmo re-otimizando o resto e com o custo de trocar de sens na conta (×2,85: +0,005 ponto; ×1,92: +0,08). Afinar mais rápido também (ρ 0,7: +0,031). Mas uma faixa e um passo **próprios de cada rodada** ganham: começa um pouco mais estreita e com passo maior, e depois a faixa quase não encolhe (`analise/concorrentes_rodada.py`) | **sim** (abaixo) |
| Outras regras da rodada | Kesten (só encolher quando a direção troca) ganha 0,0015 ponto no modelo mas perde com a melhor sens longe (+0,009); momento perde em 3 dos 9 ataques | não |
| O custo de trocar de sens estava na conta? | Não: entrava só na escolha dos alvos de adaptação. Agora o simulador do desenho tem os 25 cenários de custo de troca (proporcional ao tamanho da troca) e de aquecimento, um sorteado por dia (`concorrentes_rodada.py`, conferido contra o duelo a duelo do `otimizar_adapt.py`: mesmo efeito com diferença de 0,0004) | sim, na conta |

| Pergunta | Resposta (com o dado) | Mudou algo? |
|---|---|---|
| Faixa e passo por rodada: quanto ganha? | Em todas as durações, 9% a 13% menos perda que o desenho da segunda revisão (12 min: 0,1814% → 0,1651%), ganhando nos 9 ataques com custo de troca. O centro anda mais (12 min: +15,2% → +16,3% com a melhor a +20%) e erra menos (12,0% → 11,4%). Tabela em 5.1 | **sim** |
| E otimizar já com o custo de troca dentro da conta? | Ganha mais no modelo, mas estreita as sondas e perde em curvas que ele nunca viu (8 min: +0,013 ponto) e nas curvas planas. Fica o otimizado sem o custo e conferido com ele | não |
| Quantos alvos de adaptação? | 0 ganha de 1 em todos os cenários de custo de troca, inclusive com 25% de lentidão sumindo em 6 alvos (−0,0012 a −0,0020 ponto em 12 min). A ordem A B B A já cancela quase todo o custo da troca, e um alvo a mais medido vale mais (`conferir_adapt_cenarios.py`) | **sim** (1 → 0) |
| O otimizador achou o melhor mesmo? | O certificado mexe cada número em dias novos até nada ganhar. Isso pegou três problemas e corrigiu: <br>• 20 min tinha parado num ótimo pior (recomeçando do desenho de 16: 0,1503% → 0,1444%); <br>• 16 min tinha uma crista entre γ e os passos que um número de cada vez não atravessa (agora o certificado também mexe o desenho inteiro); <br>• 35 min tinha um limite de 16 rodadas no código (sem o limite, 16 continua o melhor). <br>No fim, as 6 durações ficaram certificadas | — |
| Depois de tudo, algo ganha do desenho novo? | Momento: o otimizador deixa em zero. Todas as faixas ×0,8 a ×1,2, ou todos os passos ×0,8 e ×1,25, com o resto re-otimizado: pior no modelo e em 5 a 7 dos 9 ataques (12 min, `concorrentes_rodada_v2.py`) | não: **fechou** |

**Ataques refeitos depois das mudanças:**
- os 9 cenários em cada duração, com custo de troca de sens, sem nenhuma perda;
- certificado em dias novos em cada duração;
- sessão inteira com o bot em 12, 25 e 35 min (24, 56 e 64 blocos), com a rodada extra em 12 min, sem nenhum erro;
- cobertura no app: 99,3%, erro típico 7,1%;
- os números do app conferidos contra os arquivos da otimização (`duracoes_js.py` gera o bloco).

Os dados das demos (situações, pesos, caminhos, boneco) não mudaram nesta revisão.
