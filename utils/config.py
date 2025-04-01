import os
import json
from typing import Dict, Optional

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件，如果不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """创建默认配置"""
        default_config = {
            "api_keys": {
                "deepseek": "",
                "zhipu": "",
                "kimi": "",
                "dashscope": ""
            },
            "use_user_keys": False  # 是否使用用户提供的keys
        }
        
        # 保存默认配置
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取指定提供商的API key"""
        return self.config.get("api_keys", {}).get(provider, "")
    
    def get_use_user_keys(self) -> bool:
        """获取是否使用用户提供的keys"""
        return self.config.get("use_user_keys", False)
    
    def set_use_user_keys(self, use_user_keys: bool) -> None:
        """设置是否使用用户提供的keys"""
        self.config["use_user_keys"] = use_user_keys
        self._save_config(self.config) 