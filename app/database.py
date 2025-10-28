from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.sql import func
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PlaidItem(Base):
    __tablename__ = "plaid_items"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(String, unique=True, index=True, nullable=False)
    access_token_enc = Column(Text, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    institution_id = Column(String)
    institution_name = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    plaid_item_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Integer)  # Store in smallest currency unit
    currency = Column(String, default="USD")
    name = Column(String)
    merchant_name = Column(String)
    date = Column(String)  # YYYY-MM-DD
    category = Column(JSON)  # Store categories as JSON array
    pending = Column(Boolean, default=False)
    payment_channel = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_type = Column(String)
    webhook_code = Column(String)
    item_id = Column(String)
    message = Column(Text)
    signature = Column(String)
    verified = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

class SecurityLog(Base):
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    user_id = Column(Integer, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    details = Column(Text)
    severity = Column(String)  # info, warning, error, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")