"""
Streamlit API 服務器 - Streamlit Cloud 優化版本
使用 localStorage + 輪詢機制處理通信
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json
import time

from backend.config import AppConfig
from backend.database.supabase_client import SupabaseClient
from backend.api.ai_service import AIService
from backend.api.weather_service import WeatherService

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

# ========== 初始化 Session State ==========
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'login_request' not in st.session_state:
    st.session_state.login_request = None
if 'register_request' not in st.session_state:
    st.session_state.register_request = None

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

# ========== API 處理函數 ==========
def api_login(username: str, password: str):
    """登入 API"""
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        result = services['supabase'].client.table("users")\
            .select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        if result.data:
            st.session_state.user_id = result.data[0]['id']
            st.session_state.username = username
            
            return {
                'success': True,
                'user_id': result.data[0]['id'],
                'username': username
            }
        else:
            return {'success': False, 'message': '帳號或密碼錯誤'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_register(username: str, password: str):
    """註冊 API"""
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
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

def api_weather(city: str = 'Taipei'):
    """天氣 API"""
    if not services['weather']:
        return {'success': False, 'message': 'Weather service not configured'}
    
    weather = services['weather'].get_weather(city)
    if weather:
        return weather.to_dict()
    return {'success': False, 'message': 'Weather data not found'}

def api_get_wardrobe(user_id: str):
    """獲取衣櫥 API"""
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        result = services['supabase'].client.table("wardrobe")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        return {
            'success': True,
            'items': result.data or []
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_delete_item(user_id: str, item_id: str):
    """刪除單個物品 API"""
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        result = services['supabase'].client.table("wardrobe")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("id", item_id)\
            .execute()
        
        return {
            'success': True,
            'deleted': True,
            'item_id': item_id
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_batch_delete(user_id: str, item_ids: list):
    """批量刪除物品 API"""
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        result = services['supabase'].client.table("wardrobe")\
            .delete()\
            .eq("user_id", user_id)\
            .in_("id", item_ids)\
            .execute()
        
        return {
            'success': True,
            'deleted_count': len(item_ids)
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

def api_get_recommendation(user_id: str, city: str, style: str, occasion: str):
    """獲取推薦 API"""
    if not services['ai']:
        return {'success': False, 'message': 'AI service not configured'}
    
    if not services['supabase']:
        return {'success': False, 'message': 'Database not configured'}
    
    try:
        # 獲取用戶衣櫥
        wardrobe = services['supabase'].client.table("wardrobe")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        # 獲取天氣
        weather = None
        if services['weather']:
            weather = services['weather'].get_weather(city)
        
        # 生成推薦（這裡需要根據你的 AIService 實現調整）
        recommendation = services['ai'].generate_recommendation(
            wardrobe.data,
            weather,
            style,
            occasion
        )
        
        return {
            'success': True,
            'recommendation': recommendation
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ========== 創建通信腳本 ==========
def create_communication_bridge(response_data=None):
    """創建前後端通信橋接"""
    response_json = json.dumps(response_data) if response_data else 'null'
    
    return f"""
    <script>
    // 全局 API 對象
    window.FashionAPI = {{
        currentResponse: {response_json},
        
        // 登入
        login: function(username, password) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'login');
            params.set('username', username);
            params.set('password', password);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 註冊
        register: function(username, password) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'register');
            params.set('username', username);
            params.set('password', password);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 獲取天氣
        getWeather: function(city) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'weather');
            params.set('city', city);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 獲取衣櫥
        getWardrobe: function(userId) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'wardrobe');
            params.set('user_id', userId);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 刪除單個物品
        deleteItem: function(userId, itemId) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'delete');
            params.set('user_id', userId);
            params.set('item_id', itemId);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 批量刪除
        batchDeleteItems: function(userId, itemIds) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'batch_delete');
            params.set('user_id', userId);
            params.set('item_ids', JSON.stringify(itemIds));
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 獲取推薦
        getRecommendation: function(userId, city, style, occasion) {{
            const params = new URLSearchParams(window.location.search);
            params.set('action', 'recommendation');
            params.set('user_id', userId);
            params.set('city', city);
            params.set('style', style);
            params.set('occasion', occasion);
            params.set('t', Date.now());
            window.location.search = params.toString();
        }},
        
        // 清除參數
        clearParams: function() {{
            if (window.location.search) {{
                window.history.replaceState({{}}, '', window.location.pathname);
            }}
        }}
    }};
    
    // 如果有響應數據，觸發事件
    if (window.FashionAPI.currentResponse) {{
        window.dispatchEvent(new CustomEvent('apiResponse', {{
            detail: window.FashionAPI.currentResponse
        }}));
        
        // 清除 URL 參數
        setTimeout(() => {{
            window.FashionAPI.clearParams();
        }}, 100);
    }}
    </script>
    """

# ========== 讀取並渲染前端 ==========
def load_frontend():
    """載入完整的前端應用"""
    
    # 檢查是否有 API 請求
    query_params = st.query_params
    response_data = None
    
    if 'action' in query_params:
        action = query_params['action']
        
        if action == 'login':
            username = query_params.get('username', '')
            password = query_params.get('password', '')
            response_data = api_login(username, password)
            
        elif action == 'register':
            username = query_params.get('username', '')
            password = query_params.get('password', '')
            response_data = api_register(username, password)
            
        elif action == 'weather':
            city = query_params.get('city', 'Taipei')
            response_data = api_weather(city)
            
        elif action == 'wardrobe':
            user_id = query_params.get('user_id', '')
            response_data = api_get_wardrobe(user_id)
            
        elif action == 'delete':
            user_id = query_params.get('user_id', '')
            item_id = query_params.get('item_id', '')
            response_data = api_delete_item(user_id, item_id)
            
        elif action == 'batch_delete':
            user_id = query_params.get('user_id', '')
            item_ids_str = query_params.get('item_ids', '[]')
            try:
                item_ids = json.loads(item_ids_str)
                response_data = api_batch_delete(user_id, item_ids)
            except:
                response_data = {'success': False, 'message': 'Invalid item_ids'}
                
        elif action == 'recommendation':
            user_id = query_params.get('user_id', '')
            city = query_params.get('city', 'Taipei')
            style = query_params.get('style', '不限定風格')
            occasion = query_params.get('occasion', '外出遊玩')
            response_data = api_get_recommendation(user_id, city, style, occasion)
    
    # 讀取前端文件
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
    
    # 在 body 結束前插入通信橋接和 JS
    bridge_script = create_communication_bridge(response_data)
    full_html = full_html.replace('</body>', f'{bridge_script}<script>{js_content}</script></body>')
    
    # 渲染
    components.html(full_html, height=1000, scrolling=True)

# ========== 主程式 ==========
def main():
    load_frontend()

if __name__ == "__main__":
    main()
