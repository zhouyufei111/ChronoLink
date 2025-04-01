
import asyncio
import lancedb
import sys
import json
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.get_emb import get_emb



async def search_character_thought(event_list: list[str] = [], character_list: list[str] = [], db_path: str = None) -> str:
    """
    搜索人物（对某件事的）思想

    Args:
        event_list (list[str]): 事件列表
        character_list (list[str]): 人物列表
        db_path (str): 数据库路径

    Returns:
        str: 人物（对某件事的）思想
    """

    res = []

    if not os.path.exists(db_path):
        return json.dumps([], ensure_ascii=False)
    
    try:
        
        db = await lancedb.connect_async(db_path)
        
      
        if "detail_table" not in await db.table_names():
            return json.dumps([], ensure_ascii=False)
        
        tbl = await db.open_table("detail_table")

        if event_list:

            for event in event_list:
                result = await tbl.search(get_emb(event))
                result = await result.limit(10).where("field='character_thought'").to_pandas()
                
                thought_text_list = result['text'].tolist()

                for text in thought_text_list:
                    for character in character_list:
                        if character in text:
                            res.append(text)

        else:
            result = await tbl.query().limit(1000).where("field='character_thought'").to_pandas()

            
            for index, row in result.iterrows():
                event_str = ''
                event = row['event']
                text = row['text']

                for single_thought in text.split("；"):
                    for character in character_list:
                        if character in single_thought:
                            if event not in event_str:
                                event_str += f"在事件\"{event}\"中，{single_thought}；"
                            else:
                                event_str += f"{single_thought}；"
                res.append(event_str)
               
        return '\n\n'.join(res)

    except Exception as e:
            print(f"搜索时出错: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
   




if __name__ == "__main__":
    print(asyncio.run(search_character_thought(character_list = ["张作霖"], db_path = "data/user_1/lancedb")))


