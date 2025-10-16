# PPR Bitcoin - Quick Start Guide 🚀

Guia rápido para começar a usar a aplicação PPR + Bitcoin.

## ⚡ Setup Inicial (5 minutos)

### 1. Iniciar PostgreSQL

```bash
# Na raiz do projeto
docker-compose up -d
```

Aguardar ~10 segundos para PostgreSQL inicializar.

### 2. Instalar Dependências Python

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Popular Base de Dados

```bash
cd ../data/seeds
python setup_database.py
```

Este comando:
- ✅ Cria 10 PPRs
- ✅ Carrega dados Bitcoin (CSV + API)
- ✅ Gera 5 anos de histórico PPRs
- ⏱️ Demora ~2-3 minutos

### 4. Iniciar API

```bash
cd ../../backend
python app.py
```

🎉 **Pronto!** API disponível em http://localhost:8000/docs

---

## 📋 Comandos Úteis

### Backend (API)

```bash
cd backend

# Iniciar servidor
python app.py

# Iniciar com hot-reload
uvicorn app:app --reload

# Testar endpoints
curl http://localhost:8000/health
```

### Popular Dados

```bash
cd data/seeds

# Setup completo
python setup_database.py

# Apenas PPRs
python populate_pprs.py

# Apenas Bitcoin
python populate_bitcoin.py

# Histórico PPRs (sample data)
python populate_ppr_historical.py
```

### Scheduler (Updates Automáticos)

```bash
cd backend/services

# Iniciar scheduler
python scheduler.py start

# Testar Bitcoin update
python scheduler.py bitcoin

# Testar PPR update
python scheduler.py ppr
```

### Docker

```bash
# Iniciar PostgreSQL + PgAdmin
docker-compose up -d

# Parar containers
docker-compose down

# Ver logs
docker-compose logs -f postgres

# Reiniciar containers
docker-compose restart
```

---

## 🌐 URLs Importantes

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **API (Swagger)** | http://localhost:8000/docs | - |
| **API (Root)** | http://localhost:8000 | - |
| **PgAdmin** | http://localhost:5050 | admin@pprbitcoin.pt / admin |
| **PostgreSQL** | localhost:5432 | pprbitcoin / pprbitcoin_dev_password |

---

## 🧪 Testar a API

### 1. Browser (Swagger UI)

Abrir http://localhost:8000/docs e testar endpoints interativamente.

### 2. cURL

```bash
# Health check
curl http://localhost:8000/health

# Lista de PPRs
curl http://localhost:8000/api/v1/pprs

# Bitcoin histórico
curl "http://localhost:8000/api/v1/bitcoin/historical?start_date=2024-01-01"

# PPR específico
curl http://localhost:8000/api/v1/pprs/{id}
```

### 3. Python

```python
import requests

# Get all PPRs
response = requests.get("http://localhost:8000/api/v1/pprs")
pprs = response.json()
print(f"Total PPRs: {pprs['total']}")

# Get Bitcoin data
response = requests.get("http://localhost:8000/api/v1/bitcoin/latest")
btc = response.json()
print(f"Bitcoin price: {btc['preco_eur']} EUR")
```

---

## 📊 Verificar Dados no PgAdmin

1. Abrir http://localhost:5050
2. Login: `admin@pprbitcoin.pt` / `admin`
3. Adicionar servidor:
   - **Name**: PPR Bitcoin
   - **Host**: `postgres`
   - **Port**: `5432`
   - **Database**: `pprbitcoin`
   - **Username**: `pprbitcoin`
   - **Password**: `pprbitcoin_dev_password`

### Queries Úteis

```sql
-- Total Bitcoin records
SELECT COUNT(*) FROM bitcoin_historical_data;

-- Latest Bitcoin price
SELECT data, preco_eur FROM bitcoin_historical_data
ORDER BY data DESC LIMIT 1;

-- All PPRs
SELECT nome, gestor, categoria FROM pprs;

-- PPR historical data count
SELECT p.nome, COUNT(h.id) as records
FROM pprs p
LEFT JOIN ppr_historical_data h ON h.ppr_id = p.id
GROUP BY p.nome;
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### "Connection refused" (PostgreSQL)

```bash
docker-compose up -d
# Aguardar 10 segundos
docker ps  # Verificar se está running
```

### "Port 5432 already in use"

Já tem PostgreSQL instalado localmente. Opções:

1. Parar PostgreSQL local
2. Mudar porta no `docker-compose.yml`:
   ```yaml
   ports:
     - "5433:5432"
   ```
   E atualizar `.env`:
   ```
   DATABASE_URL=postgresql://...@localhost:5433/pprbitcoin
   ```

### API não inicia

```bash
# Verificar se todas dependências estão instaladas
cd backend
pip install -r requirements.txt

# Verificar se PostgreSQL está acessível
python -c "from database import engine; print(engine)"
```

---

## 📁 Estrutura do Projeto

```
pprbitcoin/
├── backend/              # FastAPI backend
│   ├── api/routes/      # Endpoints REST
│   ├── models/          # SQLAlchemy models
│   ├── services/        # Business logic
│   ├── app.py           # Main app
│   ├── config.py        # Settings
│   └── database.py      # DB connection
├── data/
│   └── seeds/           # Scripts de população
├── frontend/            # React app (Fase 4)
├── docker-compose.yml   # PostgreSQL setup
└── spec.md              # Especificação completa
```

---

## 🎯 Próximos Passos

✅ **Fase 1**: Foundation (API básica) - **COMPLETA**
✅ **Fase 2**: Data Pipeline (Scrapers & APIs) - **COMPLETA**
⬜ **Fase 3**: Core Logic (Cálculo de portfolios)
⬜ **Fase 4**: Frontend (React UI)
⬜ **Fase 5**: Visualizações (Gráficos)
⬜ **Fase 6**: Refinamento
⬜ **Fase 7**: Deploy

---

## 📚 Documentação

- **API Docs**: http://localhost:8000/docs (quando servidor estiver running)
- **Spec completa**: [spec.md](spec.md)
- **Backend README**: [backend/README.md](backend/README.md)
- **Data README**: [data/README.md](data/README.md)

---

## 🤝 Contribuir

1. Fork o repositório
2. Criar branch (`git checkout -b feature/nova-feature`)
3. Commit mudanças (`git commit -m 'Add nova feature'`)
4. Push para branch (`git push origin feature/nova-feature`)
5. Abrir Pull Request

---

**Dúvidas?** Abrir issue no GitHub ou consultar a documentação completa no [spec.md](spec.md)