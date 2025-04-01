from typing import List
import os
import sys

from utils.constants import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from scipy.spatial.distance import cosine
from openai import OpenAI
import asyncio
import lancedb




async def check_exists_event(new_event: str, time_dir: str, user_db_path: str) -> bool:
    """检查新事件是否在事件列表中"""

    try:
        
        new_emb = get_emb(new_event)

        db = await lancedb.connect_async(user_db_path)
        if "event_table" not in await db.table_names():
            tbl = await db.create_table("event_table", data=[{"vector": new_emb, "event": new_event, "time": time_dir}])
        else:
            tbl = await db.open_table("event_table")
    
            search_result = await tbl.search(new_emb)
            result = await search_result.where(f"time = '{time_dir}'").limit(1).to_pandas()

            if result.empty:
                await tbl.add([{"vector": new_emb, "event": new_event, "time": time_dir}])
                return False
        
            sim = 1 - cosine(new_emb, result['vector'][0])
            
            if sim > 0.8:
                return result['event'][0]
            else:
                await tbl.add([{"vector": new_emb, "event": new_event, "time": time_dir}])
                return False
  
    except Exception as e:
        print(f"检查事件时出错: {e}", new_event, time_dir, user_db_path)
        

def get_emb(text: str) -> List[float]:
    

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL)

    completion = client.embeddings.create(
        model="text-embedding-v3",
        input=text,
        dimensions=1024,
        encoding_format="float"
    )


    
    return completion.data[0].embedding


if __name__ == "__main__":

    asyncio.run(check_exists_event("张作霖在皇姑屯被炸死，张学良接班后改旗易帜 ", "1911", "data/user_1/lancedb"))
   