from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g, Response
from core.search.react_agent import ReactAgent
import os
import json
from core.event_process.raw_text_process import EventProcessor
from utils.llm_api import LLMProcessor
from utils.sql_connector import SQLConnector  
import re
import lancedb
from utils.status_manager import StatusManager
import time
from dotenv import load_dotenv
import asyncio

load_dotenv()


app = Flask(__name__)
# query_system = TimelineQuerySystem()
search_agent = ReactAgent()
llm_processor = LLMProcessor()

# Session配置
app.secret_key = 'zhouyufei'  # 替换为你的secret key

# 初始化状态管理器
status_manager = StatusManager()

# 在请求前设置全局用户ID
@app.before_request
def set_user_data():
    """在每个请求前设置用户数据"""
    g.user_id = None
    g.user_db_path = None
    
    if 'loggedin' in session and 'id' in session:
        g.user_id = session['id']
        user_dir = ensure_user_data_dir(g.user_id)
        g.user_db_path = os.path.join(user_dir, 'lancedb')

# 创建数据库连接函数
def get_db_connection():
    return SQLConnector(
        host=os.getenv("MYSQL_HOST"),
        port=3306,
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )



# 确保用户数据目录存在
def ensure_user_data_dir(user_id):
    """确保用户的数据目录存在"""
    user_dir = os.path.join('data', f'user_{user_id}')
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(os.path.join(user_dir, 'raw_data'), exist_ok=True)
    os.makedirs(os.path.join(user_dir, 'lancedb'), exist_ok=True)
    return user_dir

@app.route('/')
def home():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # 确保用户数据目录存在
    if 'id' in session:
        ensure_user_data_dir(session['id'])
        
    return render_template('index.html', username=session['username'])

@app.route('/get_directory_structure')
async def get_directory_structure():
    print("✓ 获取目录结构")
    try:
        if not g.user_id:
            return jsonify({'error': '请先登录'}), 401
        
        # 使用全局变量中的用户数据库路径
        user_db_path = g.user_db_path
        print(user_db_path)
        
        # 如果用户的lancedb目录不存在或为空，返回空列表
        if not os.path.exists(user_db_path) or not os.listdir(user_db_path):
            return jsonify([])
        
        print("✓ 连接数据库")
        try:
            db_lance = await lancedb.connect_async(user_db_path)
            # 检查表是否存在
            if "detail_table" not in await db_lance.table_names():
                return jsonify([])
            print("✓ 确保detail_table表存在")
            tbl = await db_lance.open_table("detail_table")
            result = await tbl.query().where('field = "summary"').limit(1000).to_pandas()
       

            timeline_data = []
            event_list = []
            for index, row in result.iterrows():
                time = await tbl.query().where('field = "time" and event = "{}"'.format(row['event'])).limit(1000).to_pandas()
                if row['event'] not in event_list:
                    event_list.append(row['event'])
                
                    timeline_data.append({
                        "title": row["title"],
                        "time": time.iloc[0]['text'],
                        "event": row["text"],
                        "file": row['event'],
                        "dir": time.iloc[0]['text']
                    })

            timeline_data.sort(key=lambda x: x['time'])
         
            return jsonify(timeline_data)
        except Exception as e:
            print(f"获取用户时间线数据出错: {e}")
           
            return jsonify([])
            
    except Exception as e:
        print(f"获取目录结构时出错: {e}")
    
        return jsonify({'error': str(e)}), 500
    


async def get_relate_events(event, user_db_path):
    db = await lancedb.connect_async(user_db_path)
    tbl = await db.open_table("relations_table")
    result = await tbl.query().where('event_1 = "{}"'.format(event)).limit(1000).to_pandas()
    
    related_items = []
    for index, row in result.iterrows():
        related_items.append({
            "event": row['event_2'],
            "reason": row['relation']
        })
    
    return related_items

