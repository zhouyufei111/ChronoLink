from dotenv import load_dotenv
import os

load_dotenv()


DASHSCOPE_API_KEY = os.getenv("dashscope_api_key")
DASHSCOPE_BASE_URL = os.getenv("dashscope_base_url")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
KIMI_API_KEY = os.getenv("kimi_api_key")
KIMI_BASE_URL = os.getenv("kimi_base_url")
COZE_API_KEY = os.getenv("coze_api_key")
XUNFEI_KEY = os.getenv("xunfei_key")
XUNFEI_APPID = os.getenv("xunfei_appid")
