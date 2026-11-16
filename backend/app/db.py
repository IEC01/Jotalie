from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Wallet(Base):
    """Solde custodial d'un bénéficiaire, identifié par son téléphone (en FCFA)."""
    __tablename__ = "wallets"
    phone: Mapped[str] = mapped_column(String, primary_key=True)
    balance_xof: Mapped[int] = mapped_column(Integer, default=0)


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_name: Mapped[str] = mapped_column(String)
    recipient_phone: Mapped[str] = mapped_column(String, index=True)
    amount_xof: Mapped[int] = mapped_column(Integer)      # montant promis, figé
    amount_sats: Mapped[int] = mapped_column(Integer)
    rate_xof_per_btc: Mapped[int] = mapped_column(Integer)  # taux figé à la création
    invoice: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | paid
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Sms(Base):
    """Boîte d'envoi SMS (lue par le simulateur de téléphone du frontend)."""
    __tablename__ = "sms_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String, index=True)
    body: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String, ForeignKey("wallets.phone"))
    amount_xof: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String)  # wave | orange_money (simulé)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(engine)
