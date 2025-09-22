from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON
import uuid
from datetime import datetime
from app.db.database import Base


class PluginAsset(Base):
    __tablename__ = "plugin_assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    plugin_key = Column(String, nullable=False, unique=True)  # e.g., "rotation@2.0.0"
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
    tags = Column(JSON)  # Store as JSON array
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for API response."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "pluginKey": self.plugin_key,
            "thumbnailPath": self.thumbnail_path,
            "iconName": self.icon_name,
            "authorId": self.author_id,
            "authorName": self.author_name,
            "isPro": self.is_pro,
            "price": self.price,
            "rating": self.rating,
            "downloads": self.downloads,
            "likes": self.likes,
            "usageCount": self.usage_count,
            "tags": self.tags or [],
            "isFavorite": self.is_favorite,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
