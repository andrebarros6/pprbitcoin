# PPR Bitcoin API - Backend

API REST para análise de portfolios PPR + Bitcoin.

## Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **PostgreSQL** - Base de dados relacional
- **SQLAlchemy** - ORM Python
- **Alembic** - Migrations de base de dados
- **Pandas** - Processamento de dados financeiros

## Setup Inicial

### 1. Criar ambiente virtual Python

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Iniciar PostgreSQL (Docker)

Na raiz do projeto:

```bash
docker-compose up -d
```

Isto inicia:
- PostgreSQL na porta **5432**
- PgAdmin na porta **5050** (http://localhost:5050)

**Credenciais PgAdmin:**
- Email: `admin@pprbitcoin.pt`
- Password: `admin`

### 4. Configurar variáveis de ambiente

Copiar `.env.example` para `.env`:

```bash
cp .env.example .env
```

O ficheiro `.env` já está configurado para desenvolvimento local.

### 5. Criar tabelas na base de dados

```bash
cd backend
python -c "from database import init_db; init_db()"
```

Ou simplesmente iniciar o servidor (cria automaticamente):

```bash
python app.py
```

## Executar o Servidor

```bash
cd backend
python app.py
```

O servidor estará disponível em:
- **API**: http://localhost:8000
- **Documentação (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints Disponíveis

### PPRs

- `GET /api/v1/pprs` - Lista todos os PPRs
- `GET /api/v1/pprs/{id}` - Detalhes de um PPR
- `GET /api/v1/pprs/{id}/historical` - Dados históricos de um PPR

### Bitcoin

- `GET /api/v1/bitcoin/historical` - Dados históricos de Bitcoin (EUR)
- `GET /api/v1/bitcoin/latest` - Preço mais recente de Bitcoin

### Portfolio (NEW - Phase 3) 🎯

- `POST /api/v1/portfolio/calculate` - Calcular performance de um portfolio
  - Backtesting histórico com PPR + Bitcoin
  - Métricas financeiras completas (CAGR, Sharpe, drawdown, etc.)
  - Rebalanceamento configurável (mensal, trimestral, anual)
- `POST /api/v1/portfolio/compare` - Comparar múltiplas estratégias de portfolio
  - Comparação lado-a-lado de 2-5 portfolios
  - Análise de diferentes alocações de Bitcoin (0%, 10%, 20%, 30%)
  - Sumário de comparação com recomendação
- `GET /api/v1/portfolio/metrics` - Documentação das métricas disponíveis

### Sistema

- `GET /` - Info da API
- `GET /health` - Health check

## Estrutura do Projeto

```
backend/
├── api/
│   └── routes/
│       ├── ppr.py          # Endpoints de PPRs
│       ├── bitcoin.py      # Endpoints de Bitcoin
│       └── portfolio.py    # Endpoints de Portfolio (NEW)
├── models/
│   ├── ppr.py              # Models PPR e PPRHistoricalData
│   ├── bitcoin.py          # Model BitcoinHistoricalData
│   └── portfolio.py        # Schemas de Portfolio (NEW)
├── services/
│   ├── portfolio_calculator.py  # Cálculo de portfolios (NEW)
│   ├── bitcoin_updater.py       # Atualização de Bitcoin
│   ├── ppr_scraper.py           # Scraper de PPRs
│   └── scheduler.py             # Agendamento de tarefas
├── tests/
│   └── test_portfolio_calculator.py  # Testes unitários (NEW)
├── migrations/             # Migrations Alembic
├── app.py                  # Aplicação FastAPI principal
├── config.py               # Configurações
├── database.py             # Setup de base de dados
└── requirements.txt        # Dependências Python
```

## Desenvolvimento

### Executar com hot-reload

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Testes

```bash
pytest
```

### Code Quality

```bash
# Formatting
black .

# Linting
flake8 .

# Type checking
mypy .
```

## PgAdmin Setup

1. Aceder a http://localhost:5050
2. Login com `admin@pprbitcoin.pt` / `admin`
3. Adicionar novo servidor:
   - **Name**: PPR Bitcoin Local
   - **Host**: postgres (nome do container)
   - **Port**: 5432
   - **Database**: pprbitcoin
   - **Username**: pprbitcoin
   - **Password**: pprbitcoin_dev_password

## Status do Projeto

✅ **Fase 1**: Foundation (API básica) - **COMPLETA**
✅ **Fase 2**: Data Pipeline (Scrapers & APIs) - **COMPLETA**
✅ **Fase 3**: Core Logic (Cálculo de portfolios) - **COMPLETA**

### Próximos Passos (Fase 4)

- [ ] Implementar Frontend React com TypeScript
- [ ] Criar componentes de visualização de portfolios
- [ ] Adicionar gráficos interativos (Recharts)
- [ ] Interface de comparação de estratégias

## Troubleshooting

### Erro de conexão com PostgreSQL

Verificar se o container está a correr:

```bash
docker ps
```

Reiniciar os containers:

```bash
docker-compose down
docker-compose up -d
```

### Erro "table already exists"

Se as tabelas já existem, não é necessário executar `init_db()` novamente.

### Porta 5432 já em uso

Se já tem PostgreSQL instalado localmente, alterar a porta no `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Mudar de 5432 para 5433
```

E atualizar `DATABASE_URL` no `.env`:

```
DATABASE_URL=postgresql://pprbitcoin:pprbitcoin_dev_password@localhost:5433/pprbitcoin
```
