# Data Pipeline - Fase 2

Scripts para popular a base de dados com dados históricos de PPRs e Bitcoin.

## 📁 Estrutura

```
data/
├── seeds/
│   ├── setup_database.py           # Master script (runs all)
│   ├── populate_pprs.py            # Populate 10 PPRs
│   ├── populate_bitcoin.py         # Populate Bitcoin data (CSV + API)
│   └── populate_ppr_historical.py  # Generate sample PPR historical data
└── scrapers/                       # Future scrapers
```

## 🚀 Quick Start

### Opção 1: Setup Automático (Recomendado)

Execute o script master que faz tudo:

```bash
cd data/seeds
python setup_database.py
```

Este script:
1. ✅ Cria os 10 PPRs na base de dados
2. ✅ Carrega dados Bitcoin do CSV
3. ✅ Busca dados Bitcoin adicionais da CoinGecko API
4. ✅ Mostra estatísticas finais

### Opção 2: Setup Manual (Passo-a-Passo)

```bash
cd data/seeds

# 1. Popular PPRs (fundos)
python populate_pprs.py

# 2. Popular dados históricos de Bitcoin
python populate_bitcoin.py

# 3. Gerar dados históricos de exemplo para PPRs
python populate_ppr_historical.py
```

## 📊 Scripts Disponíveis

### 1. `populate_pprs.py`

Cria os 10 maiores PPRs portugueses na base de dados.

**Dados incluídos:**
- GNB PPR Reforma
- Alves Ribeiro PPR II
- Popular PPR
- Optimize PPR
- Santander PPR Reforma
- BPI PPR Reforma
- Montepio PPR Reformados
- Crédito Agrícola PPR Reformados
- Bankinter PPR
- Novo Banco PPR

**Uso:**
```bash
python populate_pprs.py
```

### 2. `populate_bitcoin.py`

Popula dados históricos de Bitcoin em EUR.

**Fontes:**
1. CSV local (`BTC_EUR Kraken Historical Data (1).csv`)
2. CoinGecko API (últimos 5 anos)

**Uso:**
```bash
python populate_bitcoin.py
```

### 3. `populate_ppr_historical.py`

Gera dados históricos de **exemplo** para os PPRs.

⚠️ **Nota:** Estes são dados simulados para demonstração. Em produção, seriam substituídos por dados reais de scrapers.

**Características:**
- 5 anos de dados mensais
- Retornos realistas baseados na categoria do PPR:
  - Conservador: ~3.6% anual
  - Moderado: ~4.8% anual
  - Dinâmico: ~7.2% anual

**Uso:**
```bash
python populate_ppr_historical.py
```

### 4. `setup_database.py` (Master Script)

Executa todos os scripts acima numa sequência coordenada.

**Uso:**
```bash
python setup_database.py
```

## 🌐 CoinGecko API

### Sem API Key (Gratuito)
- Limite: 10-50 requests/minuto
- Dados disponíveis: preços históricos, volume

### Com API Key (Opcional)
1. Criar conta em [CoinGecko](https://www.coingecko.com/en/api)
2. Adicionar ao `.env`:
   ```
   COINGECKO_API_KEY=your_api_key_here
   ```

## 🔄 Updates Automáticos

O scheduler (Fase 2) atualiza dados automaticamente:

**Diariamente às 09:00 UTC:**
- Atualizar preço Bitcoin

**Diariamente às 18:00 UTC:**
- Scrape valores de quota dos PPRs

**Semanalmente (Domingo 02:00 UTC):**
- Health check da base de dados

Para iniciar o scheduler:

```bash
cd backend/services
python scheduler.py start
```

## 🧪 Testar Updates Manualmente

```bash
cd backend/services

# Testar update de Bitcoin
python scheduler.py bitcoin

# Testar update de PPRs
python scheduler.py ppr

# Testar todos os jobs
python scheduler.py test
```

## 📈 Verificar Dados na BD

Após popular, verificar no PgAdmin (http://localhost:5050):

### Query 1: Total de registos Bitcoin
```sql
SELECT COUNT(*) FROM bitcoin_historical_data;
```

### Query 2: Último preço Bitcoin
```sql
SELECT data, preco_eur
FROM bitcoin_historical_data
ORDER BY data DESC
LIMIT 1;
```

### Query 3: PPRs disponíveis
```sql
SELECT nome, gestor, categoria
FROM pprs
ORDER BY nome;
```

### Query 4: Total registos por PPR
```sql
SELECT p.nome, COUNT(h.id) as total_registos
FROM pprs p
LEFT JOIN ppr_historical_data h ON h.ppr_id = p.id
GROUP BY p.nome
ORDER BY total_registos DESC;
```

## 🛠️ Troubleshooting

### Erro: "No module named 'models'"

Certifique-se que está a executar os scripts da pasta correta e que o path está configurado.

```bash
# Deve estar em data/seeds/
cd data/seeds
python setup_database.py
```

### Erro: "Connection refused" (PostgreSQL)

Verificar se o PostgreSQL está a correr:

```bash
docker ps
```

Se não estiver, iniciar:

```bash
docker-compose up -d
```

### Erro: "CoinGecko API rate limit"

A API gratuita tem limites. Aguarde alguns minutos e tente novamente, ou use uma API key.

### Dados duplicados

Os scripts verificam registos existentes antes de inserir. É seguro executar múltiplas vezes.

## 📝 Próximos Passos (Fase 3)

- [ ] Implementar scrapers reais para PPRs
- [ ] Lógica de cálculo de portfolios
- [ ] Endpoint `/portfolio/calculate`
- [ ] Métricas financeiras (Sharpe, drawdown, volatilidade)

## 🔗 Links Úteis

- [CoinGecko API Docs](https://www.coingecko.com/en/api/documentation)
- [APFIPP - Associação PPRs](https://www.apfipp.pt/)
- [CMVM - Comissão Mercado](https://web3.cmvm.pt/)