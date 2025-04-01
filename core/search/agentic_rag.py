"""
AgenticRAG - 基于代理的检索增强生成模块

该模块提供了一个智能检索系统，能够根据用户问题自动选择合适的检索工具，
并通过大语言模型生成回答。
"""

import json
import asyncio
import sys
import os
from typing import List, Dict, Any, Callable, Optional
from openai import AsyncOpenAI

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.search.rag_search import search_query
from core.search.time_search import search_by_time
from core.search.thought_search import search_character_thought
from core.search.view_search import search_author_view
from utils.constants import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL


class AgenticRAG:
    """
    基于代理的检索增强生成系统
    
    该类实现了智能检索和回答生成的功能，能够根据用户问题自动选择合适的检索工具。
    """
    
    def __init__(self, model_name: str = "qwen-plus"):
        """
        初始化AgenticRAG实例
        
        Args:
            model_name: 使用的大语言模型名称
        """
        self.model_name = model_name
        self.client = AsyncOpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL
        )
        self.tools = self._define_tools()
        self.available_functions = {
            "search_query": search_query,
            "search_by_time": search_by_time,
            "search_character_thought": search_character_thought,
            "search_author_view": search_author_view
        }
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        定义可用的检索工具
        
        Returns:
            工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_query",
                    "description": "当用户希望检索某个历史事件信息时，使用该工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户问题"
                            }
                        },
                        "required": ["query"]
                    }
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_by_time",
                    "description": "当用户希望检索某个时间点或者时间范围的历史事件信息时，使用该工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_list": {
                                "type": "array",
                                "description": "时间列表，例如['1927','1928']",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["time_list"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_character_thought",
                    "description": "当用户希望检索某个历史人物的思想时，或历史人物对某个事件的看法时，使用该工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_list": {
                                "type": "array",
                                "description": "人物列表 如:['人物A','人物B']",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "event_list": {
                                "type": "array",
                                "description": "事件列表 如:['事件A','事件B']",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["character_list", "event_list"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_author_view",
                    "description": "当用户希望获得关于某件事的观点时，使用该工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_list": {
                                "type": "array",
                                "description": "事件列表 如:['事件A','事件B']",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["event_list"]
                    }
                }
            }
        ]
    
    async def process_single_question(self, question: str, db_path: str) -> str:
        """
        处理单个问题
        
        Args:
            question: 用户问题
            db_path: 数据库路径
            
        Returns:
            str: 问题的回答
        """
        messages = []
        prompt = f"""
        你是一个历史知识检索助手，需要通过用户的问题判断检索内容的方式,并回答问题。
        不要使用你原有的知识，所有的信息都要来自检索到的文本内容。
        问题：{question}
        """
        
        # 添加用户的提问到消息列表
        messages.append({'role': 'user', 'content': prompt})
        
        try:
            # 第一次调用：决定使用哪个工具
            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,  
                tools=self.tools, 
                parallel_tool_calls=False
            )
            
            response = completion.choices[0].message
            tool_calls = response.tool_calls
            
            # 如果需要调用工具
            if tool_calls:
                function_name = tool_calls[0].function.name
                function_args = json.loads(tool_calls[0].function.arguments)
                function_args['db_path'] = db_path
                
                # 调用相应的检索函数
                function_response = await self.available_functions[function_name](**function_args)
                
                # 添加工具调用结果到消息列表
                messages.append(response)
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                    "tool_call_id": tool_calls[0].id,
                })
                
                # 第二次调用：生成最终回答
                second_response = await self.client.chat.completions.create(
                    model=self.model_name, 
                    messages=messages,
                )
                
                final_response = second_response.choices[0].message.content
                
                # 格式化输出
                return f"""
                问题：
                {question}

                答案：
                {final_response}

                _____________________________________________________________________________
                """
            else:
                # 如果不需要调用工具，直接返回回答
                return response.content
                
        except Exception as e:
            return f"处理问题时发生错误: {str(e)}"
    
    async def process_questions(self, question_list: List[str], db_path: str) -> List[str]:
        """
        并发处理多个问题
        
        Args:
            question_list: 问题列表
            db_path: 数据库路径
            
        Returns:
            包含所有问题答案的列表
        """
        tasks = []
        for question in question_list:
            task = self.process_single_question(question, db_path)
            tasks.append(task)
        
        # 并发执行所有问题的处理
        results = await asyncio.gather(*tasks)
        
        return results


async def agentic_rag(question_list: List[str], db_path: str) -> List[str]:
    """
    处理问题列表的便捷函数
    
    Args:
        question_list: 问题列表
        db_path: 数据库路径
        
    Returns:
        包含所有问题答案的列表
    """
    rag_system = AgenticRAG()
    return await rag_system.process_questions(question_list, db_path)


# 使用示例
async def main():
    """示例函数"""
    questions = [
        "1937年发生了什么？",
        "博古的主要思想是什么？",
        "讲一下卢沟桥事变"
    ]
    db_path = "path/to/your/database"
    
    results = await agentic_rag(questions, db_path)
    for question, answer in zip(questions, results):
        print(f"问题：{question}")
        print(f"答案：{answer}\n")


if __name__ == "__main__":
    asyncio.run(main())

