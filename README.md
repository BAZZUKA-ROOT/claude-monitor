# Claude Monitor

Painel de monitoramento de uso da API Anthropic, com dashboard web e alertas pelo Telegram.

## Tecnologias

Python, Flask, APScheduler, Requests, python-dotenv e python-telegram-bot.

## Estrutura

- app.py: aplicação web.
- anthropic_fetcher.py: coleta de informações da Anthropic.
- telegram_notifier.py: notificações Telegram.
- db.py: persistência.
- .env.example: referência de configuração.
- Dockerfile, docker-compose.yml e setup.sh: arquivos de implantação.

## Preparação

Revise o arquivo .env.example e configure as credenciais necessárias no ambiente. Para instalar dependências:

    python -m pip install -r requirements.txt

Os arquivos Docker também estão disponíveis. Valide credenciais e permissões antes de expor o dashboard.

## Segurança

Nunca versione arquivos .env, tokens de API ou outros segredos.
