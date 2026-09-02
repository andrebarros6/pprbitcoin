"""
PPR routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, UUID4
from decimal import Decimal

from database import get_db
from data.fund_ranking import rank_for, sort_key
from models.ppr import PPR, PPRHistoricalData

router = APIRouter(prefix="/pprs", tags=["PPRs"])


# Pydantic schemas for request/response
class PPRResponse(BaseModel):
    id: UUID4
    nome: str
    gestor: str
    isin: Optional[str]
    categoria: Optional[str]
    taxa_gestao: Optional[Decimal]
    # Position by assets under management among Portuguese PPR products;
    # None for funds outside the published top 10. See data/fund_ranking.py.
    market_rank: Optional[int] = None

    class Config:
        from_attributes = True


class PPRHistoricalDataResponse(BaseModel):
    data: date
    valor_quota: Decimal
    rentabilidade_acumulada: Optional[Decimal]

    class Config:
        from_attributes = True


class PPRListResponse(BaseModel):
    data: List[PPRResponse]
    total: int


class PPRHistoricalResponse(BaseModel):
    ppr: PPRResponse
    data: List[PPRHistoricalDataResponse]


@router.get("", response_model=PPRListResponse)
def get_pprs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of all PPRs

    Returns:
        List of PPRs with metadata
    """
    # Ordered by market position so the funds a saver is most likely to hold
    # appear first. Sorting in Python rather than SQL because the ranking is a
    # published external figure, not a stored column.
    all_pprs = sorted(db.query(PPR).all(), key=lambda p: sort_key(p.nome))
    total = len(all_pprs)
    page = all_pprs[skip:skip + limit]

    return PPRListResponse(
        data=[
            PPRResponse(
                id=p.id,
                nome=p.nome,
                gestor=p.gestor,
                isin=p.isin,
                categoria=p.categoria,
                taxa_gestao=p.taxa_gestao,
                market_rank=rank_for(p.nome),
            )
            for p in page
        ],
        total=total
    )


@router.get("/{ppr_id}", response_model=PPRResponse)
def get_ppr(ppr_id: UUID4, db: Session = Depends(get_db)):
    """
    Get a specific PPR by ID

    Args:
        ppr_id: UUID of the PPR

    Returns:
        PPR details
    """
    ppr = db.query(PPR).filter(PPR.id == ppr_id).first()

    if not ppr:
        raise HTTPException(status_code=404, detail="PPR not found")

    return ppr


@router.get("/{ppr_id}/historical", response_model=PPRHistoricalResponse)
def get_ppr_historical(
    ppr_id: UUID4,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get historical data for a specific PPR

    Args:
        ppr_id: UUID of the PPR
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        PPR details and historical data
    """
    ppr = db.query(PPR).filter(PPR.id == ppr_id).first()

    if not ppr:
        raise HTTPException(status_code=404, detail="PPR not found")

    query = db.query(PPRHistoricalData).filter(PPRHistoricalData.ppr_id == ppr_id)

    if start_date:
        query = query.filter(PPRHistoricalData.data >= start_date)
    if end_date:
        query = query.filter(PPRHistoricalData.data <= end_date)

    historical_data = query.order_by(PPRHistoricalData.data.asc()).all()

    return PPRHistoricalResponse(
        ppr=ppr,
        data=historical_data
    )
