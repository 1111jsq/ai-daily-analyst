"""
Web数据抓取模块
"""
import json
import logging
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import requests

logger = logging.getLogger(__name__)


class WebFetcher:
    """Web数据抓取器"""
    
    def __init__(self, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.timeout = timeout
    
    def fetch_json_api(self, config: Dict) -> List[Dict]:
        """从JSON API获取数据"""
        api_url = config.get("api_url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        list_path = config.get("list_path", "data")
        
        if not api_url:
            logger.warning("No API URL found in config")
            return []
        
        ts = str(int(time.time() * 1000))
        
        final_headers = {}
        for k, v in headers.items():
            final_headers[k] = v.replace("{ts}", ts)
        
        final_params = {}
        for k, v in params.items():
            if isinstance(v, str):
                final_params[k] = v.replace("{ts}", ts).replace("{page}", "1")
            else:
                final_params[k] = v
        
        max_pages = config.get("max_pages", 3)
        all_items = []
        
        for page in range(1, max_pages + 1):
            page_params = {k: v.replace("{page}", str(page)) if isinstance(v, str) else v 
                         for k, v in final_params.items()}
            
            try:
                if method == "POST":
                    response = self.session.post(
                        api_url, 
                        json=json.loads(final_params.get("json", "{}").replace("{ts}", ts).replace("{page}", str(page))),
                        headers=final_headers, 
                        timeout=self.timeout
                    )
                else:
                    response = self.session.get(
                        api_url, 
                        params=page_params, 
                        headers=final_headers, 
                        timeout=self.timeout
                    )
                
                response.raise_for_status()
                data = response.json()
                
                items = data
                for key in list_path.split("."):
                    items = items.get(key, [])
                
                if not items:
                    logger.info(f"第{page}页无数据，停止抓取")
                    break
                
                for item in items:
                    all_items.append(item)
                
                logger.info(f"第{page}页获取{len(items)}条数据")
                
            except Exception as e:
                logger.error(f"抓取第{page}页失败: {e}")
                break
        
        return all_items
    
    def parse_items(self, items: List[Dict], config: Dict) -> List[Dict]:
        """解析数据项"""
        results = []
        title_path = config.get("title_path", "title")
        summary_path = config.get("summary_path", "description")
        url_template = config.get("url_template", "")
        oid_path = config.get("oid_path", "oid")
        
        for item in items:
            title = item
            for key in title_path.split("."):
                title = title.get(key, "") if isinstance(title, dict) else ""
            
            summary = item
            for key in summary_path.split("."):
                summary = summary.get(key, "") if isinstance(summary, dict) else ""
            
            oid = item
            for key in oid_path.split("."):
                oid = oid.get(key, "") if isinstance(oid, dict) else ""
            
            url = url_template.replace("{oid}", str(oid)) if oid else ""
            
            if title:
                results.append({
                    "title": title,
                    "content": summary,
                    "url": url,
                    "score": 0.9,
                    "source": "AIbase",
                })
        
        return results
    
    def fetch(self, source_config: Dict) -> List[Dict]:
        """抓取单个数据源"""
        name = source_config.get("name", "unknown")
        
        api_config = source_config.get("api", {})
        if not api_config:
            api_config = source_config.get("pagination", {})
        
        logger.info(f"开始抓取: {name}")
        
        if api_config:
            items = self.fetch_json_api(api_config)
            return self.parse_items(items, api_config)
        
        logger.warning(f"源 {name} 无API配置")
        return []


class NewsCollector:
    """新闻收集器 - 支持多数据源"""
    
    def __init__(self, sources_config: Dict):
        self.sources_config = sources_config
        self.web_fetcher = WebFetcher()
    
    def collect(self, max_items: int = 20) -> List[Dict]:
        """收集所有启用的数据源"""
        all_articles = []
        
        daily_list = self.sources_config.get("daily", [])
        for source in daily_list:
            if source.get("enabled", True):
                articles = self.web_fetcher.fetch(source)
                all_articles.extend(articles)
                logger.info(f"从 {source.get('name')} 获取 {len(articles)} 条")
        
        web_list = self.sources_config.get("web", [])
        for source in web_list:
            if source.get("enabled", True):
                articles = self.web_fetcher.fetch(source)
                all_articles.extend(articles)
                logger.info(f"从 {source.get('name')} 获取 {len(articles)} 条")
        
        return all_articles[:max_items]
