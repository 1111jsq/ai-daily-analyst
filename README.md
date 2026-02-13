# AI Daily Analyst

一人公司项目：微信公众号 AI 分析助手

## 功能

- **每日 AI 动态分析**：自动抓取当日 AI 领域重大新闻，生成分析报告
- **每月阅读报告**：汇总当月分析文章，生成阅读量/影响力报告

## 技术栈

- Python 3.11+
- Tavily API (网络搜索)
- WeChat API (公众号推送)

## 项目结构

```
ai-daily-analyst/
├── src/
│   ├── daily_news.py      # 每日新闻抓取与分析
│   ├── monthly_report.py  # 月度报告生成
│   ├── wechat_client.py  # 微信公众号客户端
│   └── config.py         # 配置管理
├── data/                 # 数据存储
├── output/               # 生成的报告
├── requirements.txt
└── README.md
```
