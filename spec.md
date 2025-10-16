# Especificação: PPR + Bitcoin Portfolio Analyzer

## 📋 Visão Geral

Aplicação web para utilizadores portugueses analisarem o impacto de adicionar Bitcoin aos seus portfolios de PPR (Plano Poupança Reforma). A ferramenta permite comparar visualmente a evolução histórica de um portfolio 100% PPR vs. um portfolio híbrido PPR + Bitcoin.

---

## 🎯 Objetivos

1. Educar utilizadores sobre diversificação de portfolios com Bitcoin
2. Demonstrar performance histórica de estratégias híbridas
3. Facilitar decisões informadas sobre alocação de ativos
4. Interface simples e intuitiva para público geral português

---

## 👥 Público-Alvo

- Portugueses com PPR ativo
- Investidores curiosos sobre Bitcoin
- Idade: 25-55 anos
- Conhecimento financeiro: Básico a Intermédio

---

## 🏗️ Arquitetura Técnica

### Tech Stack

**Backend**
- **Framework**: FastAPI (Python 3.11+)
- **Base de Dados**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0
- **Processamento de Dados**: Pandas, NumPy
- **APIs Externas**: CoinGecko API, Kraken API
- **Web Scraping**: Selenium, BeautifulSoup4
- **Task Scheduling**: APScheduler
- **Validação**: Pydantic

**Frontend**
- **Framework**: React 18+ com TypeScript
- **Build Tool**: Vite
- **Gráficos**: Recharts ou Chart.js
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **State Management**: React Query (TanStack Query)
- **Formulários**: React Hook Form

**DevOps & Deploy**
- **Containerização**: Docker + Docker Compose
- **Backend Hosting**: Railway, Render ou Fly.io
- **Frontend Hosting**: Vercel ou Netlify
- **CI/CD**: GitHub Actions
- **Monitorização**: Sentry (erros), Plausible (analytics)

---

## 📊 Modelo de Dados

