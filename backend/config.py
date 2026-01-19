"""
配置管理模組
統一管理所有配置，支援環境變數和 Streamlit Secrets
"""
import os
import streamlit as st
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
    """應用配置類"""
    gemini_api_key: str
    weather_api_key: str
    supabase_url: str
    supabase_key: str
    default_city: str = "Taipei"
    api_rate_limit_seconds: int = 15
    max_batch_upload: int = 10
    weather_cache_hours: int = 1
    
    @classmethod
    def from_secrets(cls) -> Optional['AppConfig']:
        """從 Streamlit Secrets 載入配置"""
        try:
            return cls(
                gemini_api_key=st.secrets.get("GEMINI_KEY", ""),
                weather_api_key=st.secrets.get("WEATHER_KEY", ""),
                supabase_url=st.secrets.get("SUPABASE_URL", ""),
                supabase_key=st.secrets.get("SUPABASE_KEY", ""),
                default_city=st.secrets.get("DEFAULT_CITY", "Taipei")
            )
        except Exception:
            return None
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """從環境變數載入配置"""
        return cls(
            gemini_api_key=os.getenv("GEMINI_KEY", ""),
            weather_api_key=os.getenv("WEATHER_KEY", ""),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            default_city=os.getenv("DEFAULT_CITY", "Taipei")
        )
    
    def is_valid(self) -> bool:
        """檢查配置是否完整"""
        return all([
            self.gemini_api_key,
            self.weather_api_key,
            self.supabase_url,
            self.supabase_key
        ])

# 台灣城市資料
TAIWAN_CITIES = {
    "台北 (Taipei)": "Taipei",
    "新北 (New Taipei)": "New Taipei",
    "桃園 (Taoyuan)": "Taoyuan",
    "台中 (Taichung)": "Taichung",
    "台南 (Tainan)": "Tainan",
    "高雄 (Kaohsiung)": "Kaohsiung",
    "基隆 (Keelung)": "Keelung",
    "新竹 (Hsinchu)": "Hsinchu",
    "苗栗 (Miaoli)": "Miaoli",
    "彰化 (Changhua)": "Changhua",
    "南投 (Nantou)": "Nantou",
    "雲林 (Yunlin)": "Yunlin",
    "嘉義 (Chiayi)": "Chiayi",
    "屏東 (Pingtung)": "Pingtung",
    "宜蘭 (Yilan)": "Yilan",
    "花蓮 (Hualien)": "Hualien",
    "台東 (Taitung)": "Taitung",
    "澎湖 (Penghu)": "Penghu",
    "金門 (Kinmen)": "Kinmen",
    "馬祖 (Matsu)": "Matsu"
}

def get_city_display_name(english_name: str) -> str:
    """根據英文名稱獲取顯示名稱"""
    for display, english in TAIWAN_CITIES.items():
        if english.lower() == english_name.lower():
            return display
    return "台北 (Taipei)"
