import time
import threading
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StatusManager')

class StatusManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StatusManager, cls).__new__(cls)
                cls._instance.status_dict = {}
                logger.info("StatusManager instance created")
        return cls._instance
    
    def set_status(self, user_id, status):
        """设置用户的处理状态"""
        print(f"设置用户 {user_id} 的状态为: {status}")
        self.status_dict[user_id] = status
    
    def get_status(self, user_id):
        """获取用户的处理状态"""
        status = self.status_dict.get(user_id)
        return status
    
    def clear_status(self, user_id):
        """清除用户的处理状态"""
        if user_id in self.status_dict:
            print(f"清除用户 {user_id} 的状态")
            del self.status_dict[user_id] 