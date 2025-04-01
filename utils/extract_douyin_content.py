import json
import requests

import time

from utils.constants import COZE_API_KEY

def submit_request(video_url: str):
    bot_id = "7480052971145855027"

    url = "https://api.coze.cn/v3/chat"
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "additional_messages": [
            {
                "content_type": "text",
                "content": video_url,
                "role": "user",
                "type": "question"
            }
        ],
        "bot_id": bot_id,
        "user_id": "123",
        "stream": False
    }

    response = requests.post(url, headers=headers, json=data)

    # 检查响应状态
    if response.status_code == 200:
        result = response.json()
        print(result)
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)
        
        
    chat_id = result['data']['id']
    conversation_id = result['data']['conversation_id']


    return chat_id, conversation_id

def retrieve_status(chat_id: str, conversation_id: str):
    url_retrieve = "https://api.coze.cn/v3/chat/retrieve"
    
    url_get = "https://api.coze.cn/v3/chat/message/list"
    params = {
        "conversation_id": conversation_id,
        "chat_id": chat_id
    }
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(url_retrieve, headers=headers, params=params)
    if response.status_code == 200:
        while True:
            response = requests.get(url_retrieve, headers=headers, params=params)
            result = response.json()['data']['status']
            if result == "completed":
                break
            else:
                time.sleep(3)
        

        response = requests.get(url_get, headers=headers, params=params)
        if response.status_code == 200:
            result = response.json()['data'][2]['content']
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return response.text
    else:
        print(f"请求失败，状态码: {response.status_code}")
        return response.text

def get_video_text(video_url: str):
    chat_id, conversation_id = submit_request(video_url)
    return retrieve_status(chat_id, conversation_id)

def get_web_text(web_url: str):
    chat_id, conversation_id = submit_request(web_url)
    return json.loads(retrieve_status(chat_id, conversation_id))['content']


if __name__ == "__main__":
    import re
    text = "https://v.douyin.com/i5WkKBEM/"
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    douyin_urls = [url for url in urls if 'douyin.com' in url or 'iesdouyin.com' in url]
    get_video_text(douyin_urls[0])
