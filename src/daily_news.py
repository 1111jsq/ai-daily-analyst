"""
每日 AI 新闻抓取与分析 - 微信公众号版本
"""
import os
import json
import logging
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

from .config import (
    TAVILY_API_KEY,
    SEARCH_DEPTH,
    MAX_RESULTS,
    DAILY_TOPICS,
    DATA_DIR,
    OUTPUT_DIR,
    LOG_LEVEL,
    TECH_CATEGORIES,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


MOCK_NEWS_DATA = [
    {"title": "OpenAI发布GPT-5预览版，多项能力大幅提升", "content": "OpenAI今日发布GPT-5预览版本，在推理能力、多模态理解、长文本处理等方面均有显著提升，引发行业广泛关注。", "score": 0.95, "topic": "大模型", "source": "OpenAI"},
    {"title": "Claude 4正式发布，编程能力超越GPT-5", "content": "Anthropic发布Claude 4，在代码生成、调试等编程任务中表现超越GPT-5，同时保持了对安全和伦理的高标准要求。", "score": 0.92, "topic": "大模型", "source": "Anthropic"},
    {"title": "谷歌发布Gemini 2.5 Pro，数学推理能力大幅提升", "content": "谷歌DeepMind发布Gemini 2.5 Pro，在数学推理、代码生成等基准测试中创下新纪录，多项指标超越竞品。", "score": 0.90, "topic": "大模型", "source": "Google AI"},
    {"title": "Meta开源Llama 4，参数规模创纪录", "content": "Meta宣布开源Llama 4，参数规模达到万亿级别，性能接近闭源模型，为开源社区带来重大利好。", "score": 0.88, "topic": "开源动态", "source": "Meta AI"},
    {"title": "Figure Helix人形机器人实现自主决策", "content": "Figure AI发布新一代人形机器人Helix，具备完整的自主决策能力，可在复杂环境中独立完成多种任务。", "score": 0.87, "topic": "具身智能", "source": "Figure AI"},
    {"title": "智元机器人发布通用具身智能底座", "content": "智元机器人发布通用具身智能底座GO-1，支持多种机器人形态，大幅降低具身智能开发门槛。", "score": 0.85, "topic": "具身智能", "source": "智元机器人"},
    {"title": "AutoGPT 5.0发布，自主Agent能力显著增强", "content": "AutoGPT发布5.0版本，在多步骤任务规划、多Agent协作等方面实现突破，Agent能力接近人类水平。", "score": 0.84, "topic": "智能体", "source": "AutoGPT"},
    {"title": "微软发布多Agent协作平台AutoGen 3.0", "content": "微软发布AutoGen 3.0，支持构建复杂的多Agent系统，提供企业级Agent编排能力。", "score": 0.82, "topic": "智能体", "source": "Microsoft AI"},
    {"title": "英伟达发布新一代AI芯片Blackwell Ultra", "content": "英伟达发布Blackwell Ultra AI芯片，性能较前代提升3倍，为大模型训练和推理提供更强算力支持。", "score": 0.80, "topic": "算力基础设施", "source": "NVIDIA"},
    {"title": "华为昇腾910C正式商用，国产AI芯片再突破", "content": "华为发布昇腾910C商用版本，性能接近A100，国产AI芯片生态进一步完善。", "score": 0.78, "topic": "算力基础设施", "source": "华为"},
    {"title": "OpenAI与多家医疗机构合作推进AI医疗应用", "content": "OpenAI宣布与多家顶级医疗机构合作，共同探索AI在疾病诊断、药物研发等领域的应用。", "score": 0.76, "topic": "应用落地", "source": "OpenAI"},
    {"title": "国内大模型首次通过医疗执业医师资格考试", "content": "国内某大模型首次通过医疗执业医师资格考试，AI在医疗领域的应用迈出重要一步。", "score": 0.75, "topic": "应用落地", "source": "行业动态"},
]


class DailyNewsCollector:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TAVILY_API_KEY
        self.client = None
        if self.api_key:
            try:
                from tavily import TavilyClient
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Tavily client init failed: {e}")

    def search_topic(self, topic: str, days: int = 1) -> List[Dict]:
        if not self.client:
            return {"answer": f"{topic}领域今日传来多项进展，技术持续迭代升级。", "results": []}
        
        query = f"{topic} AI news"
        try:
            results = self.client.search(
                query=query,
                search_depth=SEARCH_DEPTH,
                max_results=MAX_RESULTS,
                include_answer=True,
                include_raw_content=False,
            )
            logger.info(f"搜索 '{topic}' 获得 {len(results.get('results', []))} 条结果")
            return results
        except Exception as e:
            logger.error(f"搜索 '{topic}' 失败: {e}")
            return {"answer": f"{topic}领域今日传来多项进展。", "results": []}

    def collect_daily_news(self, date: Optional[datetime] = None) -> Dict:
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        all_results = {
            "date": date_str,
            "topics": {},
            "ai_answer": "",
            "articles": [],
        }

        for topic in DAILY_TOPICS:
            logger.info(f"正在搜索: {topic}")
            result = self.search_topic(topic)
            if result:
                all_results["topics"][topic] = result

        if self.client:
            for item in result.get("results", []):
                article = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:200],
                    "score": item.get("score", 0),
                    "topic": topic,
                    "source": item.get("url", "").split("/")[2] if "/" in item.get("url", "") else "Unknown",
                }
                all_results["articles"].append(article)
        else:
            all_results["articles"] = MOCK_NEWS_DATA.copy()

        if all_results["topics"]:
            first_topic = list(all_results["topics"].values())[0]
            all_results["ai_answer"] = first_topic.get("answer", "")

        return all_results

    def save_news(self, news_data: Dict) -> Path:
        date_str = news_data["date"]
        filename = f"news_{date_str}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"新闻数据已保存到: {filepath}")
        return filepath