@app.route('/get_file_content', methods=['POST'])
async def get_file_content():
    if not g.user_id:
        return jsonify({'error': '请先登录'}), 401
    
    try:
        data = request.json
        file_name = data.get('file')
        
        if not file_name:
            return jsonify({'error': '未提供文件名'}), 400
            
        # 使用全局变量中的用户数据库路径
        db_lance = await lancedb.connect_async(g.user_db_path)
        if "detail_table" not in await db_lance.table_names():
            return jsonify({'error': '未找到数据表'}), 404
            
        tbl = await db_lance.open_table("detail_table")
        result = await tbl.query().where(f'event = "{file_name}"').to_pandas()
        
        if result.empty:
            return jsonify({'error': '未找到文件内容'}), 404
        
        # 按照title分组内容
        content_by_title = {}
        
        for index, row in result.iterrows():
            title = row.get('title', '未命名')
            
            if title not in content_by_title:
                content_by_title[title] = {}
            
            if row['field'] == 'summary':
                content_by_title[title]['summary'] = row["text"]
            elif row['field'] == 'character_thought':
                content_by_title[title]['character_thought'] = row["text"]
            elif row['field'] == 'author_view':
                content_by_title[title]['author_view'] = row["text"]
            elif row['field'] == 'time':
                content_by_title[title]['time'] = row["text"]

        # 获取相关事件
        print("获取相关事件")
        print(file_name)
        related_events = await get_relate_events(file_name, g.user_db_path)
        print(related_events)
        return jsonify({
            'content_by_title': content_by_title,
            'related_events': related_events
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status_stream')
def status_stream():
    """SSE端点，用于发送处理状态更新"""
    if not g.user_id:
        return jsonify({'error': '请先登录'}), 401
    
    # 在生成器函数外部获取用户ID，这样它就不依赖于请求上下文
    user_id = g.user_id
        
    def generate():
        # 使用闭包中的 user_id 而不是 g.user_id
        print(f"Starting status stream for user {user_id}")
        
        # 发送一个初始心跳，确保连接建立
        yield f"data: {json.dumps({'status': 'connected', 'type': 'heartbeat'})}\n\n"
        
        # 立即发送一个初始状态
        initial_status = status_manager.get_status(user_id) or "等待操作..."
        yield f"data: {json.dumps({'status': initial_status, 'type': 'status'})}\n\n"
        last_status = initial_status
        
        # 设置超时计数器和心跳计数器
        timeout_counter = 0
        heartbeat_counter = 0
        max_timeout = 600  # 增加到600秒超时，给予更多处理时间
        
        try:
            while True:
                # 每5次循环发送一次心跳（更频繁的心跳）
                heartbeat_counter += 1
                if heartbeat_counter >= 5:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                    heartbeat_counter = 0
                
                current_status = status_manager.get_status(user_id)
                
                if current_status != last_status and current_status is not None:
                    print(f"Status changed from {last_status} to {current_status}, sending update")
                    yield f"data: {json.dumps({'status': current_status, 'type': 'status'})}\n\n"
                    last_status = current_status
                    timeout_counter = 0  # 重置超时计数器
                    
                    # 如果状态是"完成"或"错误"，结束流
                    if current_status == "完成" or current_status == "错误":
                        print(f"Process completed or error occurred, ending stream")
                        # 发送最终状态后等待1秒再结束，确保客户端收到
                        time.sleep(1)
                        # 清除状态
                        status_manager.clear_status(user_id)
                        break
                else:
                    timeout_counter += 1
                    if timeout_counter >= max_timeout:
                        print(f"Status stream timeout for user {user_id}")
                        # 不发送超时消息，只记录日志
                        break
                        
                # 减少轮询间隔，使状态更新更及时
                time.sleep(0.5)
        except GeneratorExit:
            print(f"Client closed connection for user {user_id}")
        except Exception as e:
            print(f"Error in status stream for user {user_id}: {e}")
            yield f"data: {json.dumps({'status': '连接错误', 'type': 'error', 'message': str(e)})}\n\n"
        finally:
            print(f"Status stream ended for user {user_id}")
    
    response = Response(generate(), mimetype='text/event-stream')
    # 添加必要的头信息，防止缓存
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/upload', methods=['POST'])
async def upload_file():
    if not g.user_id:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = g.user_id  # 获取用户ID
    user_dir = ensure_user_data_dir(user_id)
    user_raw_data_dir = os.path.join(user_dir, 'raw_data')
    
    try:
        data = request.json
        filename = data.get('filename')
        text = data.get('text')
        
        if not filename or not text:
            return jsonify({'error': '文件名或内容不能为空'}), 400
        
        # 设置初始状态
        status_manager.set_status(user_id, "准备处理...")
        
        # 提取链接的正则表达式
        import re
        url_pattern = re.compile(r'https?://[^\s]+')
        
        # 检查是否包含抖音链接
        if 'douyin.com' in text or 'iesdouyin.com' in text:
            # 提取链接
            urls = url_pattern.findall(text)
            douyin_urls = [url for url in urls if 'douyin.com' in url or 'iesdouyin.com' in url]
            
            if douyin_urls:
                status_manager.set_status(user_id, "正在从抖音链接提取内容")
                try:
                    from utils.extract_douyin_content import get_video_text
                    extracted_text = get_video_text(douyin_urls[0])  # 使用第一个找到的抖音链接
                    if extracted_text:
                        text = extracted_text
                        print(f"已从抖音链接提取内容，长度: {len(text)}")
                        if len(text) < 100:
                            status_manager.set_status(user_id, "错误")
                            return jsonify({'error': f'{text}'}), 400
                    else:
                        status_manager.set_status(user_id, "错误")
                        return jsonify({'error': '无法从抖音链接提取内容'}), 400
                except Exception as e:
                    print(f"抖音内容提取错误: {str(e)}")
                    status_manager.set_status(user_id, "错误")
                    return jsonify({'error': f'抖音内容提取错误: {str(e)}'}), 500
            else:
                status_manager.set_status(user_id, "错误")
                return jsonify({'error': '文本中包含抖音关键词但未找到有效链接'}), 400
        
        # 检查是否包含B站链接
        elif 'bilibili.com' in text or 'b23.tv' in text:
            # 提取链接
            urls = url_pattern.findall(text)
            bili_urls = [url for url in urls if 'bilibili.com' in url or 'b23.tv' in url]
            
            if bili_urls:
                status_manager.set_status(user_id, "正在从B站链接提取内容")
                try:
                    from utils.extract_bili_content import extract_content_from_bili
                    extracted_text = extract_content_from_bili(bili_urls[0])  # 使用第一个找到的B站链接
                    if extracted_text:
                        text = extracted_text
                        print(f"已从B站链接提取内容，长度: {len(text)}")
                    else:
                        status_manager.set_status(user_id, "错误")
                        return jsonify({'error': '无法从B站链接提取内容'}), 400
                except Exception as e:
                    print(f"B站内容提取错误: {str(e)}")
                    status_manager.set_status(user_id, "错误")
                    return jsonify({'error': f'B站内容提取错误: {str(e)}'}), 500
            else:
                status_manager.set_status(user_id, "错误")
                return jsonify({'error': '文本中包含B站关键词但未找到有效链接'}), 400
            
        elif 'https://' in text:
            status_manager.set_status(user_id, "正在从网页链接提取内容")
            try:
                from utils.extract_douyin_content import get_web_text
                urls = url_pattern.findall(text)
                extracted_text = get_web_text(urls[0])
                if extracted_text:
                    text = extracted_text
                    print(f"已从网页链接提取内容，长度: {len(text)}")
                else:
                    status_manager.set_status(user_id, "错误")
                    return jsonify({'error': '无法从网页链接提取内容'}), 400
            except Exception as e:
                print(f"网页内容提取错误: {str(e)}")
                status_manager.set_status(user_id, "错误")
                return jsonify({'error': f'网页内容提取错误: {str(e)}'}), 500

        try:
            # 更新状态：开始处理内容
            status_manager.set_status(user_id, "正在处理内容")
            
            # 创建处理器实例
            processor = EventProcessor()
            
            # 更新状态：分析文本
            status_manager.set_status(user_id, "正在分析文本内容")
            
            # 处理文件 - 传递 user_id 参数
            user_db_path = os.path.join(user_dir, 'lancedb')
            print(f"处理文件: {filename}, 用户ID: {user_id}, 数据库路径: {user_db_path}")
            await processor.process_file(filename, text, user_db_path=user_db_path, user_id=user_id)
            
            # 更新状态：完成
            status_manager.set_status(user_id, "完成")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"处理文件时出错: {str(e)}")
            print(f"错误详情: {error_trace}")
            status_manager.set_status(user_id, "错误")
            return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 已成功上传并处理'
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"上传处理总体错误: {str(e)}")
        print(f"错误详情: {error_trace}")
        status_manager.set_status(user_id, "错误")
        return jsonify({'error': f'上传处理错误: {str(e)}'}), 500
        

