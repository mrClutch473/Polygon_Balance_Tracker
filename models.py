from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, Numeric, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from db import Base

class TokenTransfers(Base):
    __tablename__ = "token_transfers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False) 
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    token_id: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0) 

    from_address: Mapped[str] = mapped_column(String(42), nullable=False)
    to_address: Mapped[str] = mapped_column(String(42), nullable=False)
    amount: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False)

    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("block_number", "log_index", "batch_position", name="uq_block_log_batch"),
        Index("ix_from_address", "from_address"),
        Index("ix_to_address", "to_address"),
    )


class Progress(Base):
    __tablename__ = "progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False, unique=True)
    last_scanned_block: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
