"""
天氣服務層
處理天氣資料獲取與快取
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
from database.models import WeatherData

class WeatherService:
    def __init__(self, api_key: str, cache_hours: int = 1):
        self.api_key = api_key
        self.cache_hours = cache_hours
        self._cache = {}  # {city: (weather_data, timestamp)}
    
    def get_weather(self, city: str) -> Optional[WeatherData]:
        """
        獲取天氣資料(含快取機制)
        
        Args:
            city: 城市英文名稱
            
        Returns:
            WeatherData 或 None
        """
        # 檢查快取
        if city in self._cache:
            cached_data, cached_time = self._cache[city]
            if datetime.now() - cached_time < timedelta(hours=self.cache_hours):
                return cached_data
        
        # 獲取新資料
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_tw"
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'main' not in data:
                print(f"天氣 API 回應異常: {data}")
                return None
            
            weather_data = WeatherData(
                temp=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                desc=data['weather'][0]['description'],
                city=city,
                update_time=datetime.now()
            )
            
            # 更新快取
            self._cache[city] = (weather_data, datetime.now())
            
            return weather_data
            
        except requests.exceptions.Timeout:
            print(f"天氣 API 請求超時: {city}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"天氣 API 請求失敗: {str(e)}")
            return None
        except Exception as e:
            print(f"天氣資料處理失敗: {str(e)}")
            return None
    
    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
