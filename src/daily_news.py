"""
每日 AI 新闻抓取与分析
"""
import os
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

from tavily import TavilyClient

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


class DailyNewsCollector:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("Tavily API key is required")
        self.client = TavilyClient(api_key=self.api_key)

    def search_topic(self, topic: str, days: int = 1) -> List[Dict]:
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
            return {}

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
                for item in result.get("results", []):
                    article = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:200],
                        "score": item.get("score", 0),
                        "topic": topic,
                    }
                    all_results["articles"].append(article)

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

    def generate_trend_summary(self, categorized: Dict[str, List[Dict]]) -> str:
        summaries = []
        category_counts = {cat: len(articles) for cat, articles in categorized.items()}
        
        for category, articles in categorized.items():
            if not articles:
                continue
            top_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:3]
            summaries.append(f"**{category}** ({len(articles)}篇)")
            for art in top_articles:
                summaries.append(f"- {art['title'][:60]}...")
            summaries.append("")
        
        return "\n".join(summaries)

    def generate_analysis(self, news_data: Dict) -> str:
        date_str = news_data["date"]
        articles = news_data.get("articles", [])
        ai_answer = news_data.get("ai_answer", "")

        categorized = self.categorize_articles(articles)
        
        top_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:10]

        content = f"""# 每日 AI 动态分析 - {date_str}

## 今日 AI 领域要闻

"""

        if ai_answer:
            content += f"**AI 总结：**{ai_answer}\n\n"

        content += f"## 重点新闻 ({len(articles)}篇)\n\n"

        for i, article in enumerate(top_articles, 1):
            cat = categorize_article(article.get("title", ""))
            content += f"### {i}. {article['title']}\n"
            content += f"**来源：** {article.get('url', 'Unknown')[:50]}...\n"
            content += f"**类别：** {cat}\n"
            if article.get("content"):
                content += f"\n{article['content']}\n"
            content += "\n---\n\n"

        content += self.generate_trend_summary(categorized)

        content += f"""
## 类别分布

| 类别 | 文章数 |
|:---|:---:|
"""
        for cat, arts in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
            content += f"| {cat} | {len(arts)} |\n"

        content += f"""
---

## 分析结语

今日 AI 领域共收集到 **{len(articles)}** 条相关新闻，涵盖 {len(categorized)} 个技术领域。

**核心关注：** 本日新闻主要集中在 {', '.join(list(categorized.keys())[:3])} 等领域，展现出{"、".join(list(categorized.keys())[:2])}技术的快速发展趋势。

---
*本文由 AI 自动生成 | 发布日期：{date_str}*
"""

        return content

    def save_article(self, content: str, date_str: str) -> Path:
        filename = f"article_{date_str}.md"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"分析文章已保存到: {filepath}")
        return filepath

    def run(self, date: Optional[datetime] = None) -> Dict:
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        logger.info(f"开始生成 {date_str} 的每日分析...")
        
        news_data = self.collector.collect_daily_news(date)
        self.collector.save_news(news_data)
        
        article_content = self.generate_analysis(news_data)
        article_path = self.save_article(article_content, date_str)
        
        return {
            "date": date_str,
            "article_path": str(article_path),
            "articles_count": len(news_data.get("articles", [])),
        }


def main():
    collector = DailyNewsCollector()
    analyst = DailyAnalyst(collector)
    result = analyst.run()
    print(f"✅ 每日分析完成！")
    print(f"📅 日期: {result['date']}")
    print(f"📄 文章: {result['article_path']}")
    print(f"📊 收集文章数: {result['articles_count']}")


if __name__ == "__main__":
    main()