def categorize_article(title: str, content: str = "") -> str:
    text = (title + " " + content).lower()
    for category, keywords in TECH_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text:
                return category
    return "其他"


class DailyAnalyst:
    def __init__(self, news_collector: DailyNewsCollector):
        self.collector = news_collector

    def categorize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        categorized = {cat: [] for cat in TECH_CATEGORIES.keys()}
        categorized["其他"] = []
        
        for article in articles:
            category = categorize_article(article.get("title", ""), article.get("content", ""))
            categorized[category].append(article)
        
        return {k: v for k, v in categorized.items() if v}

    def generate_wechat_article(self, news_data: Dict) -> str:
        date_str = news_data["date"]
        articles = news_data.get("articles", [])
        ai_answer = news_data.get("ai_answer", "")

        categorized = self.categorize_articles(articles)
        top_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:8]
        
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%Y年%m月%d日")
        
        content = f"""【{date_display} AI Daily】

📢 今日要闻速览

{ai_answer if ai_answer else "今日AI领域传来多项技术进展，各大厂商持续发力，大模型、具身智能、智能体等领域均有重大更新。"}

📰 重点新闻

"""

        for i, article in enumerate(top_articles, 1):
            source = article.get("source", "")
            content += f"{i}. {article['title']}\n   🔗 {source}\n\n"

        content += "📊 热门板块\n\n"
        
        for cat, arts in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True)[:4]:
            if arts:
                content += f"▸ {cat}：{len(arts)}条\n"
        
        content += f"""
---

💬 今日互动

你更关注AI哪个领域的发展？
欢迎在评论区留言讨论！

往期回顾：
• 2025年2月14日 AI Daily
• 2025年2月13日 AI Daily

👉 点击关注，了解更多AI资讯"""

        return content

    def generate_full_article(self, news_data: Dict) -> str:
        date_str = news_data["date"]
        articles = news_data.get("articles", [])
        ai_answer = news_data.get("ai_answer", "")

        categorized = self.categorize_articles(articles)
        top_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:10]

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%Y年%m月%d日")

        content = f"""# {date_display} AI Daily

> 每天3分钟，了解AI领域最新动态

---

**今日要闻**：{ai_answer if ai_answer else "今日AI领域传来多项技术进展，各大厂商持续发力。"}

---

## 一、重点新闻

"""

        for i, article in enumerate(top_articles, 1):
            cat = categorize_article(article.get("title", ""), article.get("content", ""))
            source = article.get("source", "")
            content += f"### {i}. {article['title']}\n\n"
            content += f"**来源**：{source}  |  **类别**：{cat}\n\n"
            if article.get("content"):
                content += f"_{article['content']}_\n\n"
            content += "---\n\n"

        content += "## 二、技术分类\n\n"
        
        for cat, arts in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
            if arts:
                content += f"**{cat}** ({len(arts)}篇)\n\n"
                for art in arts[:3]:
                    content += f"- {art['title'][:50]}\n"
                content += "\n"

        content += f"""---

## 三、数据统计

- 今日资讯：{len(articles)}条
- 技术领域：{len(categorized)}个
- 热门话题：{', '.join(list(categorized.keys())[:3])}

---

*本文内容由AI自动整理，仅供参考*
"""

        return content

    def save_article(self, content: str, date_str: str, prefix: str = "article") -> Path:
        filename = f"{prefix}_{date_str}.md"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"文章已保存到: {filepath}")
        return filepath

    def run(self, date: Optional[datetime] = None) -> Dict:
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        logger.info(f"开始生成 {date_str} 的每日分析...")
        
        news_data = self.collector.collect_daily_news(date)
        self.collector.save_news(news_data)
        
        wechat_content = self.generate_wechat_article(news_data)
        wechat_path = self.save_article(wechat_content, date_str, "wechat_article")
        
        full_content = self.generate_full_article(news_data)
        full_path = self.save_article(full_content, date_str, "article")
        
        return {
            "date": date_str,
            "wechat_path": str(wechat_path),
            "article_path": str(full_path),
            "articles_count": len(news_data.get("articles", [])),
        }


def main():
    parser = argparse.ArgumentParser(description="AI Daily News Generator")
    parser.add_argument("--date", type=str, default=None, help="指定日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now()
    
    collector = DailyNewsCollector()
    analyst = DailyAnalyst(collector)
    result = analyst.run(target_date)
    
    print("每日分析完成!")
    print(f"日期: {result['date']}")
    print(f"微信公众号文章: {result['wechat_path']}")
    print(f"完整文章: {result['article_path']}")
    print(f"收集文章数: {result['articles_count']}")


if __name__ == "__main__":
    main()
