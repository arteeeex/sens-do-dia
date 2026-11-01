# Sens do Dia

Achador da sensibilidade do dia no CS2. O app joga um PSA (duas sens nas pontas de uma faixa, A B B A, a faixa afinando aos poucos) com alvos tirados dos teus próprios duelos das demos, cada situação com o peso que ela tem em decidir duelo, e dá a sens com que tu mata mais rápido hoje.

- **Abrir:** `app/index.html` num navegador Chromium (Brave/Chrome), ou `Abrir Sens do Dia.cmd`.
- **Como funciona, com todas as contas, simulações e revisões:** [COMO-FUNCIONA.md](COMO-FUNCIONA.md).
- **Refazer pesos, boneco e caminhos com demos novas:** `Atualizar pesos com as demos.cmd` (precisa do `.venv` com `demoparser2`, `pandas` e `numpy`, das demos do CS2 e do arquivo `analise/meu_steamid.txt` só com o teu SteamID64, que fica fora do repositório).

Fora do repositório, de propósito: o ambiente do Python (`.venv`) e `analise/duelos.json` (tem SteamID de outros jogadores). O app roda sem eles: os pesos, as situações e o boneco já estão em `app/perfil.js` e `app/boneco.js`. As hitboxes do CS2 foram tiradas uma vez com o Source 2 Viewer e estão salvas em `analise/hitboxes_cs2.json`; só é preciso baixar o Source 2 Viewer de novo se a Valve mudar os modelos dos agentes (`analise/hitboxes_cs2.py`).
