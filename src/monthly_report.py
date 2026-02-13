"""
月度报告生成器
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

from .config import DATA_DIR, OUTPUT_DIR, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MonthlyReporter:
    """月度报告生成器"""

    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.date_str = f"{year}-{month:02d}"

    def load_monthly_news(self) -> List[Dict]:
        """加载当月所有新闻数据"""
        all_articles = []
        
        # 计算月份范围
        start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1)
        else:
            end_date = datetime(self.year, self.month + 1, 1)

        # 遍历数据目录
        for file in DATA_DIR.glob("news_*.json"):
            try:
                # 解析日期
                date_str = file.stem.replace("news_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # 检查是否在当月
                if start_date <= file_date < end_date:
                    with open(file, encoding="utf-8") as f:
                        data = json.load(f)
                        articles = data.get("articles", [])
                        all_articles.extend(articles)
                        logger.info(f"加载 {date_str}: {len(articles)} 篇文章")
            except Exception as e:
                logger.warning(f"加载文件失败 {file}: {e}")

        logger.info(f"当月共收集 {len(all_articles)} 篇文章")
        return all_articles

    def load_monthly_articles(self) -> List[Dict]:
        """加载当月所有分析文章"""
        articles = []
        
        start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1)
        else:
            end_date = datetime(self.year, self.month + 1, 1)

        for file in OUTPUT_DIR.glob("article_*.md"):
            try:
                date_str = file.stem.replace("article_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if start_date <= file_date < end_date:
                    with open(file, encoding="utf-8") as f:
                        content = f.read()
                        articles.append({
                            "date": date_str,
                            "path": str(file),
                            "content": content,
                            "title": content.split("\n")[0].replace("# ", "").strip(),
                        })
            except Exception as e:
                logger.warning(f"加载文章失败 {file}: {e}")

        return articles

    def analyze_topics(self, articles: List[Dict]) -> Dict:
        """分析热门话题"""
        topics = [a.get("topic", "Unknown") for a in articles]
        topic_counts = Counter(topics)
        
        return {
            "total_topics": len(topic_counts),
            "topic_distribution": dict(topic_counts.most_common(10)),
        }

    def analyze_sources(self, articles: List[Dict]) -> Dict:
        """分析新闻来源"""
        sources = []
        for article in articles:
            url = article.get("url", "")
            if url:
                # 提取域名
                domain = url.split("/")[2] if "/" in url else url
                sources.append(domain)
        
        source_counts = Counter(sources)
        
        return {
            "total_sources": len(source_counts),
            "top_sources": dict(source_counts.most_common(10)),
        }

    def generate_report(self, articles: List[Dict], analysis_articles: List[Dict]) -> str:
        """生成月度报告"""
        # 话题分析
        topic_analysis = self.analyze_topics(articles)
        
        # 来源分析
        source_analysis = self.analyze_sources(articles)
        
        # 生成报告
        month_name = f"{self.year}年{self.month}月"
        
        report = f"""# {month_name} AI 阅读分析报告

## 📊 数据概览

- **文章总数**: {len(articles)}
- **发布文章数**: {len(analysis_articles)}
- **涉及话题数**: {topic_analysis['total_topics']}
- **新闻来源数**: {source_analysis['total_sources']}

---

## 🔥 热门话题排行

| 排名 | 话题 | 文章数 |
|:---:|:---|:---:|
"""
        
        for i, (topic, count) in enumerate(topic_analysis["topic_distribution"].items(), 1):
            report += f"| {i} | {topic} | {count} |\n"

        report += f"""

## 📰 热门来源排行

| 排名 | 来源 | 文章数 |
|:---:|:---|:---:|
"""
        
        for i, (source, count) in enumerate(source_analysis["top_sources"].items(), 1):
            report += f"| {i} | {source} | {count} |\n"

        report += f"""

## 📝 已发布文章列表

"""
        
        for art in analysis_articles:
            report += f"- {art['date']}: {art['title']}\n"

        report += f"""

---

## 💡 月度总结

{month_name} 共发布 {len(analysis_articles)} 篇每日分析文章，涵盖 AI 领域最新动态。

**本月焦点：** {', '.join(list(topic_analysis['topic_distribution'].keys())[:3])}

---

*本报告由 AI 自动生成 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report

    def save_report(self, content: str) -> Path:
        """保存月度报告"""
        filename = f"monthly_report_{self.date_str}.md"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"月度报告已保存到: {filepath}")
        return filepath

    def run(self) -> Dict:
        """运行月度报告生成流程"""
        logger.info(f"开始生成 {self.date_str} 的月度报告...")
        
        # 1. 加载当月数据
        articles = self.load_monthly_news()
        analysis_articles = self.load_monthly_articles()
        
        # 2. 生成报告
        report_content = self.generate_report(articles, analysis_articles)
        
        # 3. 保存报告
        report_path = self.save_report(report_content)
        
        return {
            "date": self.date_str,
            "report_path": str(report_path),
            "articles_count": len(articles),
            "published_count": len(analysis_articles),
        }


def main():
    """主函数"""
    now = datetime.now()
    reporter = MonthlyReporter(now.year, now.month)
    result = reporter.run()
    print(f"✅ 月度报告生成完成！")
    print(f"📅 月份: {result['date']}")
    print(f"📄 报告: {result['report_path']}")
    print(f"📊 收集文章数: {result['articles_count']}")
    print(f"📝 发布文章数: {result['published_count']}")


if __name__ == "__main__":
    main()
