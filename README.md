# AXIA - Controle de Equipamentos

Sistema web para cadastro e gerenciamento de equipamentos elétricos, desenvolvido para acompanhamento do Ofício 009/2026 da AXIA.

## Funcionalidades

- Cadastro individual de equipamentos
- Importação de planilhas Excel (.xlsx)
- Dashboard com resumo por regional e tipo de equipamento
- Relatório completo para visualização web
- Exportação de relatório formatado em Excel
- API REST para consulta dos dados

## Tecnologias

- **Python** + **Flask** (backend)
- **SQLite** (banco de dados)
- **Bootstrap 5** + **Bootstrap Icons** (frontend)
- **openpyxl** (manipulação de Excel)

## Como rodar

```bash
# Instalar dependências
pip install -r requirements.txt

# Criar arquivo de configuração
cp .env.example .env

# Iniciar o servidor
python app.py
```

Acessar em `http://127.0.0.1:5000`

## Estrutura do projeto

```
sistema-axia/
├── app.py              # Ponto de entrada
├── config.py           # Configurações (.env)
├── db.py               # Conexão com o banco
├── routes.py           # Rotas da aplicação
├── templates/          # Templates HTML
├── data/               # Banco SQLite
├── requirements.txt    # Dependências
└── test_app.py         # Testes automatizados
```

## Testes

```bash
pytest test_app.py -v
```

## API

- `GET /api/equipamentos` — Retorna todos os equipamentos em JSON
