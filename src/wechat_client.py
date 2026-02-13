"""
微信公众号客户端
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

import requests

from .config import (
    WECHAT_APP_ID,
    WECHAT_APP_SECRET,
    WECHAT_AUTHOR,
    OUTPUT_DIR,
    LOG_LEVEL,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WeChatClient:
    """微信公众号 API 客户端"""

    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or WECHAT_APP_ID
        self.app_secret = app_secret or WECHAT_APP_SECRET
        
        if not self.app_id or not self.app_secret:
            raise ValueError("WeChat App ID and Secret are required")
        
        self.access_token = None
        self.token_expires_at = 0

    def _request(self, url: str, method: str = "GET", **kwargs) -> Dict:
        """发送请求"""
        try:
            if method == "GET":
                response = requests.get(url, params=kwargs.get("params"))
            else:
                response = requests.post(url, json=kwargs.get("json"))
            
            result = response.json()
            
            if result.get("errcode") and result["errcode"] != 0:
                logger.error(f"WeChat API error: {result}")
                raise Exception(f"API error: {result.get('errmsg', 'Unknown error')}")
            
            return result
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token"""
        now = time.time()
        
        if not force_refresh and self.access_token and now < self.token_expires_at:
            return self.access_token
        
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        
        result = self._request(url, params=params)
        self.access_token = result["access_token"]
        expires_in = result.get("expires_in", 7200)
        self.token_expires_at = now + expires_in - 300  # 提前5分钟过期
        
        logger.info("Access token obtained successfully")
        return self.access_token

    def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片到微信素材库"""
        token = self.get_access_token()
        
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
        
        with open(image_path, "rb") as f:
            files = {"media": f}
            response = requests.post(url, files=files)
            result = response.json()
            
            if result.get("errcode") and result["errcode"] != 0:
                logger.error(f"Image upload failed: {result}")
                return None
            
            return result.get("url")

    def create_draft(self, title: str, content: str, author: str = None, 
                     digest: str = None, content_source_url: str = "",
                     thumb_media_id: str = None) -> Optional[str]:
        """创建草稿"""
        token = self.get_access_token()
        
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        articles = [{
            "title": title,
            "author": author or WECHAT_AUTHOR,
            "digest": digest or content[:120],
            "content": content,
            "content_source_url": content_source_url,
            "thumb_media_id": thumb_media_id or "",
        }]
        
        result = self._request(url, json={"articles": articles})
        media_id = result.get("media_id")
        
        if media_id:
            logger.info(f"Draft created: {media_id}")
        
        return media_id

    def publish_draft(self, media_id: str) -> Dict:
        """发布草稿"""
        token = self.get_access_token()
        
        # 先获取发布权限
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
        result = self._request(url, json={"media_id": media_id})
        
        logger.info(f"Draft published: {result}")
        return result

    def get_article_stats(self, begin_date: str, end_date: str) -> Dict:
        """获取文章统计数据"""
        token = self.get_access_token()
        
        url = "https://api.weixin.qq.com/datacube/getarticlesummary"
        params = {"access_token": token}
        
        data = {
            "begin_date": begin_date,
            "end_date": end_date,
        }
        
        return self._request(url, json=data)

    def get_user_stats(self, date: str) -> Dict:
        """获取用户统计数据"""
        token = self.get_access_token()
        
        url = "https://api.weixin.qq.com/datacube/getusercumulate"
        params = {"access_token": token}
        
        data = {
            "begin_date": date,
            "end_date": date,
        }
        
        return self._request(url, json=data)


class ArticlePublisher:
    """文章发布器"""

    def __init__(self, wechat_client: WeChatClient = None):
        self.client = wechat_client or WeChatClient()

    def publish_daily_article(self, date: str = None) -> Dict:
        """发布每日分析文章"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        # 读取文章
        article_path = OUTPUT_DIR / f"article_{date}.md"
        
        if not article_path.exists():
            raise FileNotFoundError(f"Article not found: {article_path}")
        
        with open(article_path, encoding="utf-8") as f:
            content = f.read()
        
        # 解析标题（第一行）
        lines = content.split("\n")
        title = lines[0].replace("# ", "").strip() if lines else "每日 AI 动态"
        
        # 转换 Markdown 为微信 HTML
        html_content = self._convert_to_wechat_html(content)
        
        # 创建并发布草稿
        media_id = self.client.create_draft(title, html_content)
        
        if not media_id:
            raise Exception("Failed to create draft")
        
        # 发布
        result = self.client.publish_draft(media_id)
        
        return {
            "date": date,
            "title": title,
            "media_id": media_id,
            "publish_result": result,
        }

    def _convert_to_wechat_html(self, markdown: str) -> str:
        """将 Markdown 转换为微信 HTML"""
        html = markdown
        
        # 标题转换
        import re
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 粗体和斜体
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        
        # 链接
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        # 列表
        html = re.sub(r'^- (.+)$', r'<p>• \1</p>', html, flags=re.MULTILINE)
        html = re.sub(r'^\d+\. (.+)$', r'<p>\1</p>', html, flags=re.MULTILINE)
        
        # 分割线
        html = html.replace("---", "<hr>")
        
        # 段落
        html = re.sub(r'\n\n+', '\n', html)
        
        return html

    def run(self, date: str = None) -> Dict:
        """运行发布流程"""
        result = self.publish_daily_article(date)
        print(f"✅ 文章发布成功！")
        print(f"📅 日期: {result['date']}")
        print(f"📝 标题: {result['title']}")
        print(f"�ds 草稿ID: {result['media_id']}")
        return result


def main():
    """主函数"""
    publisher = ArticlePublisher()
    
    # 获取昨天日期
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    
    try:
        result = publisher.run(date_str)
    except FileNotFoundError as e:
        print(f"❌ 找不到文章: {e}")
    except Exception as e:
        print(f"❌ 发布失败: {e}")


if __name__ == "__main__":
    main()