### Tabela: `pprs`
```sql
CREATE TABLE pprs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(200) NOT NULL,
    gestor VARCHAR(100) NOT NULL,
    isin VARCHAR(12) UNIQUE,
    categoria VARCHAR(50), -- 'Conservador', 'Moderado', 'Dinâmico'
    taxa_gestao DECIMAL(4,2), -- % anual
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `ppr_historical_data`
```sql
CREATE TABLE ppr_historical_data (
    id SERIAL PRIMARY KEY,
    ppr_id UUID REFERENCES pprs(id),
    data DATE NOT NULL,
    valor_quota DECIMAL(10,4) NOT NULL,
    rentabilidade_acumulada DECIMAL(10,4), -- % desde início
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ppr_id, data)
);
CREATE INDEX idx_ppr_historical_data ON ppr_historical_data(ppr_id, data DESC);
```

### Tabela: `bitcoin_historical_data`
```sql
CREATE TABLE bitcoin_historical_data (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL UNIQUE,
    preco_eur DECIMAL(12,2) NOT NULL,
    volume DECIMAL(20,8),
    market_cap DECIMAL(20,2),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_bitcoin_data ON bitcoin_historical_data(data DESC);
```

---

## 🔌 API Endpoints

### PPRs

#### `GET /api/v1/pprs`
Lista todos os PPRs disponíveis.

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "nome": "GNB PPR Reforma",
      "gestor": "GNB Gestão de Ativos",
      "isin": "PTGNBPPR0001",
      "categoria": "Moderado",
      "taxa_gestao": 1.25,
      "rentabilidade_1ano": 5.3,
      "rentabilidade_5anos": 3.8
    }
  ],
  "total": 10
}
```

#### `GET /api/v1/pprs/{id}/historical`
Dados históricos de um PPR específico.

**Query Params:**
- `start_date` (opcional): YYYY-MM-DD
- `end_date` (opcional): YYYY-MM-DD

**Response 200:**
```json
{
  "ppr": {
    "id": "uuid",
    "nome": "GNB PPR Reforma"
  },
  "data": [
    {
      "data": "2024-01-01",
      "valor_quota": 5.4321,
      "rentabilidade_acumulada": 124.5
    }
  ]
}
```

### Bitcoin

#### `GET /api/v1/bitcoin/historical`
Dados históricos de Bitcoin (EUR).

**Query Params:**
- `start_date` (opcional): YYYY-MM-DD
- `end_date` (opcional): YYYY-MM-DD

**Response 200:**
```json
{
  "data": [
    {
      "data": "2024-01-01",
      "preco_eur": 38456.78,
      "volume": 12345678.90
    }
  ]
}
```

### Portfolio

#### `POST /api/v1/portfolio/calculate`
Calcula evolução de portfolio híbrido.

**Request Body:**
```json
{
  "ppr_id": "uuid",
  "bitcoin_percentage": 10,
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "investimento_inicial": 10000,
  "aportes_mensais": 100,
  "rebalancing": "mensal"
}
```

**Parâmetros:**
- `ppr_id`: UUID do PPR selecionado
- `bitcoin_percentage`: Percentagem de Bitcoin no portfolio (0-100)
- `start_date`: Data de início da simulação
- `end_date`: Data de fim da simulação
- `investimento_inicial`: Valor inicial investido (€)
- `aportes_mensais`: Valor mensal adicionado ao portfolio (€)
- `rebalancing`: Frequência de rebalancing ('mensal', 'trimestral', 'anual', 'nunca')

**Response 200:**
```json
{
  "portfolio_ppr_only": [
    {"data": "2020-01-01", "valor": 10000},
    {"data": "2020-02-01", "valor": 10050}
  ],
  "portfolio_hybrid": [
    {"data": "2020-01-01", "valor": 10000},
    {"data": "2020-02-01", "valor": 10120}
  ],
  "metricas": {
    "ppr_only": {
      "retorno_total_pct": 23.5,
      "retorno_anualizado_pct": 4.3,
      "volatilidade_pct": 6.2,
      "sharpe_ratio": 0.69,
      "max_drawdown_pct": -12.3,
      "valor_final": 12350.00
    },
    "hybrid": {
      "retorno_total_pct": 45.8,
      "retorno_anualizado_pct": 7.9,
      "volatilidade_pct": 18.4,
      "sharpe_ratio": 0.43,
      "max_drawdown_pct": -35.2,
      "valor_final": 14580.00
    }
  },
  "alocacao_final": {
    "ppr_pct": 75.2,
    "bitcoin_pct": 24.8
  }
}
```

---

## 🎨 Interface do Utilizador

### Página Principal

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  PPR + Bitcoin Calculator  🇵🇹                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Dropdown: Selecione o seu PPR ▼]                 │
│                                                     │
│  Percentagem de Bitcoin: [====●====] 10%           │
│                                                     │
│  Período: [====●========] 5 anos                    │
│                                                     │
│  Investimento inicial: [10000] €                   │
│                                                     │
│  Aportes mensais: [100] €                          │
│                                                     │
│  [Botão: Calcular Portfolio]                       │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│              📈 GRÁFICO EVOLUTIVO                   │
│                                                     │
│  40.000€ ╭─────────────────────╮                   │
│          │    ┌────── Híbrido  │ (laranja)         │
│  30.000€ │   ┌┘                │                   │
│          │  ┌┘   ┌── PPR Only  │ (azul)            │
│  20.000€ │ ┌┘   ┌┘             │                   │
│          │┌┘   ┌┘               │                   │
│  10.000€ └────────────────────╯                   │
│          2020  2021  2022  2023  2024             │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 MÉTRICAS COMPARATIVAS                          │
│                                                     │
│  ┌─────────────────┬──────────┬──────────┐        │
│  │                 │ PPR Only │  Híbrido │        │
│  ├─────────────────┼──────────┼──────────┤        │
│  │ Retorno Total   │  +23.5%  │  +45.8%  │        │
│  │ Retorno Anual   │   +4.3%  │   +7.9%  │        │
│  │ Volatilidade    │    6.2%  │   18.4%  │        │
│  │ Sharpe Ratio    │    0.69  │    0.43  │        │
│  │ Max Drawdown    │  -12.3%  │  -35.2%  │        │
│  │ Valor Final     │ 12.350€  │ 14.580€  │        │
│  └─────────────────┴──────────┴──────────┘        │
│                                                     │
│  ⚠️  Aviso: Rentabilidades passadas não garantem  │
│     rentabilidades futuras. Bitcoin é volátil.     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Componentes React

#### `<PPRSelector>`
- Dropdown com search
- Mostra: nome, gestor, categoria, taxa gestão
- Props: `pprs[]`, `onSelect()`

#### `<BitcoinSlider>`
- Range slider 0-100%
- Valor atual visível
- Recomendação: 5-15% (highlight)
- Props: `value`, `onChange()`

