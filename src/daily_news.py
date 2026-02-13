"""
每日 AI 新闻抓取与分析
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

from tavily import TavilyClient

from .config import (
    TAVILY_API_KEY,
    SEARCH_DEPTH,
    MAX_RESULTS,
    DAILY_TOPICS,
    DATA_DIR,
    OUTPUT_DIR,
    LOG_LEVEL,
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DailyNewsCollector:
    """每日新闻收集器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("Tavily API key is required")
        self.client = TavilyClient(api_key=self.api_key)

    def search_topic(self, topic: str, days: int = 1) -> List[Dict]:
        """搜索单个主题的新闻"""
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
        """收集当日所有主题的新闻"""
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        all_results = {
            "date": date_str,
            "topics": {},
            "ai_answer": "",
            "articles": [],
        }

        # 搜索每个主题
        for topic in DAILY_TOPICS:
            logger.info(f"正在搜索: {topic}")
            result = self.search_topic(topic)
            if result:
                all_results["topics"][topic] = result
                # 收集文章
                for item in result.get("results", []):
                    article = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:200],
                        "score": item.get("score", 0),
                        "topic": topic,
                    }
                    all_results["articles"].append(article)

        # AI 总结
        if all_results["topics"]:
            first_topic = list(all_results["topics"].values())[0]
            all_results["ai_answer"] = first_topic.get("answer", "")

        return all_results

    def save_news(self, news_data: Dict) -> Path:
        """保存新闻数据到文件"""
        date_str = news_data["date"]
        filename = f"news_{date_str}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"新闻数据已保存到: {filepath}")
        return filepath


class DailyAnalyst:
    """每日分析师"""

    def __init__(self, news_collector: DailyNewsCollector):
        self.collector = news_collector

    def generate_analysis(self, news_data: Dict) -> str:
        """生成每日分析文章"""
        date_str = news_data["date"]
        articles = news_data.get("articles", [])
        ai_answer = news_data.get("ai_answer", "")

        # 按分数排序，取前10
        top_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:10]

        # 生成文章
        content = f"""# 每日 AI 动态分析 - {date_str}

## 今日 AI 领域要闻

"""

        if ai_answer:
            content += f"**AI 总结：**{ai_answer}\n\n"

        content += "## 重点新闻\n\n"

        for i, article in enumerate(top_articles, 1):
            content += f"### {i}. {article['title']}\n"
            content += f"**来源：** {article.get('url', 'Unknown')}\n"
            content += f"**相关领域：** {article.get('topic', 'AI')}\n"
            if article.get("content"):
                content += f"\n{article['content']}\n"
            content += "\n---\n\n"

        # 添加分析结语
        content += f"""
## 分析总结

今日 AI 领域共收集到 {len(articles)} 条相关新闻，以上为最具影响力的 {len(top_articles)} 条。

**关注焦点：** 本日新闻主要集中在模型更新、产品发布和应用落地等方面。

---
*本文由 AI 自动生成 | 发布日期：{date_str}*
"""

        return content

    def save_article(self, content: str, date_str: str) -> Path:
        """保存分析文章"""
        filename = f"article_{date_str}.md"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"分析文章已保存到: {filepath}")
        return filepath

    def run(self, date: Optional[datetime] = None) -> Dict:
        """运行每日分析流程"""
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        logger.info(f"开始生成 {date_str} 的每日分析...")
        
        # 1. 收集新闻
        news_data = self.collector.collect_daily_news(date)
        
        # 2. 保存原始数据
        self.collector.save_news(news_data)
        
        # 3. 生成分析
        article_content = self.generate_analysis(news_data)
        
        # 4. 保存文章
        article_path = self.save_article(article_content, date_str)
        
        return {
            "date": date_str,
            "article_path": str(article_path),
            "articles_count": len(news_data.get("articles", [])),
        }


def main():
    """主函数"""
    collector = DailyNewsCollector()
    analyst = DailyAnalyst(collector)
    result = analyst.run()
    print(f"✅ 每日分析完成！")
    print(f"📅 日期: {result['date']}")
    print(f"📄 文章: {result['article_path']}")
    print(f"📊 收集文章数: {result['articles_count']}")


if __name__ == "__main__":
    main()
