from openai import OpenAI
from typing import Dict, Optional
import os
import sys

from utils.constants import KIMI_API_KEY, DASHSCOPE_API_KEY
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import ConfigManager

class LLMProcessor:
    def __init__(self, api_keys: Dict[str, str] = None, base_url: str = "https://api.deepseek.com"):
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 用户提供的API keys优先级最高
        self.user_api_keys = api_keys or {}
        
        # Model configurations
        self.model_configs = {
            "kimi": {
                "api_key": KIMI_API_KEY,
                "base_url": "https://api.moonshot.cn/v1",
                "model": "moonshot-v1-8k"
            },
            "dashscope": {
                "api_key": DASHSCOPE_API_KEY,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-plus"
            }
        }
        
        self.prompt_templates = {
            "raw_text_process": {
                "system_prompt_file": "prompts/raw_text_process_prompts.txt",
                "user_prompt_template": "请总结下面这篇文章: \n{text}"
            },
            "events_summary": {
                "system_prompt_file": "prompts/events_summary_prompts.txt",
                "user_prompt_template": "请分析总结下面这个事件: \n{text}"
            },
            "relations": {
                "system_prompt_file": "prompts/relations_process_prompts.txt",
                "user_prompt_template": " "
            }
        }
        

    def _load_system_prompt(self, prompt_file: str) -> str:
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"提示词文件未找到: {prompt_file}")

    def generate_response(self, task_type: str, text: str, model_type: str = "deepseek", output_format: str = None, **kwargs) -> str:
        """
        Unified function to generate responses using different models.
        
        Args:
            task_type: Type of task to perform
            text: Input text to process
            model_type: Type of model to use ('deepseek', 'zhipu', 'kimi', 'dashscope')
            output_format: Optional output format specification
        """
        if task_type not in self.prompt_templates:
            raise ValueError(f"不支持的任务类型: {task_type}")
        
        if model_type not in self.model_configs:
            raise ValueError(f"不支持的模型类型: {model_type}")

        config = self.model_configs[model_type]
        
        # Special handling for zhipu model
        
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url")
        )

        # Prepare prompts
        template = self.prompt_templates[task_type]
        system_prompt = self._load_system_prompt(template["system_prompt_file"])
        user_prompt = template["user_prompt_template"].format(text=text)

        
        user_prompt = system_prompt + '\n\n' + user_prompt

        for key, value in kwargs.items():
            placeholder = f"<{key}>"
            user_prompt = user_prompt.replace(placeholder, str(value))

        # Handle JSON format if specified
        response_format = None
        if output_format == 'json':
            response_format = {'type': 'json_object'}
            

        # Handle dashscope's retry logic
        
        try_count = 0
        while try_count < 3:
            try:
                response = self._make_api_call(client, config["model"], user_prompt, response_format)
                return response.choices[0].message.content
            except Exception as e:
                print(f"第{try_count}次尝试失败: {e}")
                try_count += 1
                if try_count >= 3:
                    return None
    
        # response = self._make_api_call(client, config["model"], system_prompt, user_prompt, response_format)
        # return response.choices[0].message.content

    def _make_api_call(self, client, model, user_prompt, response_format):
        """Helper method to make the API call with consistent parameters"""
        return client.chat.completions.create(
            model=model,
            messages=[
            #    {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format
        )

if __name__ == "__main__":
    processor = LLMProcessor()
    config = processor.model_configs["kimi"]
        
   