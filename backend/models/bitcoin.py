"""
Bitcoin historical data database model
"""
from sqlalchemy import Column, DECIMAL, TIMESTAMP, Date, Index
from sqlalchemy.sql import func
import uuid
from database import Base
from utils.db_types import GUID


class BitcoinHistoricalData(Base):
    """
    Model for historical Bitcoin price data

    Stores daily Bitcoin prices in EUR
    """
    __tablename__ = "bitcoin_historical_data"
    __table_args__ = (
        Index('idx_bitcoin_data', 'data', postgresql_using='btree'),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    data = Column(Date, nullable=False, unique=True, index=True)
    preco_eur = Column(DECIMAL(12, 2), nullable=False)
    volume = Column(DECIMAL(20, 8), nullable=True)
    market_cap = Column(DECIMAL(20, 2), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<BitcoinHistoricalData(data={self.data}, preco_eur={self.preco_eur})>"