#### `<PeriodSelector>`
- Range slider 1-10 anos
- Data início/fim calculadas automaticamente
- Props: `years`, `onChange()`

#### `<InvestmentInputs>`
- Input: investimento inicial (€)
- Input: aportes mensais (€)
- Validação: valores positivos

#### `<PortfolioChart>`
- Gráfico linha dupla (Recharts)
- Tooltip interativo
- Legendas clicáveis (toggle linhas)
- Responsivo
- Props: `dataPPR[]`, `dataHybrid[]`

#### `<MetricsPanel>`
- Tabela comparativa
- Destacar melhor valor (verde)
- Tooltips explicativos (ℹ️)
- Props: `metricsPPR`, `metricsHybrid`

#### `<DisclaimerBanner>`
- Aviso legal permanente
- Link para termos de uso

---

## 📚 Os 10 Maiores PPRs em Portugal (2024)

1. **GNB PPR Reforma** - GNB Gestão de Ativos (Conservador)
2. **Alves Ribeiro PPR II** - Optimize Investment Partners (Moderado)
3. **Popular PPR** - Santander Asset Management (Conservador)
4. **Optimize PPR** - Optimize Investment Partners (Dinâmico)
5. **Santander PPR Reforma** - Santander Asset Management (Moderado)
6. **BPI PPR Reforma** - BPI Gestão de Activos (Conservador)
7. **Montepio PPR Reformados** - Montepio Gestão de Activos (Conservador)
8. **Crédito Agrícola PPR Reformados** - CA Gest (Moderado)
9. **Bankinter PPR** - Bankinter Gestão de Activos (Moderado)
10. **Novo Banco PPR** - GNB Gestão de Ativos (Conservador)

### Fontes de Dados

