import asyncio
import os
import json
import lancedb
import sys

async def search_by_time(time_list: list[str], db_path: str) -> str:
    """
    按时间搜索事件
    
    Args:
        time_list: 时间列表
        user_id: 用户ID，如果为None则尝试从Flask上下文获取
        
    Returns:
        str: 匹配的事件列表的JSON字符串
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
        
        # 打开表
        tbl = await db.open_table("detail_table")
        
        # 构建查询条件
        time_conditions = []
        for time in time_list:
            time_conditions.append(f'text like "%{time}%"')
        
        # 如果有时间条件，则执行查询
        if time_conditions:
            query_condition = " OR ".join(time_conditions)

            query_condition += " AND field='time'"

            result = await tbl.query().where(query_condition).to_pandas()
            
            event_list = result['event'].unique().tolist()

            for event in event_list:
                result = await tbl.query().where(f'event = "{event}"').to_pandas()

                content = ''
                for _, row in result.iterrows():
                    if row['field'] == 'time':
                        content += f'**事件时间：**\n   {row["text"]}\n\n'
                    elif row['field'] == 'summary':
                        content += f'**事件总结：**\n   {row["text"]}\n\n'
                    

            return content
    
    except Exception as e:
        print(f"搜索时出错: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

if __name__ == "__main__":
    
    res = asyncio.run(search_by_time(["1927", "1928"], "data/user_1/lancedb"))
    print(res)

