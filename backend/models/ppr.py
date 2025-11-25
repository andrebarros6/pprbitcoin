"""
PPR (Plano Poupança Reforma) database models
"""
from sqlalchemy import Column, String, DECIMAL, TIMESTAMP, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base
from utils.db_types import GUID


class PPR(Base):
    """
    Model for PPR funds

    Represents a Portuguese pension savings plan (PPR)
    """
    __tablename__ = "pprs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    nome = Column(String(200), nullable=False, index=True)
    gestor = Column(String(100), nullable=False)
    isin = Column(String(12), unique=True, nullable=True, index=True)
    categoria = Column(String(50), nullable=True)  # 'Conservador', 'Moderado', 'Dinâmico'
    taxa_gestao = Column(DECIMAL(4, 2), nullable=True)  # % anual
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationship to historical data
    historical_data = relationship("PPRHistoricalData", back_populates="ppr", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PPR(id={self.id}, nome='{self.nome}', gestor='{self.gestor}')>"


class PPRHistoricalData(Base):
    """
    Model for historical PPR fund data

    Stores daily/monthly values for each PPR fund
    """
    __tablename__ = "ppr_historical_data"
    __table_args__ = (
        Index('idx_ppr_historical_data', 'ppr_id', 'data', postgresql_using='btree'),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ppr_id = Column(GUID(), ForeignKey('pprs.id'), nullable=False)
    data = Column(Date, nullable=False)
    valor_quota = Column(DECIMAL(10, 4), nullable=False)
    rentabilidade_acumulada = Column(DECIMAL(10, 4), nullable=True)  # % desde início
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationship to PPR
    ppr = relationship("PPR", back_populates="historical_data")

    def __repr__(self):
        return f"<PPRHistoricalData(ppr_id={self.ppr_id}, data={self.data}, valor_quota={self.valor_quota})>"
