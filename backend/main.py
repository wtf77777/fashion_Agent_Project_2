"""
FastAPI 後端主程式
完整的 RESTful API 服務
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from api.ai_service import AIService
from api.weather_service import WeatherService
from api.wardrobe_service import WardrobeService
from database.supabase_client import SupabaseClient
from database.models import ClothingItem

# ========== FastAPI 應用初始化 ==========
app = FastAPI(
    title="AI Fashion Assistant API",
    description="智慧衣櫥管理系統後端 API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ========== CORS 設定 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境改為你的 Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 服務初始化 ==========
supabase_client = None
ai_service = None
weather_service = None
wardrobe_service = None

@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化服務"""
    global supabase_client, ai_service, weather_service, wardrobe_service
    
    # 從環境變數獲取配置
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    gemini_key = os.getenv("GEMINI_KEY")
    weather_key = os.getenv("WEATHER_KEY")
    
    if not all([supabase_url, supabase_key, gemini_key, weather_key]):
        print("警告: 缺少必要的環境變數")
        return
    
    supabase_client = SupabaseClient(supabase_url, supabase_key)
    ai_service = AIService(gemini_key)
    weather_service = WeatherService(weather_key)
    wardrobe_service = WardrobeService(supabase_client)
    
    print("✅ 所有服務已初始化")

# ========== Pydantic 模型 ==========
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class DeleteItemRequest(BaseModel):
    user_id: str
    item_id: int

class BatchDeleteRequest(BaseModel):
    user_id: str
    item_ids: List[int]

class RecommendationRequest(BaseModel):
    user_id: str
    city: str
    style: Optional[str] = ""
    occasion: Optional[str] = "外出遊玩"

# ========== 健康檢查 ==========
@app.get("/")
async def root():
    return {
        "message": "AI Fashion Assistant API",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    services_status = {
        "supabase": supabase_client is not None,
        "ai_service": ai_service is not None,
        "weather_service": weather_service is not None,
        "wardrobe_service": wardrobe_service is not None
    }
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }

# ========== 認證 API ==========
@app.post("/api/login")
async def login(request: LoginRequest):
    """使用者登入"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=503, detail="資料庫服務未就緒")
        
        result = supabase_client.client.table("users")\
            .select("*")\
            .eq("username", request.username)\
            .eq("password", request.password)\
            .execute()
        
        if result.data:
            return {
                "success": True,
                "user_id": str(result.data[0]['id']),
                "username": request.username
            }
        else:
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"登入錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登入失敗: {str(e)}")

@app.post("/api/register")
async def register(request: RegisterRequest):
    """使用者註冊"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=503, detail="資料庫服務未就緒")
        
        # 檢查用戶是否存在
        existing = supabase_client.client.table("users")\
            .select("id")\
            .eq("username", request.username)\
            .execute()
        
        if existing.data:
            raise HTTPException(status_code=400, detail="使用者名稱已存在")
        
        # 創建新用戶
        result = supabase_client.client.table("users")\
            .insert({
                "username": request.username,
                "password": request.password  # 注意：生產環境應該加密
            })\
            .execute()
        
        return {
            "success": True,
            "message": "註冊成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"註冊錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"註冊失敗: {str(e)}")

# ========== 天氣 API ==========
@app.get("/api/weather")
async def get_weather(city: str = "Taipei"):
    """獲取天氣資料"""
    try:
        if not weather_service:
            raise HTTPException(status_code=503, detail="天氣服務未就緒")
        
        weather = weather_service.get_weather(city)
        
        if weather:
            return {
                "success": True,
                **weather.to_dict()
            }
        else:
            raise HTTPException(status_code=404, detail="無法獲取天氣資料")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"天氣 API 錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取天氣失敗: {str(e)}")

