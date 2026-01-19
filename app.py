"""
Streamlit API 服務器
提供前端所需的所有 API 端點
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json
import sys
from datetime import datetime

# 添加 backend 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from config import AppConfig
from database.supabase_client import SupabaseClient
from api.ai_service import AIService
from api.weather_service import WeatherService
from api.wardrobe_service import WardrobeService

# ========== 頁面配置 ==========
st.set_page_config(
    page_title="AI Fashion Assistant",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== 隱藏 Streamlit 默認 UI ==========
st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    iframe {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        right: 0;
        width: 100%;
        height: 100%;
        border: none;
        margin: 0;
        padding: 0;
        overflow: hidden;
        z-index: 999999;
    }
</style>
""", unsafe_allow_html=True)

# ========== 初始化服務 ==========
@st.cache_resource
def init_services():
    """初始化所有服務"""
    config = AppConfig.from_secrets()
    if config is None:
        config = AppConfig.from_env()
    
    services = {
        'config': config,
        'supabase': SupabaseClient(config.supabase_url, config.supabase_key) if config.supabase_url else None,
        'ai': AIService(config.gemini_api_key) if config.gemini_api_key else None,
        'weather': WeatherService(config.weather_api_key) if config.weather_api_key else None
    }
    
    return services

services = init_services()

# ========== 讀取並渲染前端 ==========
def load_frontend():
    """載入完整的前端應用"""
    frontend_dir = Path(__file__).parent / 'frontend'
    
    # 讀取 HTML
    html_file = frontend_dir / 'index.html'
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 讀取 CSS
    css_files = ['style.css', 'upload.css', 'wardrobe.css', 'recommendation.css']
    css_content = ''
    for css_file in css_files:
        css_path = frontend_dir / 'css' / css_file
        if css_path.exists():
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content += f.read() + '\n'
    
    # 讀取 JS
    js_files = ['api.js', 'app.js', 'upload.js', 'wardrobe.js', 'recommendation.js']
    js_content = ''
    for js_file in js_files:
        js_path = frontend_dir / 'js' / js_file
        if js_path.exists():
            with open(js_path, 'r', encoding='utf-8') as f:
                js_content += f.read() + '\n'
    
    # 組合完整的 HTML
    full_html = html_content.replace('</head>', f'<style>{css_content}</style></head>')
    full_html = full_html.replace('</body>', f'<script>{js_content}</script></body>')
    
    # 渲染
    components.html(full_html, height=1000, scrolling=True)

# ========== API 處理函數 ==========
def handle_api_request():
    """處理 API 請求"""
    # 獲取請求參數
    query_params = st.query_params
    
    if 'api' not in query_params:
        return None
    
    api_endpoint = query_params['api']
    
    try:
        # 路由到對應的 API 處理函數
        if api_endpoint == 'login':
            return api_login()
        elif api_endpoint == 'register':
            return api_register()
        elif api_endpoint == 'weather':
            return api_weather()
        elif api_endpoint == 'upload':
            return api_upload()
        elif api_endpoint == 'wardrobe':
            return api_wardrobe()
        elif api_endpoint == 'delete':
            return api_delete_item()
        elif api_endpoint == 'batch_delete':
            return api_batch_delete()
        elif api_endpoint == 'recommendation':
            return api_recommendation()
        else:
            return {'success': False, 'message': 'Unknown API endpoint'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ========== API 端點實現 ==========
def api_login():
    """登入 API"""
    username = st.query_params.get('username', '')
    password = st.query_params.get('password', '')
    
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        result = services['supabase'].client.table("users")\
            .select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        if result.data:
            return {
                'success': True,
                'user_id': result.data[0]['id'],
                'username': username
            }
        else:
            return {'success': False, 'message': '帳號或密碼錯誤'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_register():
    """註冊 API"""
    username = st.query_params.get('username', '')
    password = st.query_params.get('password', '')
    
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        # 檢查用戶名是否存在
        existing = services['supabase'].client.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        
        if existing.data:
            return {'success': False, 'message': '使用者名稱已存在'}
        
        # 創建新用戶
        result = services['supabase'].client.table("users")\
            .insert({"username": username, "password": password})\
            .execute()
        
        return {'success': True, 'message': '註冊成功'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_weather():
    """天氣 API"""
    city = st.query_params.get('city', 'Taipei')
    
    if not services['weather']:
        return None
    
    weather = services['weather'].get_weather(city)
    if weather:
        return weather.to_dict()
    return None

# ========== 主程式 ==========
def main():
    # 檢查是否是 API 請求
    if 'api' in st.query_params:
        result = handle_api_request()
        st.json(result)
    else:
        # 渲染前端
        load_frontend()

if __name__ == "__main__":
    main()