@app.route('/query', methods=['POST'])
async def process_query():
    # 检查用户是否已登录
    if 'loggedin' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': '请输入查询内容'}), 400
    
    try:
        search_agent.set_db_path(g.user_db_path)
        response = await search_agent.run(query)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            db = get_db_connection()
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            data, _ = db.query(query)
            
            if data and len(data) > 0:
                # 将元组转换为字典
                account = {
                    'id': data[0][0],
                    'username': data[0][1],
                    'password': data[0][2]
                }
                
                # 登录成功后，session中设置用户信息
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                
                # 确保用户数据目录存在
                ensure_user_data_dir(session['id'])
                
                return redirect(url_for('home'))
            else:
                msg = '用户名或密码错误！'
        except Exception as e:
            print(f"登录过程中出错: {e}")
            msg = '登录过程中出错，请稍后重试'
            
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    # 清除session
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    
    # 清除全局变量不需要额外操作，因为每个请求都会重新设置
    
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            db = get_db_connection()
            
            # 检查用户名是否已存在
            check_query = f"SELECT * FROM users WHERE username = '{username}'"
            data, _ = db.query(check_query)
            
            if data and len(data) > 0:
                msg = '该用户名已存在！'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = '用户名只能包含字母和数字！'
            elif not username or not password:
                msg = '请填写完整信息！'
            else:
                # 使用execute方法直接执行插入操作
                insert_query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
                success = db.execute(insert_query)
                
                if success:
                    print(f"用户 {username} 注册成功")
                    msg = '注册成功！'
                    
                    # 验证数据是否已插入
                    verify_query = f"SELECT * FROM users WHERE username = '{username}'"
                    verify_data, _ = db.query(verify_query)
                    if verify_data:
                        print(f"验证成功: 用户 {username} 已存在于数据库中")
                    else:
                        print(f"验证失败: 用户 {username} 未找到")
                else:
                    msg = '注册失败，请稍后重试'
        except Exception as e:
            print(f"注册过程中出错: {e}")
            msg = f'注册过程中出错: {str(e)}'
            
    return render_template('register.html', msg=msg)

# 测试数据库连接
@app.route('/test_db')
def test_db():
    try:
        db = get_db_connection()
        data, _ = db.query("SELECT VERSION()")
        if data:
            return f"数据库连接成功！MySQL版本: {data[0][0]}"
        else:
            return "数据库连接成功，但未返回数据"
    except Exception as e:
        return f"数据库连接错误: {str(e)}", 500

# 删除 /settings 路由
@app.route('/settings')
def settings_page():
    """API设置页面"""
    print("访问设置页面")  # 添加调试信息
    try:
        return render_template('settings.html')
    except Exception as e:
        print(f"渲染设置页面时出错: {e}")  # 添加错误信息
        return f"渲染设置页面时出错: {e}", 500

# Add a placeholder route for set_api_key to prevent template errors
@app.route('/set_api_key')
def set_api_key():
    """Placeholder for API key settings page"""
    # Just redirect to home page since we're not using API keys anymore
    return redirect(url_for('home'))

if __name__ == '__main__':
    # get_file_content()


    # app.run(host='0.0.0.0', port=5000, debug=False) 
    app.run(debug=True, port=5002)