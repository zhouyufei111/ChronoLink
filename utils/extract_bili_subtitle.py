
"""下载哔哩哔哩 字幕"""
import aiohttp
import math
import os
import time
import requests
import json


SESSDATA = "3cf3ef68%2C1754658835%2C8684a%2A22CjAiqm5wenSKSL1JeSceB1gLPPmxtwlW4A_l7oHkXWp-IRpyeXf02sbwZ4Pq6KKikKsSVjdldUZsZnEtaE94OVA0TWlLRHl5bndCenNzRnNLcG1SRHFwa3cya2tQMVBqTmZjRkM4Y0txSDA1bC1Kd2huc1kyQkRwMUxLQTlQV1FNTldSN1ktRkdBIIECi"
BUVID3 = "8CA892FD-E73E-D314-51E6-2EDDCAFC37D586535infoc"
BILI_JCT = "eaa52371f9a9230168b75f27d52978ba"
 
 
def convert_json_to_srt(json_files_path):
    """
    json 格式的字幕转为 srt 格式
    代码来源 https://www.jianshu.com/p/66450e9554f8
    """
    json_files = os.listdir(json_files_path)
    srt_files_path = os.path.join(json_files_path, 'srt')  # 更改后缀后字幕文件的路径
    isExists = os.path.exists(srt_files_path)
    if not isExists:
        os.mkdir(srt_files_path)
 
    for json_file in json_files:
        file_name = json_file.replace(json_file[-5:], '.srt')  # 改变转换后字幕的后缀
        file = ''  # 这个变量用来保存数据
        i = 1
        # 将此处文件位置进行修改，加上utf-8是为了避免处理中文时报错
        with open(os.path.join(json_files_path, json_file), encoding='utf-8') as f:
            datas = json.load(f)  # 加载文件数据
            f.close()
 
        for data in datas['body']:
            start = data['from']  # 获取开始时间
            stop = data['to']  # 获取结束时间
            content = data['content']  # 获取字幕内容
            file += '{}\n'.format(i)  # 加入序号
            hour = math.floor(start) // 3600
            minute = (math.floor(start) - hour * 3600) // 60
            sec = math.floor(start) - hour * 3600 - minute * 60
            minisec = int(math.modf(start)[0] * 100)  # 处理开始时间
            file += str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':' + str(sec).zfill(2) + ',' + str(
                minisec).zfill(2)  # 将数字填充0并按照格式写入
            file += ' --> '
            hour = math.floor(stop) // 3600
            minute = (math.floor(stop) - hour * 3600) // 60
            sec = math.floor(stop) - hour * 3600 - minute * 60
            minisec = abs(int(math.modf(stop)[0] * 100 - 1))  # 此处减1是为了防止两个字幕同时出现
            file += str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':' + str(sec).zfill(2) + ',' + str(
                minisec).zfill(2)
            file += '\n' + content + '\n\n'  # 加入字幕文字
            i += 1
        with open(os.path.join(srt_files_path, file_name), 'w', encoding='utf-8') as f:
            f.write(file)  # 将数据写入文件
 
 
