import asyncio
import json
import lancedb
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.get_emb import get_emb



async def search_author_view(event_list: list[str] = [], db_path=None):

    """
    搜索作者观点

    Args:
        event_list (list[str]): 事件列表
        db_path (str): 数据库路径

    Returns:
        str: 作者观点
    """
    
   
    
    # 检查数据库路径是否存在
    if not os.path.exists(db_path):
        return json.dumps([], ensure_ascii=False)
    
    try:
        # 连接到LanceDB
        db = await lancedb.connect_async(db_path)
        
        # 检查表是否存在
        if "detail_table" not in await db.table_names():
            return json.dumps([], ensure_ascii=False)
        
        tbl = await db.open_table("detail_table")


    

        for event in event_list:
            result = await tbl.search(get_emb(event))
            result = await result.limit(10).where("field='author_view'").to_pandas()
            
            thought_text_list = []


            for index, row in result.iterrows():
                event = row['event']
                text = row['text']

                thought_text_list.append(f"事件\"{event}\"中，作者的观点是：{text}")

    
        return '\n\n'.join(thought_text_list)
    
    except Exception as e:
        print(f"搜索时出错: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    




if __name__ == "__main__":
    print(asyncio.run(search_author_view(event_list = ["直皖战争"], db_path = 'data/user_1/lancedb')))


