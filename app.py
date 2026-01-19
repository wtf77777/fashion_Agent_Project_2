"""
Streamlit API 服務器 - 修復版本
使用 Session State 處理登入邏輯
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json

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
if 'api_response' not in st.session_state:
    st.session_state.api_response = None

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
            # 儲存到 session state
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

def api_weather(city: str = 'Taipei'):
    """天氣 API"""
    if not services['weather']:
        return None
    
    weather = services['weather'].get_weather(city)
    if weather:
        return weather.to_dict()
    return None

# ========== 前端通信橋接 ==========
def create_bridge_script():
    """創建 JavaScript 橋接腳本"""
    return """
    <script>
    // Streamlit 通信橋接
    window.streamlitAPI = {
        login: function(username, password) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                data: {
                    action: 'login',
                    username: username,
                    password: password
                }
            }, '*');
        },
        register: function(username, password) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                data: {
                    action: 'register',
                    username: username,
                    password: password
                }
            }, '*');
        },
        getWeather: function(city) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                data: {
                    action: 'weather',
                    city: city
                }
            }, '*');
        }
    };
    
    // 接收 Streamlit 的響應
    window.addEventListener('message', function(event) {
        if (event.data.type === 'streamlit:render') {
            const response = event.data.args.api_response;
            if (response) {
                // 觸發自定義事件，讓前端處理
                window.dispatchEvent(new CustomEvent('apiResponse', {
                    detail: response
                }));
            }
        }
    });
    </script>
    """

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
    
    # 組合完整的 HTML，添加橋接腳本
    full_html = html_content.replace('</head>', f'<style>{css_content}</style></head>')
    full_html = full_html.replace('</body>', f'{create_bridge_script()}<script>{js_content}</script></body>')
    
    # 使用雙向通信組件
    component_value = components.html(
        full_html, 
        height=1000, 
        scrolling=True
    )
    
    # 處理來自前端的請求
    if component_value:
        action = component_value.get('action')
        
        if action == 'login':
            response = api_login(
                component_value.get('username'),
                component_value.get('password')
            )
            st.session_state.api_response = response
            st.rerun()
            
        elif action == 'register':
            response = api_register(
                component_value.get('username'),
                component_value.get('password')
            )
            st.session_state.api_response = response
            st.rerun()
            
        elif action == 'weather':
            response = api_weather(component_value.get('city', 'Taipei'))
            st.session_state.api_response = response
            st.rerun()

# ========== 主程式 ==========
def main():
    load_frontend()

if __name__ == "__main__":
    main()
