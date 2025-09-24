from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime, Text
from app.db.database import Base
from datetime import datetime


class PluginAsset(Base):
    __tablename__ = "plugin_assets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text)
    plugin_key = Column(String, nullable=False, unique=True)
    thumbnail_path = Column(String, default="assets/thumbnail.svg")
    icon_name = Column(String)
    author_id = Column(String, nullable=False)
    author_name = Column(String, nullable=False)
    is_pro = Column(Boolean, default=False)
    price = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    downloads = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    tags = Column(JSON)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