def download_subtitle_json(bvid: str):
    """
    下载字幕
    """
    sub_dir = f'./{bvid}'
 
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.bilibili.com/video/{bvid}/?p=1',
        'Origin': 'https://www.bilibili.com',
        'Connection': 'keep-alive',
        # TODO 改为 自己的cookie , 通过浏览器的 network(网络) 复制
        'Cookie': """buvid3=4019139B-3B9C-7A75-1D65-5F5AA969D35338123infoc; b_nut=1726298338; bsource=search_google; _uuid=3B73F47F-1097A-D1EE-1042A-F69BABCD888238672infoc; CURRENT_FNVAL=4048; buvid_fp=24e0532299743050c1be068f80ed04aa; buvid4=A0726B37-5639-A07C-15E3-57A7DD58FEA132144-023112803-; rpdid=|(kRl|YRkJm0J'u~kYkm)JJm; b_lsid=2106F5249_1926A34D780; header_theme_version=CLOSE; enable_web_push=DISABLE; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Mjg2MTc5MTQsImlhdCI6MTcyODM1ODY1NCwicGx0IjotMX0.w9zC-Vl0Yz_QUKGb2LFXOKyOjpn33xXra3xI-ibChsc; bili_ticket_expires=1728617854; SESSDATA=0b504920%2C1743910741%2C9dc2e%2Aa1CjAlrAppgLYqI_Oz4HfM98RVvNCSAv9SenFzgIRsCZVu9IAcXYGiwEykiVBmd_LkLTMSVlVfMG9TSlhZNldiY0I4enIzVk1uX2ViaFI5RmxKMnVTdGZoS3JnYmxKQVdiWWNHSmdVVVVVc0F4dTIwM3NzMG1DSkE2UUYtUFBuRkxjeGJHaFh5VmFBIIEC; bili_jct=6e29f790c3c12c71597733fa06134aa7; DedeUserID=274791771; DedeUserID__ckMd5=538a540fe3df32b7; sid=5573cbax; CURRENT_QUALITY=116; bp_t_offset_274791771=985789324798722048; home_feed_column=4; browser_resolution=453-812""",
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    resp = requests.get(f'https://www.bilibili.com/video/{bvid}/', headers=headers)
    text = resp.text
    aid = text[text.find('"aid"') + 6:]
    aid = aid[:aid.find(',')]
    cid_back = requests.get("http://api.bilibili.com/x/player/pagelist?bvid={}".format(bvid), headers=headers)
    if cid_back.status_code != 200:
        print('获取 playlist 失败')
 
    cid_json = json.loads(cid_back.content)
    for item in cid_json['data']:
        cid = item['cid']
        title = item['part'] + '.json'
 
        params = {
            'aid': aid,
            'cid': cid,
            'isGaiaAvoided': 'false',
            'web_location': '1315873',
            'w_rid': '364cdf378b75ef6a0cee77484ce29dbb',
            'wts': int(time.time()),
        }
 
        wbi_resp = requests.get('https://api.bilibili.com/x/player/wbi/v2', params=params, headers=headers)
        if wbi_resp.status_code != 200:
            print('获取 字幕链接 失败')
            return None
        subtitle_links = wbi_resp.json()['data']["subtitle"]['subtitles']
        if subtitle_links:
            # 默认下载第一个字幕
            subtitle_url = "https:" + subtitle_links[0]['subtitle_url']
            subtitle_resp = requests.get(subtitle_url, headers=headers)
            # open(os.path.join(sub_dir, title), 'w', encoding='utf-8').write(subtitle_resp.text)

            subtitle_json = json.loads(subtitle_resp.text)
            output_text = ""
            for item in subtitle_json['body']:
                output_text += item['content'] + " "
            # with open(os.path.join("data", "raw_data", file_name), 'w', encoding='utf-8') as f:
            #     f.write(output_text)

 
            return output_text

async def fetch_bili_video_detail(url, session: aiohttp.ClientSession = None, timeout=300):
    """Fetch bilibili video detail with BiliGPT"""
    # Check if session is None and create a new session if needed
    if session is None:
        session = aiohttp.ClientSession()

    headers = {
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "bibigpt.co",
        "Connection": "keep-alive",
    }

    payload = {"url": url, "includeDetail": True}

    try:
        async with session.post(
            "https://bibigpt.co/api/open/tj4phge510o6/subtitle",
            headers=headers,
            json=payload,
            timeout=timeout,
        ) as response:
            if response.status == 200:
                output = await response.json()
                if output:
                    return output
            else:
                print(f"Received unexpected status code {response.status}")
                return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        # Close session if it was created in this function
        if session is not None:
            await session.close()


async def test_trans():
    await fetch_bili_video_detail("https://www.bilibili.com/video/BV1NS4y1M7Rc")
 
if __name__ == '__main__':
    # todo 改成需要下载的 bvid, https://www.bilibili.com/video/<bvid>

    # asyncio.run(test_trans())
    BVID = 'BV1NS4y1M7Rc'
    output_text = download_subtitle_json(BVID)
    # convert_json_to_srt(f'./{BVID}')