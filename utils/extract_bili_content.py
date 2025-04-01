import os
import sys
import re
import time
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.extract_bili_subtitle import download_subtitle_json
from utils.get_video import get_video_audio, extract_bvid

def extract_content_with_timeout(url, timeout=60):
    """带超时的内容提取函数"""
    result = [None]
    error = [None]
    
    def target():
        try:
            result[0] = extract_content_from_bili_internal(url)
        except Exception as e:
            error[0] = str(e)
            print(f"提取内容时出错: {e}", flush=True)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        print(f"提取内容超时 ({timeout}秒)", flush=True)
        return None
    
    if error[0]:
        print(f"提取内容失败: {error[0]}", flush=True)
        return None
        
    return result[0]

def extract_content_from_bili(url):
    """
    从B站视频链接中提取内容
    先尝试获取字幕，如果失败则下载音频并转换为文本
    """
    # 提取BVID
    print(f"开始从URL提取BVID: {url}")
    bvid = extract_bvid(url)
    if not bvid:
        print("无法从URL中提取BVID，请确认输入的是正确的B站视频链接")
        return None
    
    print(f"正在处理视频 {bvid}...")
    
    # 首先尝试获取字幕
    print("尝试获取视频字幕...")
    subtitle_text = download_subtitle_json(bvid)
    
    # 如果字幕获取成功
    if subtitle_text:
        print("成功获取字幕内容！")
        return subtitle_text
    
    # 如果字幕获取失败，尝试下载音频并转换为文本
    print("未找到字幕，尝试下载音频并转换为文本...")
    audio_text = get_video_audio(url)
    
    if audio_text:
        print("成功通过音频获取文本内容！")
        return audio_text
    else:
        print("无法获取视频内容，请检查链接或网络连接")
        return None

def extract_content_from_bili_internal(url):
    """
    从B站视频链接中提取内容
    先尝试获取字幕，如果失败则下载音频并转换为文本
    """
    # 提取BVID
    print(f"开始从URL提取BVID: {url}", flush=True)
    bvid = extract_bvid(url)
    if not bvid:
        print("无法从URL中提取BVID，请确认输入的是正确的B站视频链接", flush=True)
        return None
    
    print(f"正在处理视频 {bvid}...", flush=True)
    
    # 首先尝试获取字幕
    print("尝试获取视频字幕...", flush=True)
    subtitle_text = download_subtitle_json(bvid)
    
    # 如果字幕获取成功
    if subtitle_text:
        print("成功获取字幕内容！", flush=True)
        return subtitle_text
    
    # 如果字幕获取失败，尝试下载音频并转换为文本
    print("未找到字幕，尝试下载音频并转换为文本...", flush=True)
    audio_text = get_video_audio(url)
    
    if audio_text:
        print("成功通过音频获取文本内容！", flush=True)
        return audio_text
    else:
        print("无法获取视频内容，请检查链接或网络连接", flush=True)
        return None

def save_content_to_file(content, filename):
    """将内容保存到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"内容已保存到文件: {filename}")

def main(url=None):
    """
    主函数，接收一个B站链接作为参数
    如果没有提供链接，则请求用户输入
    """
    # 如果没有提供URL，则请求用户输入
    if not url:
        url = input("请输入B站视频链接: ")
    
    # 提取内容
    content = extract_content_from_bili(url)
    
    if content:
        # 提取BVID作为文件名
        bvid = extract_bvid(url)
        filename = f"{bvid}.txt" if bvid else "bili_content.txt"
        save_content_to_file(content, filename)
        
        # 打印内容摘要
        print("\n内容摘要（前300字符）:")
        print(content[:300] + "..." if len(content) > 300 else content)
        print("\n完整内容已保存到文件")
        
        return content
    else:
        print("无法获取内容，操作失败")
        return None

if __name__ == "__main__":
    # 如果直接运行脚本，不传入参数
    main("https://www.bilibili.com/video/BV1Pe411p7wa?spm_id_from=333.788.videopod.sections&vd_source=c6d90b1a6c0428ec8f3abdb9a71fac2f") 