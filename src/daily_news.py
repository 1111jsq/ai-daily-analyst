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
    SOURCES_CONFIG,
)

from .web_fetcher import NewsCollector

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
        
        self.news_collector = NewsCollector(SOURCES_CONFIG)

    def search_topic(self, topic: str, days: int = 1) -> List[Dict]:
        if not self.client:
            return {"answer": "", "results": []}
        
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
            return {"answer": "", "results": []}

    def collect_daily_news(self, date: Optional[datetime] = None) -> Dict:
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        all_results = {
            "date": date_str,
            "topics": {},
            "ai_answer": "",
            "articles": [],
        }

        web_articles = self.news_collector.collect(max_items=15)
        if web_articles:
            logger.info(f"从Web源获取 {len(web_articles)} 条新闻")
            all_results["articles"].extend(web_articles)

        if self.client:
            for topic in DAILY_TOPICS[:5]:
                logger.info(f"正在搜索: {topic}")
                result = self.search_topic(topic)
                if result:
                    all_results["topics"][topic] = result
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

        if all_results["topics"]:
            first_topic = list(all_results["topics"].values())[0]
            all_results["ai_answer"] = first_topic.get("answer", "")

        if not all_results["ai_answer"] and web_articles:
            all_results["ai_answer"] = f"今日AI领域共收集{len(web_articles)}条最新资讯，涵盖智能体、大模型等技术领域。"

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
            content += f"{i}. {article['title']}\n"
            if source:
                content += f"   🔗 {source}\n"
            content += "\n"

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
    
    print("Daily news generated!")
    print(f"Date: {result['date']}")
    print(f"WeChat article: {result['wechat_path']}")
    print(f"Full article: {result['article_path']}")
    print(f"Articles collected: {result['articles_count']}")


if __name__ == "__main__":
    main()
