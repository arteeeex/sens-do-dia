# Sens do Dia

Achador da sensibilidade do dia no CS2. O app joga um PSA (duas sens nas pontas de uma faixa, A B B A, a faixa afinando aos poucos) com alvos tirados de duelos reais das demos, cada situação com o peso que ela tem em decidir duelo, e dá a sens com que tu mata mais rápido hoje.

## Como usar

**Pelo link, sem baixar nada:** https://arteeeex.github.io/sens-do-dia/app/ (funciona quando o GitHub Pages está ligado; ver "Para o dono" no fim).

**Baixando:**
1. Nesta página, botão verde **Code** → **Download ZIP**, e extrai a pasta onde quiser.
2. Dois cliques em `Abrir Sens do Dia.cmd` (abre no Brave se tiver; senão no navegador padrão). Também dá para abrir `app/index.html` direto no Chrome ou no Edge.

Tem que ser navegador **Chromium** (Chrome, Edge ou Brave): é ele que libera o movimento cru do mouse. Na tela inicial: DPI do mouse, a tua sens de hoje, o formato da imagem do CS2 e a duração do teste; depois **Começar**. No fim aparece a sens do dia e o comando `sensitivity` para copiar no console.

## Para o teste ficar com o TEU jogo

Do jeito que vem, o teste usa as situações e os pesos tirados das demos do dono do repositório: funciona como um teste genérico, mas não é feito para o teu jogo. Para usar os teus duelos:

1. Baixa a pasta (passo acima) e instala o [Python 3](https://www.python.org/downloads/). Dentro da pasta, num terminal:
   ```
   python -m venv .venv
   .venv\Scripts\pip install demoparser2==0.42.1 pandas==3.1.0 numpy==2.5.4
   ```
2. Cria o arquivo `analise/meu_steamid.txt` só com o teu SteamID64 (o número de 17 dígitos do link do teu perfil Steam).
3. Abre `Atualizar pesos com as demos.cmd` num editor de texto e troca a linha `set "DEMOS=..."` pela pasta `replays` do teu CS2 (algo como `...\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays`).
4. Baixa as tuas partidas no CS2 (**Assistir** → **Tuas partidas** → baixar) e dá dois cliques em `Atualizar pesos com as demos.cmd`. Ele refaz os pesos, as situações, os caminhos dos alvos e o boneco a partir das tuas demos.

## Para o dono: ligar o link

No repositório: **Settings** → **Pages** → em "Source", **Deploy from a branch**, branch **main**, pasta **/ (root)** → **Save**. Em cerca de 1 minuto o link lá de cima passa a funcionar.

## Mais

- Como funciona, com todas as contas, simulações e revisões: [COMO-FUNCIONA.md](COMO-FUNCIONA.md).
- Fora do repositório, de propósito: o ambiente do Python (`.venv`), `analise/duelos.json` (tem SteamID de outros jogadores) e `analise/meu_steamid.txt` (o teu ID). O app roda sem eles: os pesos, as situações e o boneco já estão em `app/perfil.js` e `app/boneco.js`.
- As hitboxes do CS2 foram tiradas uma vez com o Source 2 Viewer e estão salvas em `analise/hitboxes_cs2.json`; só é preciso baixá-lo de novo se a Valve mudar os modelos dos agentes (`analise/hitboxes_cs2.py`).
