import asyncio
from typing import List, Optional, Dict, Any
import re
import sys
import os

from openai import OpenAI


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.search.agentic_rag import agentic_rag
from utils.constants import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL


class ReactAgent:
    """
    ReAct (Reasoning and Acting) Agent for historical question answering.
    Uses a step-by-step approach to search for information and reason through answers.
    """
    
    BEGIN_SEARCH_QUERY = "<|begin_search_query|>"
    END_SEARCH_QUERY = "<|end_search_query|>"
    BEGIN_SEARCH_RESULT = "<|begin_search_result|>"
    END_SEARCH_RESULT = "<|end_search_result|>"
    
    def __init__(self, api_key: str = DASHSCOPE_API_KEY, 
                 base_url: str = DASHSCOPE_BASE_URL,
                 model: str = "qwen-plus",
                 max_search_attempts: int = 3,
                 db_path: str = None):
        """
        Initialize the ReactAgent.
        
        Args:
            api_key: API key for the LLM service
            base_url: Base URL for the LLM service
            model: Model name to use
            max_search_attempts: Maximum number of search attempts allowed
            db_path: Path to the user's database
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_search_attempts = max_search_attempts
        self.db_path = db_path
        
    def extract_between(self, text: str, start_tag: str, end_tag: str) -> Optional[list]:
        """
        Extract text between start and end tags.
        
        Args:
            text: Text to search in
            start_tag: Starting tag
            end_tag: Ending tag
            
        Returns:
            List of matches or None if no matches found
        """
        pattern = re.escape(start_tag) + r"(.*?)" + re.escape(end_tag)
        matches = re.findall(pattern, text, flags=re.DOTALL)
        if matches:
            return matches
        return None
    

    def extract_answer(self, text: str) -> Optional[list]:
        """
        Extract text between start and end tags.
        
        Args:
            text: Text to search in
            start_tag: Starting tag
            end_tag: Ending tag
            
        Returns:
            List of matches or None if no matches found
        """
        pattern = re.escape('<|start_answer|>') + r"(.*?)" + re.escape('<|end_answer|>')
        matches = re.findall(pattern, text, flags=re.DOTALL)
        if matches:
            return matches[0]
        return None
    
    def get_user_prompt(self, user_question: str, step: int, additional_info: str = ""):
        """
        Generate the prompt for the LLM.
        
        Args:
            user_question: The user's question
            step: Current step in the reasoning process
            additional_info: Additional information from previous steps
            
        Returns:
            Complete prompt for the LLM
        """
        instruction = (
            "您是一个历史学推理助手，能够搜索知识，帮助您准确回答用户的问题。\n\n"
            "你需要思考为了回答用户问题，需要先知道哪些信息，把这些信息拆解成多个问题，然后一次性分别搜索。\n\n"
            f"- 要执行搜索：在此处写下 {self.BEGIN_SEARCH_QUERY} 您的查询 {self.END_SEARCH_QUERY}。\n"
            f"然后，系统将搜索和分析相关文章，然后以以下格式为您提供有用的信息：{self.BEGIN_SEARCH_RESULT} ...搜索结果... {self.END_SEARCH_RESULT}。\n\n"
            f"如有必要，您可以多次重复搜索过程。搜索问题的最大次数限制为 {self.max_search_attempts}\n\n"
            "一旦您获得了所需的所有信息，请继续推理。\n\n"
            "示例：\n"
            "问题：\"卢沟桥事变为什么在918事变六年后才爆发\"\n"
            "助手思考步骤：\n"
            "- 我可能需要查找卢沟桥事变和918事变到卢沟桥事变中间发生的事情\n\n"
            "助手:\n"
            f"{self.BEGIN_SEARCH_QUERY}卢沟桥事变{self.END_SEARCH_QUERY}\n\n"
            f"{self.BEGIN_SEARCH_QUERY}1931年到1937年发生了什么{self.END_SEARCH_QUERY}\n\n"
            "（系统从相关网页返回处理后的信息）\n\n"
            "助手继续使用新信息进行推理……\n\n"
            "记住:\n"
            f"- 使用 {self.BEGIN_SEARCH_QUERY} 请求搜索{self.END_SEARCH_QUERY} 结束。\n"
            "- 搜索完成后，继续推理。\n\n"
            f"你可以一次搜索多个问题，分别用{self.BEGIN_SEARCH_QUERY} 和 {self.END_SEARCH_QUERY} 包裹"
        )

        user_prompt = (
            f"请回答以下问题。你应该一步一步思考如何解决它。一步一步搜索问题并解决问题\n\n"
            f"问题:\n{user_question}\n\n"
            f"当前是第{step}步"
        )

        if additional_info:
            user_prompt += f"\n\n在之前的步骤中，你做了下面这些是并获得了信息：\n{additional_info}"

        return instruction + '\n\n' + user_prompt
    
    async def generate_response(self, prompt: str) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response
        """
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    
    async def search(self, queries: List[str]) -> List[str]:
        """
        Perform search for a list of queries.
        
        Args:
            queries: List of search queries
           
        Returns:
            List of search results
        """
        return await agentic_rag(queries, self.db_path)
    
    async def run(self, user_question: str) -> str:
        """
        Run the ReAct agent to answer the user's question.
        
        Args:
            user_question: The user's question
           
        Returns:
            The final answer
        """
        output = ""
        step = 1

        while step <= self.max_search_attempts:
            # Generate prompt based on current state
            if output:
                prompt = self.get_user_prompt(user_question, step, output)
            else:
                prompt = self.get_user_prompt(user_question, step)

            # Get response from LLM
            res = await self.generate_response(prompt)
            print(res)
            output += res

            # Extract search queries if any
            search_queries = self.extract_between(res, self.BEGIN_SEARCH_QUERY, self.END_SEARCH_QUERY)

            if search_queries:
                # Perform searches
                search_results = await self.search(search_queries)

                # Add search results to output
                for query, result in zip(search_queries, search_results):
                    print(f"问题：{query}")
                    print(f"答案：{result}\n")
                    output += f"问题：{query}\n的答案为：{result}\n\n"
                
                step += 1
            else:
                # No more searches needed, we have the final answer
                break
        
        return res

    def set_db_path(self, db_path):
        """设置用户特定的数据库路径"""
        print(f"设置数据库路径：{db_path}")
        self.db_path = db_path
    
    async def query(self, query_text):
        try:
            # 使用设置的数据库路径或默认路径
            
            return await self.run(query_text)
        except Exception as e:
            print(f"查询出错: {e}")
            return "抱歉，查询过程中出现错误。"

async def search_agent(user_question: str) -> str:
    """
    Legacy function to maintain backward compatibility.
    
    Args:
        user_question: The user's question
        
    Returns:
        The answer to the user's question
    """
    agent = ReactAgent()
    return await agent.run(user_question)


if __name__ == "__main__":
    asyncio.run(search_agent(user_question="张作霖死后，中国是什么局势"))
