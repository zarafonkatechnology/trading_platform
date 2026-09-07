# src/database/init_db.py
"""
Database initialization script
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from config.settings import settings

def init_database():
    """Initialize database with tables"""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    print("✅ Database tables created")
    
    return engine

def get_session():
    """Get database session"""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    init_database()