"""
Script to populate database with top 10 Portuguese PPRs
"""
import sys
import os
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from database import SessionLocal
from models.ppr import PPR


# Top 10 PPRs in Portugal (2024 data)
PPRS_DATA = [
    {
        "nome": "GNB PPR Reforma",
        "gestor": "GNB Gestão de Ativos",
        "isin": "PTGNBPPR0009",
        "categoria": "Conservador",
        "taxa_gestao": Decimal("1.25")
    },
    {
        "nome": "Alves Ribeiro PPR II",
        "gestor": "Optimize Investment Partners",
        "isin": "PTALVPPR0003",
        "categoria": "Moderado",
        "taxa_gestao": Decimal("1.50")
    },
    {
        "nome": "Popular PPR",
        "gestor": "Santander Asset Management",
        "isin": "PTPOPPPR0007",
        "categoria": "Conservador",
        "taxa_gestao": Decimal("1.20")
    },
    {
        "nome": "Optimize PPR",
        "gestor": "Optimize Investment Partners",
        "isin": "PTOPTPPR0001",
        "categoria": "Dinâmico",
        "taxa_gestao": Decimal("1.75")
    },
    {
        "nome": "Santander PPR Reforma",
        "gestor": "Santander Asset Management",
        "isin": "PTSANPPR0005",
        "categoria": "Moderado",
        "taxa_gestao": Decimal("1.30")
    },
    {
        "nome": "BPI PPR Reforma",
        "gestor": "BPI Gestão de Activos",
        "isin": "PTBPIPPR0002",
        "categoria": "Conservador",
        "taxa_gestao": Decimal("1.15")
    },
    {
        "nome": "Montepio PPR Reformados",
        "gestor": "Montepio Gestão de Activos",
        "isin": "PTMNTPPR0006",
        "categoria": "Conservador",
        "taxa_gestao": Decimal("1.10")
    },
    {
        "nome": "Crédito Agrícola PPR Reformados",
        "gestor": "CA Gest",
        "isin": "PTCAGPPR0004",
        "categoria": "Moderado",
        "taxa_gestao": Decimal("1.35")
    },
    {
        "nome": "Bankinter PPR",
        "gestor": "Bankinter Gestão de Activos",
        "isin": "PTBNKPPR0008",
        "categoria": "Moderado",
        "taxa_gestao": Decimal("1.40")
    },
    {
        "nome": "Novo Banco PPR",
        "gestor": "GNB Gestão de Ativos",
        "isin": "PTNBAPPR0003",
        "categoria": "Conservador",
        "taxa_gestao": Decimal("1.28")
    }
]


def populate_pprs():
    """
    Populate database with PPR funds
    """
    print("=" * 60)
    print("PPR Data Population Script")
    print("=" * 60)

    db = SessionLocal()
    count = 0
    updated = 0

    try:
        for ppr_data in PPRS_DATA:
            # Check if PPR already exists (by ISIN)
            existing = db.query(PPR).filter(PPR.isin == ppr_data['isin']).first()

            if existing:
                # Update existing PPR
                existing.nome = ppr_data['nome']
                existing.gestor = ppr_data['gestor']
                existing.categoria = ppr_data['categoria']
                existing.taxa_gestao = ppr_data['taxa_gestao']
                updated += 1
                print(f"   ↻ Updated: {ppr_data['nome']}")
            else:
                # Create new PPR
                new_ppr = PPR(**ppr_data)
                db.add(new_ppr)
                count += 1
                print(f"   ✓ Added: {ppr_data['nome']}")

        db.commit()

        print("\n" + "=" * 60)
        print(f"✅ Success!")
        print(f"   New PPRs added: {count}")
        print(f"   PPRs updated: {updated}")
        print(f"   Total PPRs in database: {db.query(PPR).count()}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def list_pprs():
    """
    List all PPRs in database
    """
    db = SessionLocal()
    try:
        pprs = db.query(PPR).all()

        if pprs:
            print("\n📋 PPRs in Database:")
            print("-" * 80)
            print(f"{'Nome':<35} {'Gestor':<25} {'Categoria':<12} Taxa")
            print("-" * 80)

            for ppr in pprs:
                print(f"{ppr.nome:<35} {ppr.gestor:<25} {ppr.categoria:<12} {ppr.taxa_gestao}%")

            print("-" * 80)
        else:
            print("\n⚠️  No PPRs found in database")

    finally:
        db.close()


if __name__ == "__main__":
    populate_pprs()
    list_pprs()