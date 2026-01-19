// ========== 推薦頁面 UI 邏輯 ==========
const RecommendationUI = {
    currentRecommendation: null,
    recommendedItems: [],
    currentItemIndex: 0,
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        // 獲取推薦按鈕
        document.getElementById('get-recommendation-btn').addEventListener('click', () => {
            this.handleGetRecommendation();
        });
        
        // 城市選擇變更時更新天氣
        document.getElementById('city-select').addEventListener('change', () => {
            Weather.loadWeather();
        });
    },
    
    async handleGetRecommendation() {
        const city = document.getElementById('city-select').value;
        const style = document.getElementById('style-input').value.trim();
        const occasion = document.getElementById('occasion-input').value.trim();
        
        AppState.setLoading(true);
        
        try {
            const result = await API.getRecommendation(city, style, occasion);
            
            if (result.success) {
                this.currentRecommendation = result.recommendation;
                this.recommendedItems = result.items || [];
                this.currentItemIndex = 0;
                
                this.renderRecommendation();
                Toast.success('✨ 穿搭推薦已生成！');
            } else {
                Toast.error(result.message || '獲取推薦失敗');
            }
        } catch (error) {
            console.error('推薦錯誤:', error);
            Toast.error('獲取推薦失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    renderRecommendation() {
        const resultContainer = document.getElementById('recommendation-result');
        const textContainer = document.getElementById('recommendation-text');
        const itemsContainer = document.getElementById('recommendation-items');
        
        // 顯示結果容器
        resultContainer.style.display = 'block';
        
        // 渲染推薦文字
        textContainer.innerHTML = this.formatRecommendationText(this.currentRecommendation);
        
        // 渲染推薦單品
        if (this.recommendedItems.length > 0) {
            this.renderCarousel();
        } else {
            itemsContainer.innerHTML = `
                <div class="no-items">
                    <p>💡 AI 推薦的衣物未在您的衣櫥中找到對應圖片</p>
                    <p>建議上傳更多衣服以獲得更精準的視覺化推薦</p>
                </div>
            `;
        }
        
        // 滾動到結果區域
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },
    
    formatRecommendationText(text) {
        // 將純文字轉換為 HTML 格式
        // 處理換行、列表等
        const lines = text.split('\n');
        let html = '';
        let inList = false;
        
        lines.forEach(line => {
            line = line.trim();
            if (!line) return;
            
            // 檢測標題 (以 ** 包圍或以 # 開頭)
            if (line.startsWith('**') && line.endsWith('**')) {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                const title = line.replace(/\*\*/g, '');
                html += `<h4>${title}</h4>`;
            }
            // 檢測列表項 (以 - 或 數字. 開頭)
            else if (line.match(/^[-*]\s/) || line.match(/^\d+\.\s/)) {
                if (!inList) {
                    html += '<ul>';
                    inList = true;
                }
                const content = line.replace(/^[-*]\s/, '').replace(/^\d+\.\s/, '');
                html += `<li>${content}</li>`;
            }
            // 普通段落
            else {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                html += `<p>${line}</p>`;
            }
        });
        
        if (inList) {
            html += '</ul>';
        }
        
        return html;
    },
    
    renderCarousel() {
        const container = document.getElementById('recommendation-items');
        
        container.innerHTML = `
            <div class="carousel-container">
                <button class="carousel-btn prev" onclick="RecommendationUI.prevItem()">
                    ◀
                </button>
                
                <div class="carousel-main">
                    <div class="carousel-indicator">
                        第 ${this.currentItemIndex + 1} / ${this.recommendedItems.length} 件
                    </div>
                    
                    <div class="carousel-item-display">
                        ${this.renderCurrentItem()}
                    </div>
                </div>
                
                <button class="carousel-btn next" onclick="RecommendationUI.nextItem()">
                    ▶
                </button>
            </div>
            
            <div class="carousel-dots">
                ${this.recommendedItems.map((_, index) => `
                    <button class="dot ${index === this.currentItemIndex ? 'active' : ''}"
                            onclick="RecommendationUI.goToItem(${index})">
                    </button>
                `).join('')}
            </div>
        `;
    },
    
    renderCurrentItem() {
        const item = this.recommendedItems[this.currentItemIndex];
        
        return `
            <div class="recommended-item">
                <div class="recommended-item-image">
                    <img src="data:image/jpeg;base64,${item.image_data}" 
                         alt="${item.name}">
                </div>
                <div class="recommended-item-info">
                    <h3>${item.name}</h3>
                    <div class="item-details">
                        <p><strong>類別:</strong> ${item.category}</p>
                        <p><strong>顏色:</strong> ${item.color}</p>
                        <p><strong>風格:</strong> ${item.style || 'N/A'}</p>
                        <p><strong>保暖度:</strong> ${'🔥'.repeat(item.warmth)}</p>
                    </div>
                </div>
            </div>
        `;
    },
    
    prevItem() {
        if (this.currentItemIndex > 0) {
            this.currentItemIndex--;
            this.renderCarousel();
        }
    },
    
    nextItem() {
        if (this.currentItemIndex < this.recommendedItems.length - 1) {
            this.currentItemIndex++;
            this.renderCarousel();
        }
    },
    
    goToItem(index) {
        this.currentItemIndex = index;
        this.renderCarousel();
    }
};
