import requests
import re
import json
from lxml import etree
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.video_to_text import RequestApi

def extract_bvid(url):
    """从B站URL中提取BVID"""
    print(f"尝试从URL提取BVID: {url}", flush=True)
    
    # 直接匹配BV开头的ID
    bv_pattern = r'BV\w{10}'
    match = re.search(bv_pattern, url)
    if match:
        bvid = match.group(0)
        print(f"成功提取BVID: {bvid}", flush=True)
        return bvid
    
    # 处理短链接 b23.tv
    if 'b23.tv' in url:
        try:
            print("检测到B站短链接，尝试解析...", flush=True)
            import requests
            response = requests.head(url, allow_redirects=True)
            final_url = response.url
            print(f"短链接解析为: {final_url}", flush=True)
            return extract_bvid(final_url)  # 递归调用处理解析后的URL
        except Exception as e:
            print(f"解析短链接时出错: {e}", flush=True)
            return None
    
    print(f"无法从URL提取BVID: {url}", flush=True)
    return None

def get_video_audio(url):
    """获取B站视频的音频并转为文本"""
    headers = {
        "referer": "https://www.bilibili.com",
        "origin": "https://www.bilibili.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
    }

    # 提取BVID
    bvid = extract_bvid(url)
    if not bvid:
        print("无法从URL中提取BVID，请确认输入的是正确的B站视频链接")
        return None

    # 第一步 请求视频网页的地址，拿到网页数据
    resp_ = requests.get(url, headers=headers)
    resp = resp_.text
    resp_.close()
    tree = etree.HTML(resp)

    # 第二步 从网页数据中提取视频标题
    try:
        title = tree.xpath('//h1/text()')[0]
        print(f"视频标题: {title}")
    except:
        print("无法提取视频标题")

    # 第三步 从网页数据中提取视频url和音频url
    try:
        tree1 = tree.xpath('/html/head/script[3]/text()')[0]
        tree1 = re.sub(r'window.__playinfo__=', '', tree1)
        tree1 = json.loads(tree1)
    except:
        try:
            tree1 = tree.xpath('/html/head/script[4]/text()')[0]
            tree1 = re.sub(r'window.__playinfo__=', '', tree1)
            tree1 = json.loads(tree1)
        except:
            print("无法提取视频信息")
            return None

    try:
        video = tree1['data']['dash']['video'][0]
        video_url = video.get('backupUrl', [video.get('baseUrl')])[0]
        print("获取到视频URL")

        audio = tree1['data']['dash']['audio'][0]
        audio_url = audio.get('backupUrl', [audio.get('baseUrl')])[0]
        print("获取到音频URL")
    except:
        print("无法提取视频或音频URL")
        return None

    # 下载音频
    audio_file = f"{bvid}.wav"
    response = requests.get(audio_url, headers=headers, stream=True)

    if response.status_code == 200:
        # 以二进制写入模式打开文件
        with open(audio_file, 'wb') as file:
            # 逐块写入文件
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"音频文件已成功保存为 {audio_file}")
        
        # 调用API获取文本
        api = RequestApi(upload_file_path=audio_file)
        text = api.get_result()
        
        # 删除音频文件
        os.remove(audio_file)
        print(f"已删除音频文件 {audio_file}")
        
        return text
    else:
        print(f"请求失败，状态码: {response.status_code}")
        return None

if __name__ == "__main__":
    # 获取用户输入的B站链接
    url = input("请输入B站视频链接: ")
    text = get_video_audio(url)
    if text:
        print("\n转换后的文本内容:")
        print(text)
    else:
        print("无法获取视频文本")