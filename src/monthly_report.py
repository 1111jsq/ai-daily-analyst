"""
月度报告生成器
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

from .config import DATA_DIR, OUTPUT_DIR, LOG_LEVEL, TECH_CATEGORIES
from .daily_news import categorize_article

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MonthlyReporter:
    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.date_str = f"{year}-{month:02d}"

    def load_monthly_news(self) -> List[Dict]:
        all_articles = []
        
        start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1)
        else:
            end_date = datetime(self.year, self.month + 1, 1)

        for file in DATA_DIR.glob("news_*.json"):
            try:
                date_str = file.stem.replace("news_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
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
        topics = [a.get("topic", "Unknown") for a in articles]
        topic_counts = Counter(topics)
        
        return {
            "total_topics": len(topic_counts),
            "topic_distribution": dict(topic_counts.most_common(10)),
        }

    def analyze_categories(self, articles: List[Dict]) -> Dict:
        categorized = {cat: 0 for cat in TECH_CATEGORIES.keys()}
        categorized["其他"] = 0
        
        for article in articles:
            cat = categorize_article(article.get("title", ""), article.get("content", ""))
            categorized[cat] = categorized.get(cat, 0) + 1
        
        return dict(sorted(categorized.items(), key=lambda x: x[1], reverse=True))

    def analyze_sources(self, articles: List[Dict]) -> Dict:
        sources = []
        for article in articles:
            url = article.get("url", "")
            if url:
                domain = url.split("/")[2] if "/" in url else url
                sources.append(domain)
        
        source_counts = Counter(sources)
        
        return {
            "total_sources": len(source_counts),
            "top_sources": dict(source_counts.most_common(10)),
        }

    def generate_trends(self, articles: List[Dict]) -> str:
        categorized = self.analyze_categories(articles)
        
        trends = []
        for cat, count in categorized.items():
            if count > 0:
                trends.append(f"- **{cat}**: {count}篇")
        
        return "\n".join(trends)

    def generate_report(self, articles: List[Dict], analysis_articles: List[Dict]) -> str:
        topic_analysis = self.analyze_topics(articles)
        category_analysis = self.analyze_categories(articles)
        source_analysis = self.analyze_sources(articles)
        
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
---

## 📈 技术领域分布

| 类别 | 文章数 | 占比 |
|:---|:---:|:---:|
"""
        
        total = len(articles) or 1
        for cat, count in category_analysis.items():
            pct = count / total * 100
            report += f"| {cat} | {count} | {pct:.1f}% |\n"

        report += f"""
---

## 📰 热门来源排行

| 排名 | 来源 | 文章数 |
|:---:|:---|:---:|
"""
        
        for i, (source, count) in enumerate(source_analysis["top_sources"].items(), 1):
            report += f"| {i} | {source} | {count} |\n"

        report += f"""
---

## 💡 技术趋势总结

### 结论一：多模态与Agent技术持续升温

本月 {len(analysis_articles)} 篇分析文章显示，大模型技术继续快速演进，{list(category_analysis.keys())[0] if category_analysis else 'AI领域'}成为关注焦点。

### 结论二：应用落地加速

各厂商积极推动AI技术商业化落地，在{list(category_analysis.keys())[1] if len(category_analysis) > 1 else '应用层面'}有显著进展。

### 结论三：开源生态活跃

开源模型持续迭代，为社区提供更多选择。

### 关键趋势

| 领域 | 趋势描述 |
|:---|:---|
"""
        
        trend_descriptions = {
            "大模型": "模型能力持续提升，多模态能力增强",
            "具身智能": "人形机器人新品频发，应用场景扩展",
            "智能体": "Agent框架成熟，自主决策能力增强",
            "应用落地": "垂直领域应用加速，商业化路径清晰",
            "算力基础设施": "芯片性能提升，推理成本下降",
            "开源动态": "开源模型活跃，社区贡献增加",
        }
        
        for cat in list(category_analysis.keys())[:6]:
            desc = trend_descriptions.get(cat, "持续发展")
            report += f"| {cat} | {desc} |\n"

        report += f"""
---

## 📝 已发布文章列表

"""
        
        for art in analysis_articles:
            report += f"- {art['date']}: {art['title']}\n"

        report += f"""
---

## 💬 月度总结

{month_name} 共发布 **{len(analysis_articles)}** 篇每日分析文章，收集 **{len(articles)}** 条行业资讯。

**本月焦点：** {', '.join(list(category_analysis.keys())[:3])}

**技术趋势：** AI技术呈现{list(category_analysis.keys())[0]}、{list(category_analysis.keys())[1] if len(category_analysis) > 1 else '应用落地'}并行发展的态势。

---

*本报告由 AI 自动生成 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report

    def save_report(self, content: str) -> Path:
        filename = f"monthly_report_{self.date_str}.md"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"月度报告已保存到: {filepath}")
        return filepath

    def run(self) -> Dict:
        logger.info(f"开始生成 {self.date_str} 的月度报告...")
        
        articles = self.load_monthly_news()
        analysis_articles = self.load_monthly_articles()
        
        report_content = self.generate_report(articles, analysis_articles)
        report_path = self.save_report(report_content)
        
        return {
            "date": self.date_str,
            "report_path": str(report_path),
            "articles_count": len(articles),
            "published_count": len(analysis_articles),
        }


def main():
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
