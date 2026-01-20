// ========== API 配置 ==========
const API_BASE_URL = window.location.origin;

// ========== Streamlit 專用 API 封裝 ==========
const API = {
    // 🔥 使用 Query Parameters 傳遞數據（Streamlit 友好方式）
    async request(endpoint, params = {}) {
        // 構建 URL 查詢參數
        const queryString = new URLSearchParams({
            api: endpoint,
            ...params,
            _t: Date.now() // 防止緩存
        }).toString();
        
        const url = `${API_BASE_URL}?${queryString}`;
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const text = await response.text();
            
            // 嘗試解析 JSON
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error('無法解析 JSON:', text);
                throw new Error('服務器返回了無效的 JSON');
            }
        } catch (error) {
            console.error('API 請求失敗:', error);
            throw error;
        }
    },
    
    // ========== 認證 API ==========
    async login(username, password) {
        return this.request('login', {
            username: username,
            password: password
        });
    },
    
    async register(username, password) {
        return this.request('register', {
            username: username,
            password: password
        });
    },
    
    // ========== 天氣 API ==========
    async getWeather(city) {
        return this.request('weather', {
            city: city
        });
    },
    
    // ========== 衣櫥 API ==========
    async getWardrobe(userId) {
        return this.request('wardrobe', {
            user_id: userId
        });
    },
    
    async deleteItem(itemId, userId) {
        return this.request('delete_item', {
            item_id: itemId,
            user_id: userId
        });
    },
    
    async batchDeleteItems(itemIds, userId) {
        return this.request('batch_delete', {
            item_ids: JSON.stringify(itemIds),
            user_id: userId
        });
    },
    
    // ========== 上傳 API (特殊處理) ==========
    async uploadImages(files) {
        const user = AppState.getUser();
        if (!user) {
            throw new Error('請先登入');
        }
        
        // 🔥 對於文件上傳，我們需要使用 Base64 編碼
        const uploadPromises = files.map(async (file, index) => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result.split(',')[1];
                    resolve({
                        name: file.name,
                        data: base64,
                        type: file.type
                    });
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        });
        
        const filesData = await Promise.all(uploadPromises);
        
        return this.request('upload', {
            user_id: user.id,
            files: JSON.stringify(filesData)
        });
    },
    
    // ========== 推薦 API ==========
    async getRecommendation(city, style, occasion) {
        const user = AppState.getUser();
        return this.request('recommendation', {
            user_id: user.id,
            city: city,
            style: style || '不限定風格',
            occasion: occasion || '外出遊玩'
        });
    }
};

// ========== 圖片處理工具 ==========
const ImageUtils = {
    // 壓縮圖片
    async compressImage(file, maxWidth = 1200, maxHeight = 1200, quality = 0.8) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;
                    
                    // 計算縮放比例
                    if (width > height) {
                        if (width > maxWidth) {
                            height = height * (maxWidth / width);
                            width = maxWidth;
                        }
                    } else {
                        if (height > maxHeight) {
                            width = width * (maxHeight / height);
                            height = maxHeight;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    canvas.toBlob((blob) => {
                        resolve(new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        }));
                    }, 'image/jpeg', quality);
                };
                
                img.onerror = reject;
                img.src = e.target.result;
            };
            
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    // 生成預覽 URL
    createPreviewURL(file) {
        return URL.createObjectURL(file);
    },
    
    // 清理預覽 URL
    revokePreviewURL(url) {
        URL.revokeObjectURL(url);
    },
    
    // 驗證圖片文件
    validateImageFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!validTypes.includes(file.type)) {
            throw new Error(`不支援的檔案類型: ${file.type}`);
        }
        
        if (file.size > maxSize) {
            throw new Error(`檔案過大: ${(file.size / 1024 / 1024).toFixed(2)}MB (最大 10MB)`);
        }
        
        return true;
    }
};

// ========== 本地儲存工具 ==========
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('儲存失敗:', error);
        }
    },
    
    get(key) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error('讀取失敗:', error);
            return null;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('刪除失敗:', error);
        }
    },
    
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('清空失敗:', error);
        }
    }
};

// ========== 工具函數 ==========
const Utils = {
    // 防抖
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 節流
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // 格式化日期
    formatDate(date) {
        return new Date(date).toLocaleDateString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    },
    
    // 格式化檔案大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
};
