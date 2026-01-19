"""
AI 服務層
處理所有與 Gemini API 相關的業務邏輯
"""
import json
import time
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from database.models import ClothingItem, WeatherData

class AIService:
    def __init__(self, api_key: str, rate_limit_seconds: int = 15):
        self.api_key = api_key
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def _rate_limit_wait(self):
        """API 速率限制保護"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def batch_auto_tag(self, img_bytes_list: List[bytes]) -> Optional[List[Dict]]:
        """
        批次 AI 自動標籤
        
        Args:
            img_bytes_list: 圖片 bytes 列表
            
        Returns:
            標籤列表或 None（如果失敗）
        """
        try:
            self._rate_limit_wait()
            
            prompt = f"""請仔細分析這 {len(img_bytes_list)} 件衣服,為每件衣服分別回傳 JSON 格式的標籤。

回傳格式必須是一個 JSON 陣列,包含 {len(img_bytes_list)} 個物件:
[
  {{
    "name": "衣服名稱(如:白色T恤、牛仔褲)",
    "category": "上衣|下身|外套|鞋子|配件",
    "color": "主要顏色",
    "style": "風格(如:休閒、正式、運動)",
    "warmth": 保暖度1-10的數字
  }},
  ... (依序對應每張圖片)
]

重要規則:
1. 只回傳 JSON 陣列,不要任何其他文字
2. 不要包含 ```json 或任何 Markdown 標籤
3. 陣列中的順序必須與圖片順序一致
4. 每個物件都必須包含所有 5 個欄位
"""
            
            content_parts = [prompt]
            for img_bytes in img_bytes_list:
                content_parts.append({
                    "mime_type": "image/jpeg",
                    "data": img_bytes
                })
            
            response = self.model.generate_content(content_parts)
            
            # 清理並解析回應
            clean_text = response.text.strip()
            clean_text = clean_text.replace('```json', '').replace('```', '').strip()
            
            tags_list = json.loads(clean_text)
            
            # 驗證回應
            if not isinstance(tags_list, list):
                raise ValueError("AI 回傳格式錯誤: 應為陣列")
            
            if len(tags_list) != len(img_bytes_list):
                raise ValueError(f"AI 回傳數量不符: 預期 {len(img_bytes_list)} 件,實際 {len(tags_list)} 件")
            
            # 驗證必要欄位
            required_fields = ['name', 'category', 'color', 'warmth']
            for idx, tags in enumerate(tags_list):
                for field in required_fields:
                    if field not in tags:
                        raise ValueError(f"第 {idx+1} 件衣服缺少必要欄位: {field}")
                
                tags['warmth'] = int(tags['warmth'])
            
            return tags_list
            
        except json.JSONDecodeError as e:
            print(f"JSON 解析錯誤: {str(e)}")
            return None
        except Exception as e:
            print(f"批次 AI 標籤失敗: {str(e)}")
            return None
    
    def generate_outfit_recommendation(
        self, 
        wardrobe: List[ClothingItem],
        weather: WeatherData,
        style: str,
        occasion: str
    ) -> Optional[str]:
        """
        生成穿搭推薦
        
        Args:
            wardrobe: 衣櫥列表
            weather: 天氣資料
            style: 風格偏好
            occasion: 場合
            
        Returns:
            AI 推薦文字或 None
        """
        try:
            self._rate_limit_wait()
            
            # 準備衣櫥摘要（不含圖片資料）
            wardrobe_summary = [
                {k: v for k, v in item.to_dict().items() if k != 'image_data'}
                for item in wardrobe
            ]
            
            prompt = f"""
你是一位專業的 AI 時尚顧問。請根據以下資訊推薦今日穿搭:

**情境資訊:**
- 城市: {weather.city}
- 溫度: {weather.temp}°C (體感 {weather.feels_like}°C)
- 天氣: {weather.desc}
- **場合/活動: {occasion}**
- **指定風格: {style}**

**使用者衣櫥:**
{json.dumps(wardrobe_summary, ensure_ascii=False, indent=2)}

**請提供:**
1. 推薦的完整穿搭組合,必須符合「{style}」風格並適合「{occasion}」場合。
2. 每件單品的選擇理由 (需綜合考慮天氣、風格特色與場合得體度)。
3. 整體風格說明與針對「{occasion}」的穿搭小建議。

請用親切、專業的口吻回答,使用繁體中文。
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"AI 推薦失敗: {str(e)}")
            return None
    
    def parse_recommended_items(
        self, 
        ai_response: str, 
        wardrobe: List[ClothingItem]
    ) -> List[ClothingItem]:
        """
        解析 AI 推薦文字,提取推薦的衣物 ID
        
        Args:
            ai_response: AI 回應文字
            wardrobe: 完整衣櫥列表
            
        Returns:
            推薦的衣物列表
        """
        recommended_items = []
        response_lower = ai_response.lower()
        
        for item in wardrobe:
            item_name = item.name.lower()
            item_category = item.category.lower()
            item_color = item.color.lower()
            
            # 使用名稱、類別、顏色進行匹配
            if (item_name and item_name in response_lower) or \
               (item_color and item_category and f"{item_color}{item_category}" in response_lower.replace(' ', '')):
                recommended_items.append(item)
        
        return recommended_items