# ========== 上傳 API ==========
@app.post("/api/upload")
async def upload_images(
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """批次上傳圖片並 AI 辨識"""
    try:
        if not all([ai_service, wardrobe_service]):
            raise HTTPException(status_code=503, detail="AI 服務未就緒")
        
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="一次最多上傳 10 張圖片")
        
        # 讀取所有圖片
        img_bytes_list = []
        for file in files:
            content = await file.read()
            img_bytes_list.append(content)
        
        # AI 批次辨識
        tags_list = ai_service.batch_auto_tag(img_bytes_list)
        
        if not tags_list:
            raise HTTPException(status_code=500, detail="AI 辨識失敗")
        
        # 儲存到資料庫
        success_count = 0
        duplicate_count = 0
        fail_count = 0
        saved_items = []
        
        for img_bytes, tags in zip(img_bytes_list, tags_list):
            # 檢查重複
            img_hash = wardrobe_service.get_image_hash(img_bytes)
            is_duplicate, existing_name = wardrobe_service.check_duplicate_image(
                user_id, img_hash
            )
            
            if is_duplicate:
                duplicate_count += 1
                print(f"跳過重複圖片: {existing_name}")
                continue
            
            # 創建衣物項目
            item = ClothingItem(
                user_id=user_id,
                name=tags['name'],
                category=tags['category'],
                color=tags['color'],
                style=tags.get('style', ''),
                warmth=int(tags['warmth'])
            )
            
            # 儲存
            success, message = wardrobe_service.save_item(item, img_bytes)
            
            if success:
                success_count += 1
                saved_items.append(tags)
            else:
                fail_count += 1
                print(f"儲存失敗: {message}")
        
        return {
            "success": True,
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "fail_count": fail_count,
            "items": saved_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"上傳錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")

# ========== 衣櫥 API ==========
@app.get("/api/wardrobe")
async def get_wardrobe(user_id: str):
    """獲取使用者的衣櫥"""
    try:
        if not wardrobe_service:
            raise HTTPException(status_code=503, detail="衣櫥服務未就緒")
        
        items = wardrobe_service.get_wardrobe(user_id)
        
        return {
            "success": True,
            "items": [item.to_dict() for item in items],
            "total": len(items)
        }
        
    except Exception as e:
        print(f"獲取衣櫥錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取衣櫥失敗: {str(e)}")

@app.post("/api/wardrobe/delete")
async def delete_item(request: DeleteItemRequest):
    """刪除單件衣物"""
    try:
        if not wardrobe_service:
            raise HTTPException(status_code=503, detail="衣櫥服務未就緒")
        
        success = wardrobe_service.delete_item(request.user_id, request.item_id)
        
        return {
            "success": success,
            "message": "刪除成功" if success else "刪除失敗"
        }
        
    except Exception as e:
        print(f"刪除錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")

@app.post("/api/wardrobe/batch-delete")
async def batch_delete(request: BatchDeleteRequest):
    """批次刪除衣物"""
    try:
        if not wardrobe_service:
            raise HTTPException(status_code=503, detail="衣櫥服務未就緒")
        
        success, success_count, fail_count = wardrobe_service.batch_delete_items(
            request.user_id,
            request.item_ids
        )
        
        return {
            "success": success,
            "success_count": success_count,
            "fail_count": fail_count
        }
        
    except Exception as e:
        print(f"批次刪除錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批次刪除失敗: {str(e)}")

# ========== 推薦 API ==========
@app.post("/api/recommendation")
async def get_recommendation(request: RecommendationRequest):
    """獲取 AI 穿搭推薦"""
    try:
        if not all([ai_service, weather_service, wardrobe_service]):
            raise HTTPException(status_code=503, detail="推薦服務未就緒")
        
        # 獲取衣櫥
        wardrobe = wardrobe_service.get_wardrobe(request.user_id)
        
        if not wardrobe:
            raise HTTPException(status_code=404, detail="衣櫥是空的，請先上傳衣服")
        
        # 獲取天氣
        weather = weather_service.get_weather(request.city)
        
        if not weather:
            raise HTTPException(status_code=404, detail="無法獲取天氣資料")
        
        # 生成推薦
        style = request.style if request.style else "不限定風格"
        
        recommendation = ai_service.generate_outfit_recommendation(
            wardrobe=wardrobe,
            weather=weather,
            style=style,
            occasion=request.occasion
        )
        
        if not recommendation:
            raise HTTPException(status_code=500, detail="AI 推薦生成失敗")
        
        # 解析推薦的衣物
        recommended_items = ai_service.parse_recommended_items(
            recommendation,
            wardrobe
        )
        
        return {
            "success": True,
            "recommendation": recommendation,
            "items": [item.to_dict() for item in recommended_items],
            "weather": weather.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"推薦錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取推薦失敗: {str(e)}")

# ========== 本地開發啟動 ==========
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 啟動 FastAPI 服務於 port {port}")
    print(f"📚 API 文檔: http://localhost:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True  # 開發模式自動重載
    )
