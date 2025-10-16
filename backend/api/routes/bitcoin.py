"""
Bitcoin routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from decimal import Decimal

from database import get_db
from models.bitcoin import BitcoinHistoricalData

router = APIRouter(prefix="/bitcoin", tags=["Bitcoin"])


# Pydantic schemas
class BitcoinDataResponse(BaseModel):
    data: date
    preco_eur: Decimal
    volume: Optional[Decimal]

    class Config:
        from_attributes = True


class BitcoinHistoricalResponse(BaseModel):
    data: List[BitcoinDataResponse]


@router.get("/historical", response_model=BitcoinHistoricalResponse)
def get_bitcoin_historical(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get historical Bitcoin price data (EUR)

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of historical Bitcoin prices
    """
    query = db.query(BitcoinHistoricalData)

    if start_date:
        query = query.filter(BitcoinHistoricalData.data >= start_date)
    if end_date:
        query = query.filter(BitcoinHistoricalData.data <= end_date)

    historical_data = query.order_by(BitcoinHistoricalData.data.asc()).all()

    return BitcoinHistoricalResponse(data=historical_data)


@router.get("/latest", response_model=BitcoinDataResponse)
def get_latest_bitcoin_price(db: Session = Depends(get_db)):
    """
    Get the most recent Bitcoin price

    Returns:
        Latest Bitcoin price data
    """
    latest = db.query(BitcoinHistoricalData).order_by(
        BitcoinHistoricalData.data.desc()
    ).first()

    if not latest:
        return {"data": [], "message": "No Bitcoin data available"}

    return latest