- **APFIPP** (https://www.apfipp.pt/) - Associação oficial
- **CMVM** (https://web3.cmvm.pt/) - Dados regulados
- **Morningstar Portugal** - Ratings e performance
- Sites dos gestores/bancos - Valores de quota diários

---

## 🧮 Lógica de Cálculo

### Algoritmo de Simulação

```python
def calcular_portfolio_hibrido(
    ppr_data: pd.DataFrame,
    btc_data: pd.DataFrame,
    btc_percentage: float,
    investimento_inicial: float,
    aportes_mensais: float,
    rebalancing: str
) -> dict:
    """
    Simula a evolução de um portfolio híbrido PPR + Bitcoin.

    Passos:
    1. Alinhar datas (merge dos dataframes por data)
    2. Calcular retornos mensais de cada ativo
    3. Para cada mês:
       - Aplicar aporte mensal
       - Calcular valor de cada ativo com base em retornos
       - Se mês de rebalancing: reajustar para % target
       - Registrar valor total do portfolio
    4. Calcular métricas finais (Sharpe, drawdown, etc.)

    Returns:
        dict com arrays de valores e métricas calculadas
    """

    # Merge datasets por data
    df = pd.merge(ppr_data, btc_data, on='data', how='inner')

    # Calcular retornos mensais
    df['ppr_return'] = df['valor_quota'].pct_change()
    df['btc_return'] = df['preco_eur'].pct_change()

    # Inicializar portfolios
    portfolio_values = []
    ppr_allocation = investimento_inicial * (1 - btc_percentage / 100)
    btc_allocation = investimento_inicial * (btc_percentage / 100)

    for idx, row in df.iterrows():
        # Aplicar retornos mensais
        ppr_allocation *= (1 + row['ppr_return'])
        btc_allocation *= (1 + row['btc_return'])

        # Adicionar aporte mensal
        total_value = ppr_allocation + btc_allocation
        ppr_allocation += aportes_mensais * (1 - btc_percentage / 100)
        btc_allocation += aportes_mensais * (btc_percentage / 100)

        # Rebalancing (se aplicável)
        if should_rebalance(idx, rebalancing):
            total_value = ppr_allocation + btc_allocation
            ppr_allocation = total_value * (1 - btc_percentage / 100)
            btc_allocation = total_value * (btc_percentage / 100)

        portfolio_values.append({
            'data': row['data'],
            'valor': ppr_allocation + btc_allocation
        })

    # Calcular métricas
    metricas = calcular_metricas(portfolio_values, investimento_inicial, aportes_mensais)

    return {
        'portfolio_values': portfolio_values,
        'metricas': metricas
    }
```

### Métricas Calculadas

**Retorno Total (%)**
```python
investimento_total = investimento_inicial + (aportes_mensais * num_meses)
retorno_total_pct = ((valor_final - investimento_total) / investimento_total) * 100
```

**Retorno Anualizado (%)**
```python
anos = num_meses / 12
retorno_anualizado_pct = (((valor_final / investimento_total) ** (1 / anos)) - 1) * 100
```

**Volatilidade (Desvio Padrão Anualizado)**
```python
retornos_mensais = pd.Series(portfolio_values).pct_change().dropna()
volatilidade_pct = retornos_mensais.std() * np.sqrt(12) * 100
```

**Sharpe Ratio**
```python
# Taxa Livre Risco = Euribor 12M ou Obrigações Tesouro PT 10 anos
taxa_livre_risco = 3.0  # % anual (ajustar dinamicamente)
excess_return = retorno_anualizado_pct - taxa_livre_risco
sharpe_ratio = excess_return / volatilidade_pct
```

**Maximum Drawdown (%)**
```python
valores = pd.Series([v['valor'] for v in portfolio_values])
cummax = valores.cummax()
drawdown = (valores - cummax) / cummax
max_drawdown_pct = drawdown.min() * 100
```

---

## 🔄 Atualização de Dados

### Scheduler (APScheduler)

**Diariamente às 09:00 UTC:**
- Atualizar preço Bitcoin (CoinGecko API)
- Scrape valores de quota PPRs (sites gestores)
- Calcular rentabilidades acumuladas

**Semanalmente (Domingo 02:00 UTC):**
- Backup base de dados (pg_dump)
- Limpeza de logs antigos (> 30 dias)
- Verificação de integridade de dados (missing dates, outliers)

### Script de Scraping PPRs

```python
# backend/services/ppr_scraper.py

from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from datetime import datetime

async def scrape_all_pprs():
    """
    Para cada PPR na base de dados:
    1. Aceder ao site do gestor
    2. Extrair valor de quota mais recente
    3. Validar dados (range esperado, data correta)
    4. Inserir em BD se não existir
    5. Notificar erros (Sentry)
    """
    pprs = await get_pprs_from_db()

    for ppr in pprs:
        try:
            valor_quota = await scrape_ppr(ppr)
            await save_historical_data(ppr.id, datetime.today(), valor_quota)
            logger.info(f"✓ {ppr.nome}: {valor_quota}")
        except Exception as e:
            logger.error(f"✗ {ppr.nome}: {str(e)}")
            sentry.capture_exception(e)

async def scrape_ppr(ppr):
    """Scraping específico por gestor"""
    if ppr.gestor == "GNB Gestão de Ativos":
        return await scrape_gnb(ppr.url)
    elif ppr.gestor == "Optimize Investment Partners":
        return await scrape_optimize(ppr.url)
    # ... outros gestores
```

### Integração CoinGecko API

```python
# backend/services/bitcoin_updater.py

import aiohttp
from datetime import datetime

async def update_bitcoin_price():
    """
    Obter preço atual de Bitcoin em EUR via CoinGecko API
    """
    async with aiohttp.ClientSession() as session:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin",
            "vs_currencies": "eur",
            "include_24hr_vol": "true",
            "include_market_cap": "true"
        }

        async with session.get(url, params=params) as response:
            data = await response.json()

            await save_bitcoin_data(
                data=datetime.today(),
                preco_eur=data['bitcoin']['eur'],
                volume=data['bitcoin']['eur_24h_vol'],
                market_cap=data['bitcoin']['eur_market_cap']
            )
```

---

## 🚀 Fases de Implementação

### **Fase 1: Foundation** (Semana 1-2)

- [ ] Setup repositório GitHub
- [ ] Configurar Docker Compose (PostgreSQL + PgAdmin)
- [ ] Criar estrutura de pastas backend/frontend
- [ ] Implementar models SQLAlchemy (pprs, ppr_historical_data, bitcoin_historical_data)
- [ ] Criar migrations (Alembic)
- [ ] Migrar dados CSV existentes para PostgreSQL
- [ ] Setup FastAPI com endpoints básicos (GET /pprs)
- [ ] Documentação Swagger automática

### **Fase 2: Data Pipeline** (Semana 2-3)

- [ ] Integrar CoinGecko API para Bitcoin histórico
- [ ] Desenvolver scrapers para 10 PPRs (Selenium + BeautifulSoup)
- [ ] Popular BD com dados históricos (mínimo 5 anos)
- [ ] Implementar APScheduler para updates diários
- [ ] Criar endpoint GET /pprs/{id}/historical
- [ ] Criar endpoint GET /bitcoin/historical
- [ ] Testes de integridade de dados

### **Fase 3: Core Logic** (Semana 3-4)

- [ ] Implementar algoritmo de simulação de portfolio
- [ ] Cálculo de métricas (Sharpe, drawdown, volatilidade)
- [ ] Suporte para aportes mensais
- [ ] Implementar estratégias de rebalancing (mensal, trimestral, anual)
- [ ] Endpoint POST /portfolio/calculate
- [ ] Validação de inputs (Pydantic schemas)
- [ ] Testes unitários (pytest) - cobertura > 80%

### **Fase 4: Frontend Base** (Semana 4-5)

- [ ] Setup Vite + React + TypeScript
- [ ] Configurar Tailwind CSS + PostCSS
- [ ] Implementar componente PPRSelector (com search)
- [ ] Implementar BitcoinSlider e PeriodSelector
- [ ] Implementar InvestmentInputs (React Hook Form)
- [ ] Integrar React Query para API calls
- [ ] Error handling e loading states

### **Fase 5: Visualizações** (Semana 5-6)

- [ ] Implementar PortfolioChart com Recharts
- [ ] Gráfico responsivo e interativo (tooltip, zoom)
- [ ] Componente MetricsPanel (tabela comparativa)
- [ ] Loading states e skeletons
- [ ] Animações e transições suaves (Framer Motion)
- [ ] Dark mode (opcional)

### **Fase 6: Refinamento** (Semana 6-7)

- [ ] Adicionar tooltips explicativos (ℹ️) para métricas
- [ ] Página "Sobre" com metodologia detalhada
- [ ] FAQ sobre PPRs e Bitcoin
- [ ] Disclaimer legal e termos de uso
- [ ] Melhorias de UX/UI (feedback de designers)
- [ ] Testes E2E (Playwright)
- [ ] Testes de acessibilidade (WCAG 2.1)

### **Fase 7: Deploy** (Semana 7-8)

- [ ] Configurar CI/CD (GitHub Actions)
- [ ] Deploy backend (Railway/Render com PostgreSQL)
- [ ] Deploy frontend (Vercel)
- [ ] Configurar domínio personalizado (pprbitcoin.pt)
- [ ] Setup Sentry para error monitoring
- [ ] SSL e segurança (HTTPS, CORS, rate limiting)
- [ ] Performance optimization (caching com Redis)
- [ ] Configurar CDN (Cloudflare)

### **Fase 8: Lançamento** (Semana 8+)

- [ ] Beta testing com 10-20 utilizadores reais
- [ ] Correção de bugs reportados
- [ ] Documentação API (Swagger/OpenAPI)
- [ ] Anúncio em comunidades portuguesas:
  - Reddit r/literaciafinanceira
  - Fórum PPR Portugal
  - Twitter/X
  - LinkedIn
- [ ] SEO optimization (meta tags, sitemap, robots.txt)
- [ ] Google Analytics / Plausible Analytics
- [ ] Press kit e media outreach

---

## 🔒 Segurança & Compliance

### Avisos Legais Obrigatórios

> ⚠️ **Aviso Legal**
>
> Esta ferramenta é apenas para fins educacionais e informativos. Não constitui aconselhamento financeiro, fiscal ou de investimento. Rentabilidades passadas não garantem rentabilidades futuras. Bitcoin é um ativo altamente volátil e pode perder valor rapidamente. Os PPRs estão sujeitos a riscos de mercado e as rentabilidades podem variar.
>
> Consulte sempre um consultor financeiro certificado antes de tomar decisões de investimento. Esta ferramenta não recolhe nem armazena dados pessoais dos utilizadores.

### GDPR Compliance

- ✅ Não armazenar dados pessoais dos utilizadores
- ✅ Não requer registo/login
- ✅ Analytics anónimos (sem cookies de tracking)
- ✅ Política de privacidade transparente
- ✅ Direito ao esquecimento (N/A - sem dados pessoais)
- ✅ Consentimento de cookies (apenas essenciais)

### Rate Limiting

```python
# backend/middleware/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Aplicar aos endpoints
@app.post("/api/v1/portfolio/calculate")
@limiter.limit("100/minute")  # 100 requests por minuto por IP
async def calculate_portfolio():
    pass
```

### Proteção contra DDoS

- Cloudflare WAF
- Rate limiting por IP
- CAPTCHA em caso de suspeita

---

## 📈 Métricas de Sucesso

### KPIs (6 meses)

**Tráfego:**
- 1000+ utilizadores únicos/mês
- 500+ cálculos realizados/mês
- Tempo médio na página > 3 minutos
- Taxa de rejeição < 40%

**Engagement:**
- 30% dos visitantes fazem cálculo
- 20% ajustam parâmetros múltiplas vezes
- 10% partilham resultados (feature futura)

**Técnico:**
- API response time < 500ms (p95)
- Uptime > 99.5%
- Zero erros críticos

### Feedback Qualitativo

- Formulário de feedback simples (opcional)
- Sugestões de novos PPRs para adicionar
- Reportar dados incorretos
- Ideias de features

---

## 🛠️ Manutenção

### Atualizações Regulares

**Diariamente (automático):**
- Update preços Bitcoin
- Scrape valores quota PPRs
- Verificação de erros (logs)

**Semanalmente:**
- Revisão de logs e erros
- Verificação de integridade de dados
- Backup completo de BD

**Mensalmente:**
- Verificar alterações nos sites dos gestores (scrapers podem quebrar)
- Atualizar lista de PPRs (novos fundos, descontinuados)
- Revisar taxas de gestão
- Análise de métricas de uso

**Trimestralmente:**
- Atualizar dependências (npm, pip)
- Security audit (OWASP, Snyk)
- Backup completo de BD (offsite)
- Revisão de performance (otimizações)

---

## 💡 Features Futuras (Roadmap)

### V2 (3-6 meses pós-lançamento)

- [ ] Comparar múltiplos PPRs simultaneamente (até 3)
- [ ] Adicionar outros ativos (S&P500 ETF, ouro, obrigações PT)
- [ ] Simulação de cenários (bull/bear markets, stress testing)
- [ ] Exportar relatório PDF com gráficos e métricas
- [ ] Calculadora de benefícios fiscais PPR (dedução IRS)
- [ ] Comparação com ETFs globais (VWCE, IWDA)
- [ ] Calculadora de FIRE (Financial Independence Retire Early)

### V3 (6-12 meses pós-lançamento)

- [ ] Registo opcional (guardar portfolios favoritos)
- [ ] Alertas de rebalancing (email/push notifications)
- [ ] API pública (para developers/integrações)
- [ ] App mobile (React Native)
- [ ] Integração com Open Banking (Plaid/Tink) - ver saldos reais
- [ ] Community features (partilhar estratégias)
- [ ] Backtesting avançado (diferentes períodos, DCA)

### V4 (Longo prazo)

- [ ] Suporte para outros países (Espanha, Brasil)
- [ ] Integração com exchanges (compra automática)
- [ ] Robo-advisor básico (recomendações personalizadas)
- [ ] Curso educacional sobre PPRs e Bitcoin

---

## 📞 Contacto & Suporte

- **GitHub Issues**: https://github.com/username/pprbitcoin/issues
- **Email**: suporte@pprbitcoin.pt
- **Twitter**: @pprbitcoin
- **Discord**: Comunidade de suporte (futuro)

---

## 📄 Licença

**MIT License** - Open Source

```
MIT License

Copyright (c) 2025 PPR Bitcoin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Standard MIT License text]
```

**Contribuições bem-vindas!** 🇵🇹

---

## 🙏 Agradecimentos

- **APFIPP** - Dados sobre fundos PPR
- **CoinGecko** - API de preços Bitcoin
- **Comunidade r/literaciafinanceira** - Feedback e testes
- **Open Source Community** - Ferramentas utilizadas

---

## 📚 Recursos Adicionais

### Artigos de Referência
- [PPRs em Portugal: Guia Completo 2024](https://example.com)
- [Bitcoin como Ativo de Portfolio](https://example.com)
- [Teoria Moderna de Portfolio (Markowitz)](https://example.com)

### Estudos Relevantes
- "Bitcoin: A Hedge Against Inflation?" - Fidelity Digital Assets
- "Efficient Diversification of Investments" - Harry Markowitz
- "The Case for Bitcoin in Institutional Portfolios" - ARK Invest

---

**Versão**: 1.0.0
**Última Atualização**: 2025-10-15
**Autor**: [Seu Nome]
**Status**: 📋 Em Planeamento

---

*Este documento é uma especificação viva e será atualizado conforme o projeto evolui.*
