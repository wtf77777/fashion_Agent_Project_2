"""
Supabase 客戶端 - Database Client
統一管理資料庫連接,適用於 Streamlit Cloud
"""
from supabase import create_client, Client
from typing import Optional

class SupabaseClient:
    """Supabase 資料庫客戶端"""
    
    def __init__(self, url: str, key: str):
        """
        初始化 Supabase 客戶端
        
        Args:
            url: Supabase 專案 URL
            key: Supabase Anon Key
        """
        self.url = url
        self.key = key
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """
        獲取 Supabase 客戶端實例
        使用延遲初始化模式
        """
        if self._client is None:
            self._client = create_client(self.url, self.key)
        return self._client
    
    def test_connection(self) -> bool:
        """
        測試資料庫連接
        
        Returns:
            是否連接成功
        """
        try:
            # 嘗試查詢 users 表格
            result = self.client.table("users").select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Supabase 連接測試失敗: {str(e)}")
            return False
