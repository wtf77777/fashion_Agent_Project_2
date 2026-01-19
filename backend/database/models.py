"""
資料模型定義
定義所有資料結構，確保類型安全
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ClothingItem:
    """衣物項目資料模型"""
    id: Optional[int] = None
    name: str = ""
    category: str = ""  # 上衣|下身|外套|鞋子|配件
    color: str = ""
    style: str = ""
    warmth: int = 5
    image_data: Optional[str] = None
    image_hash: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """轉換為字典格式（用於資料庫儲存）"""
        return {
            "name": self.name,
            "category": self.category,
            "color": self.color,
            "style": self.style,
            "warmth": self.warmth,
            "image_data": self.image_data,
            "image_hash": self.image_hash,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ClothingItem':
        """從字典創建實例"""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            category=data.get("category", ""),
            color=data.get("color", ""),
            style=data.get("style", ""),
            warmth=data.get("warmth", 5),
            image_data=data.get("image_data"),
            image_hash=data.get("image_hash"),
            user_id=data.get("user_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )

@dataclass
class WeatherData:
    """天氣資料模型"""
    temp: float
    feels_like: float
    desc: str
    city: str
    update_time: datetime
    
    def to_dict(self) -> dict:
        return {
            "temp": round(self.temp, 1),
            "feels_like": round(self.feels_like, 1),
            "desc": self.desc,
            "city": self.city
        }

@dataclass
class User:
    """使用者資料模型"""
    id: Optional[str] = None
    username: str = ""
    password: str = ""  # 實際應用應使用加密
    created_at: Optional[datetime] = None
