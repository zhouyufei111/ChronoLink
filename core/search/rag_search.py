import asyncio
import os
import json
from scipy.spatial.distance import cosine
import sys
from openai import OpenAI
import lancedb

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.get_emb import get_emb
from core.search.bm25_search import BM25

from utils.constants import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL

class TimelineQuerySystem:
    def __init__(self,  api_key=DASHSCOPE_API_KEY):
        self.client = OpenAI(
            api_key=api_key,
            base_url=DASHSCOPE_BASE_URL
        )
        self.emb_list = []
        self.name_list = []
        self.text_list = []
        self.db = None
        self.bm25 = BM25()
        # Don't call async methods in __init__

    @classmethod
    async def create(cls, db_path, api_key="sk-969b5d0c33774991b4f417aa185a2f8c"):
        """Async factory method to properly initialize the class"""
        instance = cls(api_key)
        await instance.connect_db(db_path)
        await instance._load_text()
        return instance

    async def connect_db(self, db_path=None):
        
        if not os.path.exists(db_path):
            print(f"Database path does not exist: {db_path}")
            self.db = None
            return
        
        # Connect to LanceDB
        self.db = await lancedb.connect_async(db_path)

    async def _load_text(self):
        """Load all text from the timeline data"""
    

        tbl = await self.db.open_table("article_segment_emb_table")
      
        result = await tbl.query().limit(1000).to_pandas()
        self.text_list = result['summary'].tolist()


    async def find_similar_events(self, query, similarity_threshold=0.8, top_k=3):
        """Find similar events based on query embedding"""
        query_emb = get_emb(query)
      
        tbl = await self.db.open_table("detail_table")

        result = await tbl.search(query_emb)
        result_detail = await result.limit(top_k).to_pandas()

        detail_list = []
        for index, row in result_detail.iterrows():
            if row['field'] == 'summary':
                detail_list.append(f"事件总结：{row['text']}")
            elif row['field'] == 'character_thought':
                detail_list.append(f"事件人物的想法：{row['text']}")
            elif row['field'] == 'author_view':
                detail_list.append(f"作者的观点：{row['text']}")

        tbl2 = await self.db.open_table("article_segment_emb_table")

        result = await tbl2.search(query_emb)
        result_summary = await result.limit(top_k).to_pandas()

        return detail_list + result_summary['summary'].tolist()
  


    async def find_similar_events_by_bm25(self, query):
        """Find similar events based on BM25"""
        self.bm25.add_corpus(self.text_list)
        score_list = self.bm25.get_scores(query)
        
        # 创建带索引的元组列表并排序
        indexed_scores = list(enumerate(score_list))
        sorted_scores = sorted(indexed_scores, key=lambda x: x[1], reverse=True)
        
    
        return [self.text_list[idx] for idx, score in sorted_scores[:3] if score > 0.2]

        

    def get_ai_response(self, query, content):
        """Get AI response for the query based on content"""
        prompt = f"""
        根据文本的内容，回答用户问题
        文本内容：{content}
        用户问题：{query}

        """
        try:
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[{'role': 'user', 'content': prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error getting AI response: {e}"

    async def search_query(self, query: str) -> str:
        """
        处理用户查询并返回结果
        
        Args:
            query: 用户查询
            
        Returns:
            str: 查询结果
        """
       
        
        # Find similar events
        kw_events = await self.find_similar_events_by_bm25(query)
        similar_events = await self.find_similar_events(query)

        all_events = kw_events + similar_events

        if not all_events:
            return "没有查询到相关内容"

        
        content = "\n\n".join(all_events)
        
       
        return content

async def search_query(query, db_path):
    
    
    system = await TimelineQuerySystem.create(db_path)
    response = await system.search_query(query)
    print(response)

    return response


async def search_in_raw_data( query):
    """Search in raw data"""
    query_emb = get_emb(query)
    uri = "data/lancedb"
    db = lancedb.connect(uri)
    tbl = db.open_table("article_segment_emb_table")
    result = tbl.search(query_emb).limit(3).to_pandas()
    return result['summary'].tolist()



def quick_test_load_text():
    system = TimelineQuerySystem()
    print(system.find_similar_events_by_bm25("卢沟桥事变为什么在918事变六年后才爆发"))

if __name__ == "__main__":
    asyncio.run(search_query('张作霖','data/user_1/lancedb'))
