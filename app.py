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
import base64
import io
from PIL import Image

# ========== 修正 Import 路徑 ==========
# 添加 backend 到 Python 路徑
backend_path = Path(__file__).parent / 'backend'
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 現在可以直接 import
try:
    from config import AppConfig
    from database.supabase_client import SupabaseClient
    from database.models import ClothingItem, WeatherData
    from api.ai_service import AIService
    from api.weather_service import WeatherService
    from api.wardrobe_service import WardrobeService
except ImportError as e:
    st.error(f"❌ Import 錯誤: {str(e)}")
    st.info("請確認 backend/ 目錄下的所有文件都已上傳")
    st.stop()

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
    
    /* 讓 iframe 填滿整個視窗 */
    .main .block-container {
        padding: 0;
        max-width: 100%;
    }
    
    iframe {
        width: 100%;
        height: 100vh;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# ========== 初始化服務 ==========
@st.cache_resource
def init_services():
    """初始化所有服務"""
    try:
        config = AppConfig.from_secrets()
        if config is None:
            config = AppConfig.from_env()
        
        supabase_client = None
        if config.supabase_url and config.supabase_key:
            supabase_client = SupabaseClient(config.supabase_url, config.supabase_key)
        
        services = {
            'config': config,
            'supabase': supabase_client,
            'ai': AIService(config.gemini_api_key) if config.gemini_api_key else None,
            'weather': WeatherService(config.weather_api_key) if config.weather_api_key else None,
            'wardrobe': WardrobeService(supabase_client) if supabase_client else None
        }
        
        return services
    except Exception as e:
        st.error(f"服務初始化失敗: {str(e)}")
        return None

# ========== 讀取前端文件 ==========
@st.cache_data
def load_frontend_files():
    """載入所有前端文件"""
    frontend_dir = Path(__file__).parent / 'frontend'
    
    if not frontend_dir.exists():
        return None, "frontend 目錄不存在"
    
    try:
        # 讀取 HTML
        html_file = frontend_dir / 'index.html'
        if not html_file.exists():
            return None, "index.html 不存在"
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 讀取所有 CSS
        css_content = ''
        css_files = ['style.css', 'upload.css', 'wardrobe.css', 'recommendation.css']
        for css_file in css_files:
            css_path = frontend_dir / 'css' / css_file
            if css_path.exists():
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content += f'/* {css_file} */\n{f.read()}\n\n'
        
        # 讀取所有 JS
        js_content = ''
        js_files = ['api.js', 'app.js', 'upload.js', 'wardrobe.js', 'recommendation.js']
        for js_file in js_files:
            js_path = frontend_dir / 'js' / js_file
            if js_path.exists():
                with open(js_path, 'r', encoding='utf-8') as f:
                    js_content += f'// {js_file}\n{f.read()}\n\n'
        
        # 組合完整 HTML
        full_html = html_content.replace(
            '<link rel="stylesheet" href="css/style.css">',
            f'<style>{css_content}</style>'
        ).replace(
            '<script src="js/api.js"></script>',
            ''
        ).replace(
            '</body>',
            f'<script>{js_content}</script></body>'
        )
        
        # 移除其他外部引用
        full_html = full_html.replace('<link rel="stylesheet" href="css/upload.css">', '')
        full_html = full_html.replace('<link rel="stylesheet" href="css/wardrobe.css">', '')
        full_html = full_html.replace('<link rel="stylesheet" href="css/recommendation.css">', '')
        full_html = full_html.replace('<script src="js/app.js"></script>', '')
        full_html = full_html.replace('<script src="js/upload.js"></script>', '')
        full_html = full_html.replace('<script src="js/wardrobe.js"></script>', '')
        full_html = full_html.replace('<script src="js/recommendation.js"></script>', '')
        
        return full_html, None
        
    except Exception as e:
        return None, f"讀取前端文件失敗: {str(e)}"

# ========== API 端點處理 ==========
def api_login(services):
    """登入 API"""
    try:
        # 從 query params 獲取參數
        username = st.query_params.get('username', '')
        password = st.query_params.get('password', '')
        
        if not services or not services['supabase']:
            return {'success': False, 'message': '資料庫未配置'}
        
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

def api_register(services):
    """註冊 API"""
    try:
        username = st.query_params.get('username', '')
        password = st.query_params.get('password', '')
        
        if not services or not services['supabase']:
            return {'success': False, 'message': '資料庫未配置'}
        
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

def api_weather(services):
    """天氣 API"""
    try:
        city = st.query_params.get('city', 'Taipei')
        
        if not services or not services['weather']:
            return {'success': False, 'message': '天氣服務未配置'}
        
        weather = services['weather'].get_weather(city)
        if weather:
            return weather.to_dict()
        return None
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ========== 主程式 ==========
def main():
    # 初始化服務
    services = init_services()
    
    if services is None:
        st.error("❌ 服務初始化失敗")
        st.info("請檢查 Streamlit Secrets 配置")
        st.stop()
    
    # 檢查是否是 API 請求
    if 'api' in st.query_params:
        api_endpoint = st.query_params['api']
        
        result = None
        if api_endpoint == 'login':
            result = api_login(services)
        elif api_endpoint == 'register':
            result = api_register(services)
        elif api_endpoint == 'weather':
            result = api_weather(services)
        else:
            result = {'success': False, 'message': 'Unknown API endpoint'}
        
        # 返回 JSON
        st.json(result)
        return
    
    # 載入前端
    html_content, error = load_frontend_files()
    
    if error:
        st.error(f"❌ {error}")
        st.info("請確認以下文件已上傳到 GitHub:")
        st.code("""
frontend/
├── index.html
├── css/
│   ├── style.css
│   ├── upload.css
│   ├── wardrobe.css
│   └── recommendation.css
└── js/
    ├── api.js
    ├── app.js
    ├── upload.js
    ├── wardrobe.js
    └── recommendation.js
        """)
        st.stop()
    
    # 渲染前端
    components.html(html_content, height=800, scrolling=True)

if __name__ == "__main__":
    main()
