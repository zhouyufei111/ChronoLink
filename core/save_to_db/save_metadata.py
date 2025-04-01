import asyncio
import os
import json
from typing import Dict, List, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.get_emb import get_emb
import lancedb


def extract_metadata_fields(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract required fields from metadata.json"""
    texts = []
    for title,event_data in metadata.items():
        fields = ['character_thought', 'author_view', 'summary', 'time']
        for field in fields:
            if field in event_data and event_data[field]:
                texts.append({'title': title,'field': field, 'text': event_data[field]})
    return texts

async def save_relations(relations: List[Dict[str, Any]], user_db_path: str):
    relations_list = []
    for relation_dict in relations:
        event_1 = relation_dict['event_1']
        event_2 = relation_dict['event_2']
        relation = relation_dict['relation']
        relations_list.append({'event_1': event_1, 'event_2': event_2, 'relation': relation})

    db = await lancedb.connect_async(user_db_path)
    if "relations_table" not in await db.table_names():
        await db.create_table("relations_table", data=relations_list)
        tbl = await db.open_table("relations_table")
        await tbl.add(relations_list)
        
    else:
        tbl = await db.open_table("relations_table")
        result = await tbl.query().where('event_1 = "{}" and event_2 = "{}"'.format(event_1, event_2)).limit(1).to_pandas()
        if result.empty:
            
            await tbl.add(relations_list)
        else:
            print("关系已存在")


async def save_metadata_emb(metadata: Dict[str, Any], saving_dir, user_db_path: str):
    texts_with_vectors = []

    db = await lancedb.connect_async(user_db_path)
    
    texts = extract_metadata_fields(metadata)

    for text in texts:

        text_with_vector = text.copy()
        text_with_vector['vector'] = get_emb(text['text'])
        text_with_vector['event'] = saving_dir
        texts_with_vectors.append(text_with_vector)


    if "detail_table" not in await db.table_names():
        await db.create_table("detail_table", data=texts_with_vectors)
    else:
        tbl = await db.open_table("detail_table")
                       
        await tbl.add(texts_with_vectors)


if __name__ == "__main__":

    async def test():
        uri = "data/user_1/lancedb"
        db = await lancedb.connect_async(uri)
        # tbl = await db.open_table("detail_table")

        # result = await tbl.query().limit(1000).to_pandas()
        
        # print(result)


        tbl = await db.open_table("relations_table")
        result = await tbl.query().limit(1000).to_pandas()
        result_list = result.to_dict('records')
        print(result_list)

        # result_list = result_list[:10]
        # await db.drop_table("detail_table")
        # await db.create_table("detail_table", data=result_list)

        

    asyncio.run(test())
