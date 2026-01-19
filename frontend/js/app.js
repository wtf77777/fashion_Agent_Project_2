// ========== 應用狀態管理 ==========
const AppState = {
    user: null,
    currentPage: 'upload',
    isLoading: false,
    
    setUser(user) {
        this.user = user;
        if (user) {
            localStorage.setItem('user', JSON.stringify(user));
        } else {
            localStorage.removeItem('user');
        }
    },
    
    getUser() {
        if (!this.user) {
            const stored = localStorage.getItem('user');
            this.user = stored ? JSON.parse(stored) : null;
        }
        return this.user;
    },
    
    setLoading(loading) {
        this.isLoading = loading;
        const overlay = document.getElementById('loading-overlay');
        if (loading) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
};

// ========== Toast 通知系統 ==========
const Toast = {
    show(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    },
    
    success(message) {
        this.show(message, 'success');
    },
    
    error(message) {
        this.show(message, 'error');
    },
    
    warning(message) {
        this.show(message, 'warning');
    },
    
    info(message) {
        this.show(message, 'info');
    }
};

// ========== 認證系統 ==========
const Auth = {
    init() {
        // 檢查登入狀態
        const user = AppState.getUser();
        if (user) {
            this.showAppContent(user);
        }
        
        // 綁定事件
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });
        
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        document.getElementById('register-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });
        
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });
    },
    
    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tab}-tab`);
        });
    },
    
    async handleLogin() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        AppState.setLoading(true);
        
        try {
            const result = await API.login(username, password);
            
            if (result.success) {
                const user = {
                    id: result.user_id,
                    username: username
                };
                AppState.setUser(user);
                this.showAppContent(user);
                Toast.success(`歡迎回來, ${username}! 🎉`);
            } else {
                Toast.error(result.message || '登入失敗');
            }
        } catch (error) {
            Toast.error('登入失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    async handleRegister() {
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const password2 = document.getElementById('register-password2').value;
        
        if (password !== password2) {
            Toast.error('兩次密碼輸入不一致');
            return;
        }
        
        if (password.length < 6) {
            Toast.error('密碼至少需要 6 個字元');
            return;
        }
        
        AppState.setLoading(true);
        
        try {
            const result = await API.register(username, password);
            
            if (result.success) {
                Toast.success('註冊成功! 請登入 ✅');
                this.switchTab('login');
                document.getElementById('login-username').value = username;
            } else {
                Toast.error(result.message || '註冊失敗');
            }
        } catch (error) {
            Toast.error('註冊失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    handleLogout() {
        AppState.setUser(null);
        document.getElementById('auth-section').style.display = 'block';
        document.getElementById('app-content').style.display = 'none';
        document.getElementById('weather-widget').style.display = 'none';
        document.getElementById('username-display').textContent = '未登入';
        document.getElementById('logout-btn').style.display = 'none';
        Toast.info('已登出');
    },
    
    showAppContent(user) {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('app-content').style.display = 'block';
        document.getElementById('weather-widget').style.display = 'block';
        document.getElementById('username-display').textContent = user.username;
        document.getElementById('logout-btn').style.display = 'block';
        
        // 載入天氣
        Weather.loadWeather();
    }
};

// ========== 天氣系統 ==========
const Weather = {
    async loadWeather() {
        const city = document.getElementById('city-select').value;
        
        try {
            const weather = await API.getWeather(city);
            
            if (weather) {
                document.getElementById('weather-city-name').textContent = `🌍 ${city} 即時天氣`;
                document.getElementById('weather-temp').textContent = `${weather.temp}°C`;
                document.getElementById('weather-feels').textContent = `${weather.feels_like}°C`;
                document.getElementById('weather-desc').textContent = weather.desc;
                
                const now = new Date();
                const timeStr = now.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
                document.getElementById('weather-update-time').textContent = `⏰ 更新時間: ${timeStr} (每小時自動更新)`;
            }
        } catch (error) {
            console.error('載入天氣失敗:', error);
        }
    }
};

// ========== 頁面導航 ==========
const Navigation = {
    init() {
        document.querySelectorAll('.app-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = e.target.dataset.page;
                this.switchPage(page);
            });
        });
    },
    
    switchPage(page) {
        AppState.currentPage = page;
        
        document.querySelectorAll('.app-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.page === page);
        });
        
        document.querySelectorAll('.page-content').forEach(content => {
            content.classList.toggle('active', content.id === `${page}-page`);
        });
        
        // 載入頁面數據
        this.loadPageData(page);
    },
    
    loadPageData(page) {
        switch(page) {
            case 'upload':
                // Upload page 在 upload.js 中處理
                break;
            case 'wardrobe':
                WardrobeUI.loadWardrobe();
                break;
            case 'recommendation':
                // Recommendation page 在 recommendation.js 中處理
                break;
        }
    }
};

// ========== Scroll to Top ==========
const ScrollToTop = {
    init() {
        const btn = document.getElementById('scroll-top-btn');
        
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                btn.classList.add('visible');
            } else {
                btn.classList.remove('visible');
            }
        });
        
        btn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
};

// ========== 城市選擇器 ==========
document.getElementById('city-select').addEventListener('change', () => {
    Weather.loadWeather();
});

// ========== 應用初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    Auth.init();
    Navigation.init();
    ScrollToTop.init();
    
    // 初始化各個模組
    if (typeof UploadUI !== 'undefined') UploadUI.init();
    if (typeof WardrobeUI !== 'undefined') WardrobeUI.init();
    if (typeof RecommendationUI !== 'undefined') RecommendationUI.init();
});

// ========== 全局錯誤處理 ==========
window.addEventListener('error', (event) => {
    console.error('全局錯誤:', event.error);
    Toast.error('發生錯誤，請重新整理頁面');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('未處理的 Promise 拒絕:', event.reason);
    Toast.error('操作失敗，請稍後重試');
});
