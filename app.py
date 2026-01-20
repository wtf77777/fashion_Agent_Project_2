"""
Streamlit API 服務器 - 修復版
使用 iframe 和 postMessage 實現前後端通信
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json
import sys
import base64

# 添加 backend 到路徑
backend_path = Path(__file__).parent / 'backend'
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    from config import AppConfig
    from database.supabase_client import SupabaseClient
    from database.models import ClothingItem
    from api.ai_service import AIService
    from api.weather_service import WeatherService
    from api.wardrobe_service import WardrobeService
except ImportError as e:
    st.error(f"Import 錯誤: {str(e)}")
    st.stop()

# 頁面配置
st.set_page_config(
    page_title="AI Fashion Assistant",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隱藏 Streamlit UI
st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    .main .block-container {padding: 0; max-width: 100%;}
</style>
""", unsafe_allow_html=True)

# ========== 初始化服務 ==========
@st.cache_resource
def init_services():
    config = AppConfig.from_secrets() or AppConfig.from_env()
    
    supabase_client = None
    if config.supabase_url and config.supabase_key:
        supabase_client = SupabaseClient(config.supabase_url, config.supabase_key)
    
    return {
        'config': config,
        'supabase': supabase_client,
        'ai': AIService(config.gemini_api_key) if config.gemini_api_key else None,
        'weather': WeatherService(config.weather_api_key) if config.weather_api_key else None,
        'wardrobe': WardrobeService(supabase_client) if supabase_client else None
    }

# ========== API 處理器 ==========
def handle_api():
    services = init_services()
    api_endpoint = st.query_params.get('api', '')
    
    if not api_endpoint:
        return {'success': False, 'message': 'No API endpoint specified'}
    
    try:
        if api_endpoint == 'login':
            return api_login(services)
        elif api_endpoint == 'register':
            return api_register(services)
        elif api_endpoint == 'weather':
            return api_weather(services)
        elif api_endpoint == 'wardrobe':
            return api_wardrobe(services)
        elif api_endpoint == 'delete_item':
            return api_delete_item(services)
        elif api_endpoint == 'batch_delete':
            return api_batch_delete(services)
        else:
            return {'success': False, 'message': f'Unknown API: {api_endpoint}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ========== API 端點 ==========
def api_login(services):
    username = st.query_params.get('username', '')
    password = st.query_params.get('password', '')
    
    if not services['supabase']:
        return {'success': False, 'message': '資料庫未配置'}
    
    try:
        result = services['supabase'].client.table("users")\
            .select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        if result.data:
            return {
                'success': True,
                'user_id': str(result.data[0]['id']),
                'username': username
            }
        return {'success': False, 'message': '帳號或密碼錯誤'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_register(services):
    username = st.query_params.get('username', '')
    password = st.query_params.get('password', '')
    
    if not services['supabase']:
        return {'success': False, 'message': '資料庫未配置'}
    
    try:
        existing = services['supabase'].client.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        
        if existing.data:
            return {'success': False, 'message': '使用者名稱已存在'}
        
        result = services['supabase'].client.table("users")\
            .insert({"username": username, "password": password})\
            .execute()
        
        return {'success': True, 'message': '註冊成功'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_weather(services):
    city = st.query_params.get('city', 'Taipei')
    
    if not services['weather']:
        return {'success': False, 'message': '天氣服務未配置'}
    
    try:
        weather = services['weather'].get_weather(city)
        return weather.to_dict() if weather else {'success': False, 'message': '無法獲取天氣'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_wardrobe(services):
    user_id = st.query_params.get('user_id', '')
    
    if not services['wardrobe']:
        return {'success': False, 'message': '衣櫥服務未配置'}
    
    try:
        items = services['wardrobe'].get_wardrobe(user_id)
        return {
            'success': True,
            'items': [item.to_dict() for item in items]
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_delete_item(services):
    user_id = st.query_params.get('user_id', '')
    item_id = st.query_params.get('item_id', '')
    
    if not services['wardrobe']:
        return {'success': False, 'message': '衣櫥服務未配置'}
    
    try:
        success = services['wardrobe'].delete_item(user_id, int(item_id))
        return {'success': success}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_batch_delete(services):
    user_id = st.query_params.get('user_id', '')
    item_ids_json = st.query_params.get('item_ids', '[]')
    
    if not services['wardrobe']:
        return {'success': False, 'message': '衣櫥服務未配置'}
    
    try:
        item_ids = json.loads(item_ids_json)
        success, success_count, fail_count = services['wardrobe'].batch_delete_items(user_id, item_ids)
        return {
            'success': success,
            'success_count': success_count,
            'fail_count': fail_count
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ========== 讀取前端 ==========
@st.cache_data
def load_frontend_files():
    frontend_dir = Path(__file__).parent / 'frontend'
    
    try:
        with open(frontend_dir / 'index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        css = ''
        for file in ['style.css', 'upload.css', 'wardrobe.css', 'recommendation.css']:
            path = frontend_dir / 'css' / file
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    css += f'/* {file} */\n{f.read()}\n\n'
        
        js = ''
        for file in ['api.js', 'app.js', 'upload.js', 'wardrobe.js', 'recommendation.js']:
            path = frontend_dir / 'js' / file
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    js += f'// {file}\n{f.read()}\n\n'
        
        # 組合 HTML
        html = html.replace('</head>', f'<style>{css}</style></head>')
        html = html.replace('</body>', f'<script>{js}</script></body>')
        
        # 移除外部引用
        for tag in [
            '<link rel="stylesheet" href="css/style.css">',
            '<link rel="stylesheet" href="css/upload.css">',
            '<link rel="stylesheet" href="css/wardrobe.css">',
            '<link rel="stylesheet" href="css/recommendation.css">',
            '<script src="js/api.js"></script>',
            '<script src="js/app.js"></script>',
            '<script src="js/upload.js"></script>',
            '<script src="js/wardrobe.js"></script>',
            '<script src="js/recommendation.js"></script>'
        ]:
            html = html.replace(tag, '')
        
        return html, None
    except Exception as e:
        return None, str(e)

# ========== 渲染 API 響應頁面 ==========
def render_api_response(result):
    """為 API 請求渲染一個純 JSON 響應頁面"""
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>API Response</title>
    </head>
    <body>
        <script>
            // 將結果發送給父窗口
            if (window.parent !== window) {{
                window.parent.postMessage({{
                    type: 'api_response',
                    data: {json_str}
                }}, '*');
            }}
        </script>
        <pre>{json_str}</pre>
    </body>
    </html>
    """
    
    components.html(html, height=400)

# ========== 主程式 ==========
def main():
    # 檢查是否是 API 請求
    if 'api' in st.query_params:
        result = handle_api()
        render_api_response(result)
        st.stop()
    
    # 渲染前端
    html, error = load_frontend_files()
    if error:
        st.error(f"載入前端失敗: {error}")
        st.info("請確認 frontend/ 目錄下的所有文件都已上傳")
        st.stop()
    
    components.html(html, height=800, scrolling=True)

if __name__ == "__main__":
    main()
