"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Tavily API 配置
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# 微信公众号配置
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")
WECHAT_AUTHOR = os.environ.get("WECHAT_AUTHOR", "AI Daily Analyst")

# 搜索配置
SEARCH_DEPTH = "basic"  # basic 或 advanced
MAX_RESULTS = 10

# 每日分析配置
DAILY_TOPICS = [
    "AI 大模型",
    "GPT",
    "Claude",
    "Gemini",
    "OpenAI",
    "Anthropic",
    "Google AI",
    "Microsoft AI",
    "Meta AI",
]

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"
