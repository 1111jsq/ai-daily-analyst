"""
配置文件
"""
import os
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")
WECHAT_AUTHOR = os.environ.get("WECHAT_AUTHOR", "AI Daily Analyst")

SEARCH_DEPTH = "basic"
MAX_RESULTS = 10

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
    "具身智能",
    "智能体 Agent",
]

TECH_CATEGORIES = {
    "大模型": ["大模型", "LLM", "GPT", "Claude", "Gemini", "MoE", "模型训练", "模型发布"],
    "具身智能": ["具身智能", "机器人", "人形机器人", "自动驾驶", "具身AI"],
    "智能体": ["智能体", "Agent", "AI Agent", "多智能体", "自主决策"],
    "应用落地": ["AI应用", "落地", "商业化", "产品发布", "行业应用"],
    "算力基础设施": ["算力", "GPU", "芯片", "训练集群", "推理优化"],
    "开源动态": ["开源", "Meta", "Llama", "Mistral", "Qwen", "模型权重"],
}

LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"

def load_sources_config() -> dict:
    sources_path = CONFIG_DIR / "sources.yaml"
    if sources_path.exists():
        with open(sources_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

SOURCES_CONFIG = load_sources_config()
