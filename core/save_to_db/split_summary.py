import os
import lancedb
import sys
from langchain.text_splitter import RecursiveCharacterTextSplitter


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.general_utils import generate_id_from_chinese
from utils.get_emb import get_emb
import lancedb



# def load_documents(directory):
#     """加载文档"""
#     loader = TextLoader(directory, encoding='utf-8')
#     return loader.load()

from openai import OpenAI


def generate_summary(context, current_chunk):
    prompt = f"""
    请根据文章的前文摘要和当前的文章段落，生成一个当前段落的总结。
    前文摘要：{context}
    当前段落：{current_chunk}
    
    注意不要输出可能审查不通过的内容
    """

    api_key="sk-969b5d0c33774991b4f417aa185a2f8c"

    client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
    n = 0
    while n < 3:
        n += 1
        try:
            completion = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{'role': 'user', 'content': prompt}]
                )

            print(completion.choices[0].message.content)
            
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            continue
        
    return '无当前段落内容总结'

def process_chunks(splits):
    
    chunks = []
    summaries = []
    
    context = "这是第一段"
    
    for current_chunk in splits:
       
       
       summary = generate_summary(context, current_chunk)
       summaries.append(summary)
       chunks.append(current_chunk)
       context = summary
       
    return summaries, chunks


def split_documents(text):
    """分割文档"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=600,
        length_function=len
    )
    splits = text_splitter.split_text(text)
    return splits


    
async def store_embedding(emb_list, id_list, summary_list, chunk_list, doc_title, uri: str):
    print(f"store_embedding called with {len(emb_list)} embeddings for doc: {doc_title}")
    
    # 确保使用绝对路径
    if not os.path.isabs(uri):
        # 获取当前工作目录
        current_dir = os.getcwd()
        uri = os.path.join(current_dir, uri)
        print(f"Converting to absolute path: {uri}")
    
    data_list = []
    for i in range(len(id_list)):
        data_list.append({"vector": emb_list[i], "item": id_list[i], "summary": summary_list[i], "chunk": chunk_list[i], "doc_title": doc_title, "flag": 1})
        
    try:
        db = await lancedb.connect_async(uri)
        print(f"Connected to database successfully")
    except Exception as conn_err:
        print(f"Database connection error: {str(conn_err)}")
        print(f"Error type: {type(conn_err).__name__}")
        raise
        
    # 其余代码保持不变
    print(f"Getting table names")
    try:
        table_names = await db.table_names()
        print(f"Connected to database. Tables: {table_names}")
    except Exception as table_err:
        print(f"Error getting table names: {str(table_err)}")
        print(f"Error type: {type(table_err).__name__}")
        raise

    if "article_segment_emb_table" not in table_names:
        print("Creating new table: article_segment_emb_table")
        try:
            await db.create_table("article_segment_emb_table", data=data_list)
            print("Table created successfully")
        except Exception as create_err:
            print(f"Error creating table: {str(create_err)}")
            print(f"Error type: {type(create_err).__name__}")
            print(f"First data item structure: {data_list[0].keys() if data_list else 'No data'}")
            raise
    else:
        print("Opening existing table: article_segment_emb_table")
        try:
            tbl = await db.open_table("article_segment_emb_table")
            print(f"Adding {len(data_list)} records to existing table")
            await tbl.add(data_list)
            print("Records added successfully")
        except Exception as add_err:
            print(f"Error adding records: {str(add_err)}")
            print(f"Error type: {type(add_err).__name__}")
            raise
   

async def process_summary(text: str, doc_name: str, uri: str):
    splits = split_documents(text)
    summaries, chunks = process_chunks(splits)


    emb_list = []
    id_list = []

    for i in range(len(chunks)):
            chunk_id = generate_id_from_chinese(chunks[i])
            chunk = chunks[i]
            
            emb = get_emb(chunk)
            emb_list.append(emb)
            id_list.append(chunk_id)
            
    await store_embedding(emb_list, id_list, summaries, chunks, doc_name, uri)
    

    
