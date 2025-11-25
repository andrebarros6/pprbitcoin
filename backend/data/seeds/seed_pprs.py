"""
Seed script to populate the database with Portuguese PPR funds
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal, engine, Base
from models.ppr import PPR, PPRHistoricalData
from datetime import datetime, timedelta
import random

def seed_pprs():
    """Seed database with 10 major Portuguese PPR funds"""

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Check if PPRs already exist
    existing_count = db.query(PPR).count()
    if existing_count > 0:
        print(f"Database already has {existing_count} PPRs. Skipping seed.")
        db.close()
        return

    # 10 major Portuguese PPR funds
    # Using Portuguese column names: nome, gestor, taxa_gestao
    pprs_data = [
        {
            "nome": "GNB PPR Reforma Acções",
            "gestor": "GNB Gestão de Ativos",
            "isin": "PTGNBRE0007",
            "taxa_gestao": 1.95,  # Already as percentage (1.95%)
            "avg_annual_return": 0.065
        },
        {
            "nome": "Optimize PPR Reforma",
            "gestor": "Optimize Investment Partners",
            "isin": "PTOPTPPR001",
            "taxa_gestao": 1.80,
            "avg_annual_return": 0.058
        },
        {
            "nome": "Santander PPR Dinâmico",
            "gestor": "Santander Asset Management",
            "isin": "PTSANPPR003",
            "taxa_gestao": 2.10,
            "avg_annual_return": 0.055
        },
        {
            "nome": "BPI PPR Reforma Activa",
            "gestor": "BPI Gestão de Activos",
            "isin": "PTBPIPPR002",
            "taxa_gestao": 2.05,
            "avg_annual_return": 0.052
        },
        {
            "nome": "Montepio PPR Reforma",
            "gestor": "Montepio Gestão de Activos",
            "isin": "PTMONTPPR01",
            "taxa_gestao": 2.20,
            "avg_annual_return": 0.048
        },
        {
            "nome": "CGD PPR Reforma Valorização",
            "gestor": "Caixa Gestão de Ativos",
            "isin": "PTCGDPPR001",
            "taxa_gestao": 2.15,
            "avg_annual_return": 0.050
        },
        {
            "nome": "NB PPR Reforma Rendimento",
            "gestor": "Novo Banco Gestão de Ativos",
            "isin": "PTNBPPPR001",
            "taxa_gestao": 2.00,
            "avg_annual_return": 0.047
        },
        {
            "nome": "Bankinter PPR Reforma Prudente",
            "gestor": "Bankinter Gestão de Ativos",
            "isin": "PTBANKPPR01",
            "taxa_gestao": 1.85,
            "avg_annual_return": 0.045
        },
        {
            "nome": "ActivoBank PPR Global",
            "gestor": "ActivoBank Asset Management",
            "isin": "PTACTPPR001",
            "taxa_gestao": 1.75,
            "avg_annual_return": 0.062
        },
        {
            "nome": "BiG PPR Reforma Crescimento",
            "gestor": "BiG Gestão de Activos",
            "isin": "PTBIGPPR001",
            "taxa_gestao": 1.90,
            "avg_annual_return": 0.054
        }
    ]

    print("Seeding PPR funds...")

    for ppr_data in pprs_data:
        # Extract avg_return before creating PPR
        avg_return = ppr_data.pop("avg_annual_return")

        # Create PPR (Portuguese column names)
        ppr = PPR(**ppr_data)
        db.add(ppr)
        db.flush()  # Get the ID

        # Generate 5 years of historical data (monthly)
        print(f"  Creating historical data for {ppr.nome}...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)

        current_date = start_date
        base_value = 100.0
        current_value = base_value

        while current_date <= end_date:
            # Simulate monthly returns with some randomness
            monthly_return = (avg_return / 12) + random.uniform(-0.02, 0.02)
            current_value *= (1 + monthly_return)

            # Use Portuguese column names: data, valor_quota, rentabilidade_acumulada
            historical = PPRHistoricalData(
                ppr_id=ppr.id,
                data=current_date.date(),
                valor_quota=round(current_value, 4),
                rentabilidade_acumulada=round((current_value - base_value) / base_value * 100, 4)
            )
            db.add(historical)

            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        print(f"  [OK] {ppr.nome} - {ppr.isin}")

    db.commit()
    print(f"\n[SUCCESS] Seeded {len(pprs_data)} PPR funds with historical data!")
    db.close()


if __name__ == "__main__":
    seed_pprs()
