/**
 * API 模塊 - 與 Streamlit 後端通信
 */

// API 響應處理器
const apiHandlers = {
    login: null,
    register: null,
    weather: null
};

// 監聽 API 響應
window.addEventListener('apiResponse', (event) => {
    const response = event.detail;
    console.log('收到 API 響應:', response);
    
    // 根據響應類型調用對應的處理器
    if (response.user_id !== undefined) {
        // 登入響應
        if (apiHandlers.login) {
            apiHandlers.login(response);
            apiHandlers.login = null;
        }
    } else if (response.message === '註冊成功') {
        // 註冊響應
        if (apiHandlers.register) {
            apiHandlers.register(response);
            apiHandlers.register = null;
        }
    } else if (response.temperature !== undefined) {
        // 天氣響應
        if (apiHandlers.weather) {
            apiHandlers.weather(response);
            apiHandlers.weather = null;
        }
    }
});

/**
 * 登入
 */
async function login(username, password) {
    return new Promise((resolve, reject) => {
        // 設置響應處理器
        apiHandlers.login = (response) => {
            if (response.success) {
                // 保存用戶信息到 sessionStorage
                sessionStorage.setItem('user_id', response.user_id);
                sessionStorage.setItem('username', response.username);
                resolve(response);
            } else {
                reject(new Error(response.message || '登入失敗'));
            }
        };
        
        // 調用 Streamlit API
        if (window.FashionAPI) {
            window.FashionAPI.login(username, password);
        } else {
            reject(new Error('API 未初始化'));
        }
        
        // 設置超時
        setTimeout(() => {
            if (apiHandlers.login) {
                apiHandlers.login = null;
                reject(new Error('請求超時'));
            }
        }, 10000);
    });
}

/**
 * 註冊
 */
async function register(username, password) {
    return new Promise((resolve, reject) => {
        // 設置響應處理器
        apiHandlers.register = (response) => {
            if (response.success) {
                resolve(response);
            } else {
                reject(new Error(response.message || '註冊失敗'));
            }
        };
        
        // 調用 Streamlit API
        if (window.FashionAPI) {
            window.FashionAPI.register(username, password);
        } else {
            reject(new Error('API 未初始化'));
        }
        
        // 設置超時
        setTimeout(() => {
            if (apiHandlers.register) {
                apiHandlers.register = null;
                reject(new Error('請求超時'));
            }
        }, 10000);
    });
}

/**
 * 獲取天氣信息
 */
async function getWeather(city = 'Taipei') {
    return new Promise((resolve, reject) => {
        // 設置響應處理器
        apiHandlers.weather = (response) => {
            if (response.temperature !== undefined) {
                resolve(response);
            } else {
                reject(new Error(response.message || '獲取天氣失敗'));
            }
        };
        
        // 調用 Streamlit API
        if (window.FashionAPI) {
            window.FashionAPI.getWeather(city);
        } else {
            reject(new Error('API 未初始化'));
        }
        
        // 設置超時
        setTimeout(() => {
            if (apiHandlers.weather) {
                apiHandlers.weather = null;
                reject(new Error('請求超時'));
            }
        }, 10000);
    });
}

/**
 * 登出
 */
function logout() {
    sessionStorage.removeItem('user_id');
    sessionStorage.removeItem('username');
    // 清除 URL 參數
    if (window.FashionAPI) {
        window.FashionAPI.clearParams();
    }
    // 刷新頁面
    window.location.reload();
}

/**
 * 檢查是否已登入
 */
function isLoggedIn() {
    return sessionStorage.getItem('user_id') !== null;
}

/**
 * 獲取當前用戶信息
 */
function getCurrentUser() {
    return {
        user_id: sessionStorage.getItem('user_id'),
        username: sessionStorage.getItem('username')
    };
}

// 導出 API
window.API = {
    login,
    register,
    logout,
    getWeather,
    isLoggedIn,
    getCurrentUser
};
