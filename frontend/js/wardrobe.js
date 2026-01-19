// ========== 衣櫥頁面 UI 邏輯 ==========
const WardrobeUI = {
    items: [],
    selectedItems: new Set(),
    isBatchDeleteMode: false,
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        // 刷新按鈕
        document.getElementById('refresh-wardrobe-btn').addEventListener('click', () => {
            this.loadWardrobe();
        });
        
        // 批量刪除按鈕
        document.getElementById('batch-delete-btn').addEventListener('click', () => {
            this.toggleBatchDeleteMode();
        });
    },
    
    async loadWardrobe() {
        AppState.setLoading(true);
        
        try {
            const result = await API.getWardrobe();
            
            if (result.success) {
                this.items = result.items || [];
                this.renderWardrobe();
                this.updateStats();
            } else {
                Toast.error('載入衣櫥失敗');
            }
        } catch (error) {
            console.error('載入衣櫥錯誤:', error);
            Toast.error('載入失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    renderWardrobe() {
        const grid = document.getElementById('wardrobe-grid');
        const emptyState = document.getElementById('wardrobe-empty');
        
        if (this.items.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        grid.innerHTML = '';
        
        this.items.forEach(item => {
            const card = this.createItemCard(item);
            grid.appendChild(card);
        });
    },
    
    createItemCard(item) {
        const card = document.createElement('div');
        card.className = 'wardrobe-item';
        card.dataset.itemId = item.id;
        
        // 批量刪除模式下的選擇框
        let checkboxHTML = '';
        if (this.isBatchDeleteMode) {
            const isSelected = this.selectedItems.has(item.id);
            checkboxHTML = `
                <div class="item-checkbox">
                    <input type="checkbox" 
                           id="check-${item.id}" 
                           ${isSelected ? 'checked' : ''}
                           onchange="WardrobeUI.toggleItemSelection(${item.id})">
                    <label for="check-${item.id}">選擇</label>
                </div>
            `;
        }
        
        card.innerHTML = `
            ${checkboxHTML}
            <div class="item-image">
                <img src="data:image/jpeg;base64,${item.image_data}" 
                     alt="${item.name}"
                     loading="lazy">
            </div>
            <div class="item-info">
                <h3 class="item-name">${item.name}</h3>
                <div class="item-details">
                    <p><strong>類別:</strong> ${item.category}</p>
                    <p><strong>顏色:</strong> ${item.color}</p>
                    <p><strong>風格:</strong> ${item.style || 'N/A'}</p>
                    <p><strong>保暖度:</strong> ${'🔥'.repeat(item.warmth)}</p>
                </div>
                ${!this.isBatchDeleteMode ? `
                    <button class="btn btn-secondary btn-delete" 
                            onclick="WardrobeUI.deleteItem(${item.id})">
                        🗑️ 刪除
                    </button>
                ` : ''}
            </div>
        `;
        
        return card;
    },
    
    updateStats() {
        // 更新統計資訊
        document.getElementById('total-items').textContent = this.items.length;
        
        // 計算分類統計
        const categories = {};
        this.items.forEach(item => {
            const cat = item.category || '其他';
            categories[cat] = (categories[cat] || 0) + 1;
        });
        
        // 更新統計網格
        const statsGrid = document.getElementById('wardrobe-stats');
        statsGrid.innerHTML = `
            <div class="stat-card">
                <span class="stat-label">總計</span>
                <span class="stat-value">${this.items.length}</span>
            </div>
            ${Object.entries(categories).map(([cat, count]) => `
                <div class="stat-card">
                    <span class="stat-label">${cat}</span>
                    <span class="stat-value">${count}</span>
                </div>
            `).join('')}
        `;
    },
    
    toggleBatchDeleteMode() {
        this.isBatchDeleteMode = !this.isBatchDeleteMode;
        
        const btn = document.getElementById('batch-delete-btn');
        
        if (this.isBatchDeleteMode) {
            btn.textContent = '✅ 完成選擇';
            btn.classList.add('btn-primary');
            btn.classList.remove('btn-secondary');
            this.selectedItems.clear();
        } else {
            btn.textContent = '🗑️ 批量刪除';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
            
            // 如果有選中的項目，執行刪除
            if (this.selectedItems.size > 0) {
                this.executeBatchDelete();
            }
        }
        
        // 重新渲染
        this.renderWardrobe();
    },
    
    toggleItemSelection(itemId) {
        if (this.selectedItems.has(itemId)) {
            this.selectedItems.delete(itemId);
        } else {
            this.selectedItems.add(itemId);
        }
        
        // 更新按鈕文字
        const btn = document.getElementById('batch-delete-btn');
        if (this.selectedItems.size > 0) {
            btn.textContent = `🗑️ 刪除選中的 ${this.selectedItems.size} 件`;
        } else {
            btn.textContent = '✅ 完成選擇';
        }
    },
    
    async deleteItem(itemId) {
        if (!confirm('確定要刪除這件衣服嗎？')) {
            return;
        }
        
        AppState.setLoading(true);
        
        try {
            const result = await API.deleteItem(itemId);
            
            if (result.success) {
                Toast.success('✅ 已刪除');
                // 從列表中移除
                this.items = this.items.filter(item => item.id !== itemId);
                this.renderWardrobe();
                this.updateStats();
            } else {
                Toast.error('刪除失敗');
            }
        } catch (error) {
            console.error('刪除錯誤:', error);
            Toast.error('刪除失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    async executeBatchDelete() {
        if (this.selectedItems.size === 0) {
            return;
        }
        
        if (!confirm(`確定要刪除選中的 ${this.selectedItems.size} 件衣服嗎？`)) {
            this.selectedItems.clear();
            this.isBatchDeleteMode = false;
            this.renderWardrobe();
            return;
        }
        
        AppState.setLoading(true);
        
        try {
            const itemIds = Array.from(this.selectedItems);
            const result = await API.batchDeleteItems(itemIds);
            
            if (result.success) {
                Toast.success(`✅ 已刪除 ${result.success_count} 件衣服`);
                
                if (result.fail_count > 0) {
                    Toast.warning(`⚠️ ${result.fail_count} 件刪除失敗`);
                }
                
                // 重新載入衣櫥
                await this.loadWardrobe();
                this.selectedItems.clear();
            } else {
                Toast.error('批量刪除失敗');
            }
        } catch (error) {
            console.error('批量刪除錯誤:', error);
            Toast.error('批量刪除失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    }
};
