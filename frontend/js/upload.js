// ========== 上傳頁面 UI 邏輯 ==========
const UploadUI = {
    selectedFiles: [],
    uploadedFiles: new Set(),
    maxFiles: 10,
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('batch-upload-btn');
        
        // 點擊上傳區域打開文件選擇
        uploadZone.addEventListener('click', (e) => {
            if (e.target.closest('.upload-placeholder')) {
                fileInput.click();
            }
        });
        
        // 文件選擇
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });
        
        // 拖放上傳
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('drag-over');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            this.handleFileSelect(e.dataTransfer.files);
        });
        
        // 批量上傳按鈕
        uploadBtn.addEventListener('click', () => {
            this.handleBatchUpload();
        });
    },
    
    handleFileSelect(files) {
        const fileArray = Array.from(files);
        
        // 檢查數量限制
        if (fileArray.length > this.maxFiles) {
            Toast.error(`一次最多只能上傳 ${this.maxFiles} 張照片，您選擇了 ${fileArray.length} 張`);
            return;
        }
        
        // 驗證文件
        const validFiles = [];
        for (const file of fileArray) {
            try {
                ImageUtils.validateImageFile(file);
                
                // 檢查是否已上傳過
                if (!this.uploadedFiles.has(file.name)) {
                    validFiles.push(file);
                } else {
                    Toast.warning(`${file.name} 已上傳過，已自動過濾`);
                }
            } catch (error) {
                Toast.error(`${file.name}: ${error.message}`);
            }
        }
        
        if (validFiles.length === 0) {
            Toast.info('沒有有效的新文件');
            return;
        }
        
        this.selectedFiles = validFiles;
        this.renderPreview();
        this.showUploadActions();
    },
    
    renderPreview() {
        const preview = document.getElementById('upload-preview');
        const placeholder = document.getElementById('upload-placeholder');
        
        placeholder.style.display = 'none';
        preview.style.display = 'grid';
        preview.innerHTML = '';
        
        this.selectedFiles.forEach((file, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item';
            
            const img = document.createElement('img');
            img.src = ImageUtils.createPreviewURL(file);
            img.alt = file.name;
            
            const info = document.createElement('div');
            info.className = 'preview-info';
            
            const name = document.createElement('p');
            name.className = 'preview-name';
            name.textContent = file.name;
            
            const size = document.createElement('p');
            size.className = 'preview-size';
            size.textContent = Utils.formatFileSize(file.size);
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'preview-remove';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = () => this.removeFile(index);
            
            info.appendChild(name);
            info.appendChild(size);
            previewItem.appendChild(img);
            previewItem.appendChild(info);
            previewItem.appendChild(removeBtn);
            preview.appendChild(previewItem);
        });
    },
    
    removeFile(index) {
        const file = this.selectedFiles[index];
        const url = document.querySelectorAll('.preview-item img')[index].src;
        ImageUtils.revokePreviewURL(url);
        
        this.selectedFiles.splice(index, 1);
        
        if (this.selectedFiles.length === 0) {
            this.hideUploadActions();
            document.getElementById('upload-placeholder').style.display = 'flex';
            document.getElementById('upload-preview').style.display = 'none';
        } else {
            this.renderPreview();
            this.updateUploadCount();
        }
    },
    
    showUploadActions() {
        document.getElementById('upload-actions').style.display = 'block';
        this.updateUploadCount();
    },
    
    hideUploadActions() {
        document.getElementById('upload-actions').style.display = 'none';
    },
    
    updateUploadCount() {
        document.getElementById('upload-count').textContent = 
            `已選擇 ${this.selectedFiles.length} 張照片`;
    },
    
    async handleBatchUpload() {
        if (this.selectedFiles.length === 0) {
            Toast.warning('請先選擇要上傳的圖片');
            return;
        }
        
        AppState.setLoading(true);
        
        try {
            // 壓縮圖片
            Toast.info('正在壓縮圖片...');
            const compressedFiles = await Promise.all(
                this.selectedFiles.map(file => ImageUtils.compressImage(file))
            );
            
            // 上傳
            Toast.info(`正在上傳 ${compressedFiles.length} 張圖片...`);
            const result = await API.uploadImages(compressedFiles);
            
            if (result.success) {
                // 記錄已上傳的文件
                this.selectedFiles.forEach(file => {
                    this.uploadedFiles.add(file.name);
                });
                
                // 清空當前選擇
                this.selectedFiles = [];
                
                // 重置 UI
                document.getElementById('upload-placeholder').style.display = 'flex';
                document.getElementById('upload-preview').style.display = 'none';
                this.hideUploadActions();
                
                // 清空文件輸入
                document.getElementById('file-input').value = '';
                
                // 顯示結果
                Toast.success(`🎉 成功上傳 ${result.success_count} 件衣服！`);
                
                if (result.duplicate_count > 0) {
                    Toast.warning(`已過濾 ${result.duplicate_count} 件重複衣服`);
                }
                
                if (result.fail_count > 0) {
                    Toast.error(`${result.fail_count} 件上傳失敗`);
                }
                
                // 顯示詳細結果
                if (result.items && result.items.length > 0) {
                    this.showUploadResults(result.items);
                }
                
            } else {
                Toast.error(result.message || '上傳失敗');
            }
            
        } catch (error) {
            console.error('上傳錯誤:', error);
            Toast.error('上傳失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },
    
    showUploadResults(items) {
        // 在頁面上顯示上傳結果
        const resultsHTML = `
            <div class="upload-results">
                <h3>✅ 上傳成功的衣服</h3>
                <div class="results-grid">
                    ${items.map(item => `
                        <div class="result-item">
                            <p class="result-name">${item.name}</p>
                            <p class="result-category">${item.category} | ${item.color}</p>
                            <p class="result-warmth">${'🔥'.repeat(item.warmth)}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        // 插入到上傳區域下方
        const resultsContainer = document.createElement('div');
        resultsContainer.innerHTML = resultsHTML;
        
        const uploadZone = document.getElementById('upload-zone');
        const existingResults = document.querySelector('.upload-results');
        if (existingResults) {
            existingResults.remove();
        }
        uploadZone.after(resultsContainer.firstElementChild);
        
        // 3秒後自動淡出
        setTimeout(() => {
            const results = document.querySelector('.upload-results');
            if (results) {
                results.style.transition = 'opacity 0.5s';
                results.style.opacity = '0';
                setTimeout(() => results.remove(), 500);
            }
        }, 5000);
    }
};
