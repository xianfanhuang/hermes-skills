#!/usr/bin/env python3
"""
Global Info Fetcher v3.0 - Agent感知基础设施
支持: Hacker News, Lobste.rs, GitHub Trending, Reddit, RSS + Jina Reader
新增感知层: arXiv, CVE/NVD, Coze平台, 中文AI媒体
新增金融感知: iTick, AKShare, Binance, FRED

核心升级 (v3.0):
- arXiv API: AI/Agent最新学术论文
- CVE/NVD: 安全威胁实时监控
- Coze平台动态: 平台变更感知
- 感知信号系统: 从文章列表到结构化信号
- 信号驱动自进化: 安全威胁自动评估
- 金融数据感知: 跨市场行情、加密货币、宏观数据

Author: AI Agent
Version: 3.0.0
"""

import json
import time
import random
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GlobalInfoFetcher")

# ============ Enums and Config ============
class OutputFormat(Enum):
    """输出格式枚举"""
    MARKDOWN = "markdown"
    JSON = "json"
    SIMPLE = "simple"

class SignalType(Enum):
    """感知信号类型枚举"""
    SECURITY_THREAT = "security_threat"      # 安全威胁，需立即评估
    PARADIGM_SHIFT = "paradigm_shift"        # 范式变化，评估采纳
    ECOSYSTEM_CHANGE = "ecosystem_change"    # 生态演进，关注跟进
    PLATFORM_UPDATE = "platform_update"      # 平台变更，确认影响
    TECH_BREAKTHROUGH = "tech_breakthrough"  # 技术突破，知识储备
    MARKET_SIGNAL = "market_signal"          # 市场信号，用户关注

class Severity(Enum):
    """严重程度枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

# ============ Data Classes ============
@dataclass
class NewsItem:
    """标准化新闻条目"""
    source: str
    title: str
    url: str
    author: Optional[str] = None
    timestamp: Optional[str] = None
    score: Optional[int] = None
    comments: Optional[int] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    language: str = "en"
    # 新增字段
    raw_content: Optional[str] = None  # 原始正文（通过Jina提取）
    extracted_summary: Optional[str] = None  # 提取的摘要
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_markdown(self, include_content: bool = False) -> str:
        """转换为Markdown格式"""
        lines = [
            f"## {self.title}",
            f"",
            f"- **来源**: {self.source}",
            f"- **链接**: {self.url}",
        ]
        if self.author:
            lines.append(f"- **作者**: {self.author}")
        if self.timestamp:
            lines.append(f"- **时间**: {self.timestamp}")
        if self.score:
            lines.append(f"- **评分**: {self.score}")
        if self.comments:
            lines.append(f"- **评论数**: {self.comments}")
        if self.tags:
            lines.append(f"- **标签**: {', '.join(self.tags)}")
        if self.content and not include_content:
            lines.append(f"- **摘要**: {self.content[:200]}..." if len(self.content or '') > 200 else f"- **摘要**: {self.content}")
        if self.extracted_summary:
            lines.append(f"- **摘要**: {self.extracted_summary}")
        return "\n".join(lines)

@dataclass
class PerceptionSignal:
    """
    感知信号 - Agent自主进化的核心数据结构
    
    区别于普通NewsItem：
    - 明确的信号类型（安全/范式/生态/平台/技术/市场）
    - 行动指引（action_required）
    - 与自进化系统直接对接
    """
    type: str                    # SignalType.value
    source: str                  # 数据来源
    title: str                   # 信号标题
    url: str                     # 原始链接
    relevance: str               # 相关性说明
    action_required: bool        # 是否需要采取行动
    severity: str = "info"       # Severity.value
    summary: Optional[str] = None  # 简短摘要
    timestamp: Optional[str] = None  # 发现时间
    related_signals: List[str] = field(default_factory=list)  # 关联信号
    metadata: Dict[str, Any] = field(default_factory=dict)   # 额外元数据
    
    # 原始来源信息（用于追溯）
    original_item: Optional[Dict] = None  # 原始NewsItem数据
    
    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'relevance': self.relevance,
            'action_required': self.action_required,
            'severity': self.severity,
            'summary': self.summary,
            'timestamp': self.timestamp,
            'related_signals': self.related_signals,
            'metadata': self.metadata
        }
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        action_emoji = "🔴" if self.action_required else "🟢"
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "📝",
            "info": "ℹ️"
        }.get(self.severity, "ℹ️")
        
        lines = [
            f"### {severity_emoji} {self.title}",
            "",
            f"| 属性 | 值 |",
            f"|------|-----|",
            f"| **信号类型** | {self.type} |",
            f"| **来源** | {self.source} |",
            f"| **严重程度** | {self.severity} |",
            f"| **行动要求** | {'是' if self.action_required else '否'} |",
            f"| **相关性** | {self.relevance} |",
            f"| **链接** | {self.url} |",
        ]
        if self.summary:
            lines.append(f"| **摘要** | {self.summary} |")
        if self.timestamp:
            lines.append(f"| **发现时间** | {self.timestamp} |")
        if self.related_signals:
            lines.append(f"| **关联信号** | {', '.join(self.related_signals)} |")
        
        return "\n".join(lines)

@dataclass
class FetchResult:
    """抓取结果"""
    source: str
    success: bool
    items: List[NewsItem]
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)  # 新增元数据
    
    def to_dict(self) -> dict:
        return {
            'source': self.source,
            'success': self.success,
            'item_count': len(self.items),
            'error': self.error,
            'duration': self.duration,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'items': [item.to_dict() for item in self.items]
        }
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = [f"## {self.source}", ""]
        status = "✅ 成功" if self.success else "❌ 失败"
        lines.append(f"**状态**: {status}")
        lines.append(f"**获取条数**: {len(self.items)}")
        lines.append(f"**耗时**: {self.duration:.2f}s")
        if self.error:
            lines.append(f"**错误**: {self.error}")
        lines.append("")
        
        if self.items:
            for item in self.items[:10]:  # 只显示前10条
                lines.append(item.to_markdown())
                lines.append("")
        
        if len(self.items) > 10:
            lines.append(f"*... 还有 {len(self.items) - 10} 条*")
        
        return "\n".join(lines)

# ============ Jina Reader 支持 ============
class JinaReader:
    """
    Jina Reader - 绕过反爬，返回干净Markdown
    使用方式：在任意URL前加 https://r.jina.ai/
    """
    
    BASE_URL = "https://r.jina.ai/"
    
    @staticmethod
    def make_reader_url(url: str) -> str:
        """将普通URL转换为Jina Reader URL"""
        return f"{JinaReader.BASE_URL}{url}"
    
    @staticmethod
    def extract_content(url: str, timeout: int = 15) -> Optional[str]:
        """
        使用Jina Reader提取网页正文
        
        Args:
            url: 原始URL
            timeout: 超时时间（秒）
            
        Returns:
            干净的Markdown文本，失败返回None
        """
        import urllib.request
        import urllib.error
        
        reader_url = JinaReader.make_reader_url(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; GlobalInfoFetcher/2.0)',
            'Accept': 'text/plain, */*',
            'X-Return-Format': 'markdown',  # 请求返回Markdown格式
        }
        
        try:
            req = urllib.request.Request(reader_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode('utf-8')
                logger.debug(f"Jina Reader extracted {len(content)} chars from {url}")
                return content
        except Exception as e:
            logger.warning(f"Jina Reader failed for {url}: {e}")
            return None
    
    @staticmethod
    def extract_summary(content: str, max_length: int = 200) -> str:
        """从内容中提取摘要"""
        if not content:
            return ""
        # 清理Markdown格式
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # 移除链接
        text = re.sub(r'[#*_`~>-]', '', text)  # 移除格式符号
        text = re.sub(r'\s+', ' ', text)  # 合并空白
        return text[:max_length].strip() + "..."

# ============ Base Fetcher ============
class BaseFetcher:
    """抓取器基类"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.session_config = {
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 2,
            'backoff_factor': 1.5
        }
        self.use_jina_fallback = self.config.get('use_jina_fallback', True)
    
    def _make_request(self, url: str, headers: Optional[Dict] = None, 
                      use_jina: bool = False) -> Optional[Dict]:
        """通用HTTP请求方法，带重试机制"""
        import urllib.request
        import urllib.error
        
        # 如果启用Jina Reader模式
        if use_jina:
            content = JinaReader.extract_content(url)
            if content:
                return {'raw': content, 'is_markdown': True}
            return None
        
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if headers:
            default_headers.update(headers)
        
        last_error = None
        for attempt in range(self.session_config['max_retries']):
            try:
                req = urllib.request.Request(url, headers=default_headers)
                with urllib.request.urlopen(req, timeout=self.session_config['timeout']) as response:
                    content = response.read().decode('utf-8')
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'json' in content_type:
                        return json.loads(content)
                    else:
                        return {'raw': content}
                        
            except urllib.error.HTTPError as e:
                last_error = f"HTTP Error {e.code}"
                logger.warning(f"{last_error} for {url}, attempt {attempt + 1}")
                if e.code == 429:
                    wait_time = 60 * (attempt + 1)
                    logger.info(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif attempt < self.session_config['max_retries'] - 1:
                    delay = self.session_config['retry_delay'] * (self.session_config['backoff_factor'] ** attempt)
                    time.sleep(delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Request failed: {e}, attempt {attempt + 1}")
                if attempt < self.session_config['max_retries'] - 1:
                    delay = self.session_config['retry_delay'] * (self.session_config['backoff_factor'] ** attempt)
                    time.sleep(delay)
        
        # 如果配置了降级到Jina Reader
        if self.use_jina_fallback and not use_jina:
            logger.info(f"Falling back to Jina Reader for {url}")
            return self._make_request(url, headers, use_jina=True)
        
        return None
    
    def _extract_article_content(self, url: str) -> Optional[str]:
        """尝试提取文章正文"""
        if not self.use_jina_fallback:
            return None
        return JinaReader.extract_content(url)

# ============ Hacker News Fetcher ============
class HackerNewsFetcher(BaseFetcher):
    """Hacker News 抓取器 - 使用官方Firebase API，完全免费"""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Hacker News"
    
    async def fetch_top_stories(self, limit: int = 30, 
                                 extract_content: bool = False) -> FetchResult:
        """获取热门故事
        
        Args:
            limit: 数量限制
            extract_content: 是否提取文章正文
        """
        start_time = time.time()
        items = []
        
        try:
            response = self._make_request(f"{self.BASE_URL}/topstories.json")
            if not response:
                return FetchResult(
                    source=self.name,
                    success=False,
                    items=[],
                    error="Failed to fetch story IDs",
                    duration=time.time() - start_time
                )
            
            story_ids = response[:limit]
            
            for story_id in story_ids:
                story = self._make_request(f"{self.BASE_URL}/item/{story_id}.json")
                if story and story.get('type') == 'story':
                    item = NewsItem(
                        source="hackernews",
                        title=story.get('title', ''),
                        url=story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                        author=story.get('by'),
                        timestamp=datetime.fromtimestamp(story.get('time', 0)).isoformat() if story.get('time') else None,
                        score=story.get('score'),
                        comments=story.get('descendants'),
                        tags=story.get('tags', [])
                    )
                    
                    # 可选：提取正文
                    if extract_content and item.url.startswith('http'):
                        raw = self._extract_article_content(item.url)
                        if raw:
                            item.raw_content = raw
                            item.extracted_summary = JinaReader.extract_summary(raw)
                    
                    items.append(item)
                time.sleep(0.1)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'requested': limit, 'content_extracted': extract_content}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_new_stories(self, limit: int = 30) -> FetchResult:
        """获取最新故事"""
        start_time = time.time()
        items = []
        
        try:
            response = self._make_request(f"{self.BASE_URL}/newstories.json")
            if not response:
                return FetchResult(source=self.name, success=False, items=[], error="Failed to fetch")
            
            story_ids = response[:limit]
            
            for story_id in story_ids:
                story = self._make_request(f"{self.BASE_URL}/item/{story_id}.json")
                if story and story.get('type') == 'story':
                    items.append(NewsItem(
                        source="hackernews",
                        title=story.get('title', ''),
                        url=story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                        author=story.get('by'),
                        timestamp=datetime.fromtimestamp(story.get('time', 0)).isoformat() if story.get('time') else None,
                        score=story.get('score'),
                        comments=story.get('descendants')
                    ))
                time.sleep(0.1)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(source=self.name, success=False, items=[], error=str(e))

# ============ Reddit Fetcher ============
class RedditFetcher(BaseFetcher):
    """Reddit 抓取器 - 使用公共JSON端点，完全免费"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Reddit"
        self.subreddits = config.get('subreddits', ['technology', 'programming', 'artificial', 'MachineLearning']) if config else ['technology', 'programming', 'artificial', 'MachineLearning']
    
    async def fetch_subreddit(self, subreddit: str, limit: int = 25) -> List[NewsItem]:
        """获取指定subreddit的热门帖子"""
        items = []
        
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot/.json?limit={limit}"
            response = self._make_request(url, headers={'Accept': 'application/json'})
            
            if response and 'data' in response:
                for post in response['data']['children']:
                    data = post['data']
                    items.append(NewsItem(
                        source=f"reddit/{subreddit}",
                        title=data.get('title', ''),
                        url=data.get('url', ''),
                        author=data.get('author'),
                        timestamp=datetime.fromtimestamp(data.get('created_utc', 0)).isoformat() if data.get('created_utc') else None,
                        score=data.get('score'),
                        comments=data.get('num_comments'),
                        content=data.get('selftext', '')[:500] if data.get('selftext') else None,
                        tags=data.get('link_flair_text', '').split(',') if data.get('link_flair_text') else []
                    ))
                    
        except Exception as e:
            logger.warning(f"Error fetching r/{subreddit}: {e}")
        
        return items
    
    async def fetch_all(self, limit_per_sub: int = 20) -> FetchResult:
        """获取所有配置的subreddits"""
        start_time = time.time()
        all_items = []
        
        for subreddit in self.subreddits:
            items = await self.fetch_subreddit(subreddit, limit_per_sub)
            all_items.extend(items)
            time.sleep(1)
        
        return FetchResult(
            source=self.name,
            success=True,
            items=all_items,
            duration=time.time() - start_time,
            timestamp=datetime.now().isoformat()
        )

# ============ GitHub Trending Fetcher ============
class GitHubTrendingFetcher(BaseFetcher):
    """GitHub Trending 抓取器 - 使用第三方API"""
    
    API_URL = "https://githubtrending.lessx.xyz/trending"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "GitHub Trending"
    
    async def fetch_trending(self, language: str = "", since: str = "daily") -> FetchResult:
        """获取GitHub Trending"""
        start_time = time.time()
        items = []
        
        try:
            params = f"?since={since}"
            if language:
                params += f"&language={language}"
            
            response = self._make_request(f"{self.API_URL}{params}")
            
            if response and isinstance(response, list):
                for repo in response:
                    items.append(NewsItem(
                        source="github",
                        title=repo.get('name', ''),
                        url=repo.get('repository', ''),
                        content=repo.get('description', ''),
                        score=int(repo.get('stars', '0').replace(',', '')) if repo.get('stars') else None,
                        tags=[language] if language else [],
                        language="en"
                    ))
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )

# ============ Lobste.rs Fetcher ============
class LobstersFetcher(BaseFetcher):
    """Lobste.rs 抓取器 - 使用官方API"""
    
    BASE_URL = "https://lobste.rs"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Lobste.rs"
    
    async def fetch_hot(self, limit: int = 30) -> FetchResult:
        """获取热门故事"""
        start_time = time.time()
        items = []
        
        try:
            url = f"{self.BASE_URL}/hottest.json"
            response = self._make_request(url)
            
            if response and isinstance(response, list):
                for story in response[:limit]:
                    items.append(NewsItem(
                        source="lobste.rs",
                        title=story.get('title', ''),
                        url=story.get('url', ''),
                        author=story.get('submitter_user', {}).get('username') if isinstance(story.get('submitter_user'), dict) else story.get('submitter_user'),
                        timestamp=story.get('created_at'),
                        score=story.get('score'),
                        comments=story.get('comment_count'),
                        tags=story.get('tags', [])
                    ))
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_new(self, limit: int = 30) -> FetchResult:
        """获取最新故事"""
        start_time = time.time()
        items = []
        
        try:
            url = f"{self.BASE_URL}/newest.json"
            response = self._make_request(url)
            
            if response and isinstance(response, list):
                for story in response[:limit]:
                    items.append(NewsItem(
                        source="lobste.rs",
                        title=story.get('title', ''),
                        url=story.get('url', ''),
                        author=story.get('submitter_user', {}).get('username') if isinstance(story.get('submitter_user'), dict) else story.get('submitter_user'),
                        timestamp=story.get('created_at'),
                        score=story.get('score'),
                        comments=story.get('comment_count'),
                        tags=story.get('tags', [])
                    ))
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(source=self.name, success=False, items=[], error=str(e))

# ============ RSS Feed Fetcher (增强版) ============
class RSSFetcher(BaseFetcher):
    """
    RSS Feed 聚合器 (感知增强版)
    
    新增功能：
    - 更多默认RSS源（AI/Agent/中文媒体）
    - 使用Jina Reader提取正文
    - 支持提取摘要
    """
    
    DEFAULT_FEEDS = {
        # 科技媒体
        'techcrunch': 'https://techcrunch.com/feed/',
        'ars technica': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
        'the verge': 'https://www.theverge.com/rss/index.xml',
        'hacker news': 'https://hnrss.org/frontpage',
        'mit tech review': 'https://www.technologyreview.com/feed/',
        # AI/ML
        'ai weekly': 'https://aiweekly.co/feed',
        # AI公司官方博客（新增）
        'openai blog': 'https://openai.com/blog/rss/',
        'anthropic blog': 'https://www.anthropic.com/news/rss',
        'deepmind blog': 'https://deepmind.com/blog/feed/basic/',
        # 安全
        'threatpost': 'https://threatpost.com/feed/',
        'dark reading': 'https://www.darkreading.com/rss.xml',
        # 开发
        'dev.to': 'https://dev.to/feed',
        'hashnode': 'https://hashnode.com/feed',
        # 中文AI媒体（新增）
        '机器之心': 'https://jiqizhixin.com/rss',
        '量子位': 'https://www.qbitai.com/feed',
        '少数派': 'https://sspai.com/feed',
        # AI开发者社区
        'simonw ai': 'https://simonwillison.net/atom.xml',
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "RSS Feeds"
        cfg = config or {}
        self.feeds = cfg.get('feeds', self.DEFAULT_FEEDS)
        self.extract_content_enabled = cfg.get('extract_content', False)
    
    def _parse_rss(self, xml_content: str) -> List[Dict]:
        """解析RSS XML内容"""
        items = []
        
        item_pattern = r'<item>(.*?)</item>'
        items_xml = re.findall(item_pattern, xml_content, re.DOTALL)
        
        for item_xml in items_xml[:20]:
            title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', item_xml)
            link_match = re.search(r'<link>(.*?)</link>', item_xml)
            desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>', item_xml)
            date_match = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
            author_match = re.search(r'<author>(.*?)</author>|<dc:creator><!\[CDATA\[(.*?)\]\]>', item_xml)
            
            title = title_match.group(1) or title_match.group(2) or '' if title_match else ''
            link = link_match.group(1) if link_match else ''
            desc = desc_match.group(1) or desc_match.group(2) or '' if desc_match else ''
            date = date_match.group(1) if date_match else ''
            author = author_match.group(1) or author_match.group(2) or '' if author_match else ''
            
            if title and link:
                items.append({
                    'title': title.strip(),
                    'url': link.strip(),
                    'description': desc[:500].strip() if desc else '',
                    'date': date,
                    'author': author.strip()
                })
        
        return items
    
    async def fetch_all(self, extract_content: bool = False) -> FetchResult:
        """获取所有配置的RSS源
        
        Args:
            extract_content: 是否使用Jina Reader提取正文
        """
        start_time = time.time()
        all_items = []
        content_extracted = 0
        
        for feed_name, feed_url in self.feeds.items():
            try:
                response = self._make_request(feed_url)
                if response and 'raw' in response:
                    items = self._parse_rss(response['raw'])
                    for item in items:
                        news_item = NewsItem(
                            source=f"rss/{feed_name}",
                            title=item['title'],
                            url=item['url'],
                            author=item.get('author'),
                            timestamp=item.get('date'),
                            content=item.get('description')
                        )
                        
                        # 可选：使用Jina提取正文
                        if extract_content or self.extract_content_enabled:
                            if news_item.url.startswith('http'):
                                raw = self._extract_article_content(news_item.url)
                                if raw:
                                    news_item.raw_content = raw
                                    news_item.extracted_summary = JinaReader.extract_summary(raw)
                                    content_extracted += 1
                        
                        all_items.append(news_item)
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error fetching RSS feed {feed_name}: {e}")
        
        return FetchResult(
            source=self.name,
            success=True,
            items=all_items,
            duration=time.time() - start_time,
            timestamp=datetime.now().isoformat(),
            metadata={
                'feeds_count': len(self.feeds),
                'content_extracted': content_extracted
            }
        )

# ============ Twitter/X 推荐方案说明 ============
class TwitterFetcher(BaseFetcher):
    """
    Twitter/X 抓取器 (v2.0 - 推荐使用Coze官方插件)
    
    ⚠️ 注意：Cookie方案存在封号风险，已移除代码实现
    ✅ 推荐使用Coze官方X插件获取Twitter数据
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Twitter/X"
    
    def get_recommendation(self) -> str:
        """返回推荐方案说明"""
        return """
## Twitter/X 数据获取方案 (v2.0)

### ❌ 不再推荐：Cookie方案
由于以下风险，Cookie方案已从代码中移除：
- 账号封禁风险高
- Cookie有效期短，需要频繁更新
- 违反Twitter ToS

### ✅ 推荐方案

1. **Coze官方X插件** (推荐)
   - 在Coze平台配置X插件
   - 无封号风险，稳定可靠
   - 支持搜索、获取用户推文等

2. **ClawHub X Search技能**
   - 使用XAI API
   - 需要 XAI_API_KEY
   - 完全免费额度

3. **第三方RSS服务**
   - Nitter (开源替代，但不稳定)
   - rss.app 等RSS聚合服务

### 使用示例

```python
# 在Coze中配置X插件后，可直接调用
result = await coze.x.search_tweets("AI Agent", limit=10)
```

如需获取Twitter数据，请在Coze中安装并配置X插件。
"""
    
    async def fetch_user_tweets(self, username: str = "", limit: int = 20) -> FetchResult:
        """获取用户推文 - 返回推荐说明"""
        return FetchResult(
            source=self.name,
            success=False,
            items=[],
            error="Twitter fetcher v2.0 - 请使用Coze官方X插件",
            metadata={'recommendation': self.get_recommendation()}
        )

# ============ Agent News Sources ============
class AgentNewsFetcher(BaseFetcher):
    """Agent/AI社区新闻源抓取器"""
    
    SOURCES = {
        'agent_brief': 'https://news.agentcommunity.org/',
        'ai_agents_subreddit': 'https://www.reddit.com/r/AIAgents/.json',
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Agent News"
    
    async def fetch_all(self) -> FetchResult:
        """获取Agent社区新闻"""
        start_time = time.time()
        all_items = []
        
        try:
            url = "https://www.reddit.com/r/AIAgents/hot/.json?limit=20"
            response = self._make_request(url, headers={'Accept': 'application/json'})
            
            if response and 'data' in response:
                for post in response['data']['children'][:15]:
                    data = post['data']
                    all_items.append(NewsItem(
                        source="reddit/AIAgents",
                        title=data.get('title', ''),
                        url=data.get('url', ''),
                        author=data.get('author'),
                        timestamp=datetime.fromtimestamp(data.get('created_utc', 0)).isoformat(),
                        score=data.get('score'),
                        comments=data.get('num_comments'),
                        tags=['AI Agents']
                    ))
        except Exception as e:
            logger.warning(f"Error fetching Agent news: {e}")
        
        return FetchResult(
            source=self.name,
            success=True,
            items=all_items,
            duration=time.time() - start_time,
            timestamp=datetime.now().isoformat()
        )

# ============ ArXiv Fetcher (新增) ============
class ArxivFetcher(BaseFetcher):
    """
    ArXiv API 抓取器 - AI/Agent学术论文
    
    完全免费，无需API key
    搜索关键词：AI Agent, LLM, autonomous agent, self-evolving AI
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"
    # AI/Agent相关搜索关键词
    SEARCH_KEYWORDS = [
        "AI agent",
        "autonomous agent", 
        "LLM agent",
        "self-evolving AI",
        "multi-agent system",
        "agent architecture"
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "arXiv"
        self.max_results = config.get('max_results', 15) if config else 15
    
    def _parse_arxiv_atom(self, xml_content: str) -> List[NewsItem]:
        """解析ArXiv Atom格式响应"""
        items = []
        
        # 提取entry块
        entry_pattern = r'<entry>(.*?)</entry>'
        entries = re.findall(entry_pattern, xml_content, re.DOTALL)
        
        for entry in entries[:self.max_results]:
            title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            link_match = re.search(r'<id>(.*?)</id>', entry)
            summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            date_match = re.search(r'<published>(.*?)</published>', entry)
            author_match = re.search(r'<author>.*?<name>(.*?)</name>', entry)
            
            title = title_match.group(1).strip().replace('\n', ' ') if title_match else ''
            link = link_match.group(1).strip() if link_match else ''
            summary = summary_match.group(1).strip()[:500] if summary_match else ''
            date = date_match.group(1).strip() if date_match else ''
            author = author_match.group(1).strip() if author_match else ''
            
            if title and link:
                items.append(NewsItem(
                    source="arxiv",
                    title=title,
                    url=link,
                    author=author,
                    timestamp=date,
                    content=summary,
                    tags=["AI", "research", "paper"],
                    language="en"
                ))
        
        return items
    
    async def fetch_latest(self, keyword: Optional[str] = None) -> FetchResult:
        """
        获取最新AI/Agent相关论文
        
        Args:
            keyword: 搜索关键词，默认使用配置的关键词
        """
        start_time = time.time()
        items = []
        
        try:
            # 使用配置的关键词或默认关键词
            search_keyword = keyword or random.choice(self.SEARCH_KEYWORDS)
            
            # 构建查询URL
            # 使用OR组合多个关键词，并按日期排序
            query = search_keyword.replace(' ', '+')
            url = f"{self.BASE_URL}?search_query=all:{query}&start=0&max_results={self.max_results}&sortBy=submittedDate&sortOrder=descending"
            
            response = self._make_request(url)
            
            if response and 'raw' in response:
                items = self._parse_arxiv_atom(response['raw'])
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'keyword': search_keyword}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_multi_keywords(self) -> FetchResult:
        """获取多个关键词的最新论文"""
        start_time = time.time()
        all_items = []
        seen_urls = set()
        
        try:
            for keyword in self.SEARCH_KEYWORDS[:3]:  # 限制为前3个关键词
                result = await self.fetch_latest(keyword)
                if result.success:
                    for item in result.items:
                        if item.url not in seen_urls:
                            seen_urls.add(item.url)
                            all_items.append(item)
                time.sleep(1)  # 避免请求过快
            
            return FetchResult(
                source=self.name,
                success=True,
                items=all_items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )

# ============ CVE/NVD Security Fetcher (新增) ============
class NVDFetcher(BaseFetcher):
    """
    NVD (National Vulnerability Database) 抓取器 - 安全威胁监控
    
    完全免费，API端点: https://services.nvd.nist.gov/rest/json/cves/2.0
    搜索关键词：AI agent, LLM, MCP, OpenClaw, Claude
    """
    
    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    # AI/Agent相关安全关键词
    SECURITY_KEYWORDS = [
        "AI",
        "agent",
        "LLM",
        "MCP",
        "OpenAI",
        "Anthropic",
        "autonomous"
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "NVD/CVE"
        self.session_config['timeout'] = 60  # NVD API较慢，增加超时
    
    def _parse_cve_response(self, data: Dict) -> List[NewsItem]:
        """解析NVD API响应"""
        items = []
        
        vulnerabilities = data.get('vulnerabilities', [])
        
        for vuln in vulnerabilities:
            cve = vuln.get('cve', {})
            cve_id = cve.get('id', '')
            description_list = cve.get('descriptions', [])
            
            # 获取英文描述
            description = ''
            for desc in description_list:
                if desc.get('lang') == 'en':
                    description = desc.get('value', '')[:500]
                    break
            
            # 获取严重程度
            metrics = cve.get('metrics', {})
            severity = 'MEDIUM'  # 默认
            score = None
            
            if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                cvss = metrics['cvssMetricV31'][0].get('cvssData', {})
                score = cvss.get('baseScore')
                severity = cvss.get('baseSeverity', 'MEDIUM')
            elif 'cvssMetricV30' in metrics and metrics['cvssMetricV30']:
                cvss = metrics['cvssMetricV30'][0].get('cvssData', {})
                score = cvss.get('baseScore')
                severity = cvss.get('baseSeverity', 'MEDIUM')
            elif 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                cvss = metrics['cvssMetricV2'][0].get('cvssData', {})
                score = cvss.get('baseScore')
            
            # 获取发布和更新时间
            published = cve.get('published', '')
            last_modified = cve.get('lastModified', '')
            
            # 获取参考链接
            references = cve.get('references', [])
            url = references[0].get('url', '') if references else ''
            
            if cve_id and description:
                items.append(NewsItem(
                    source="nvd",
                    title=f"{cve_id}: {description[:100]}...",
                    url=url or f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    timestamp=published,
                    content=description,
                    score=int(score) if score else None,
                    tags=[severity.lower(), 'security', 'vulnerability'],
                    language="en"
                ))
        
        return items
    
    async def fetch_recent(self, keyword: Optional[str] = None, days: int = 7) -> FetchResult:
        """
        获取最近的安全漏洞
        
        Args:
            keyword: 搜索关键词
            days: 最近几天内的漏洞
        """
        start_time = time.time()
        items = []
        
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 搜索关键词
            search_keyword = keyword or random.choice(self.SECURITY_KEYWORDS)
            
            # 构建查询URL
            pub_start = start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            pub_end = end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            
            # NVD API参数
            url = f"{self.BASE_URL}?pubStartDate={pub_start}&pubEndDate={pub_end}&keywordSearch={search_keyword}&resultsPerPage=20"
            
            response = self._make_request(url)
            
            if response and 'vulnerabilities' in response:
                items = self._parse_cve_response(response)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'keyword': search_keyword, 'days': days}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_high_severity(self) -> FetchResult:
        """获取最近的高危漏洞"""
        start_time = time.time()
        items = []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            pub_start = start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            pub_end = end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            
            # 获取高危漏洞 (CVSS 7.0+)
            for keyword in ['AI', 'agent', 'LLM']:
                url = f"{self.BASE_URL}?pubStartDate={pub_start}&pubEndDate={pub_end}&keywordSearch={keyword}&cvssV3Severity=HIGH&resultsPerPage=10"
                
                try:
                    response = self._make_request(url)
                    if response and 'vulnerabilities' in response:
                        new_items = self._parse_cve_response(response)
                        for item in new_items:
                            if item not in items:
                                items.append(item)
                    time.sleep(2)  # 避免请求过快
                except Exception as e:
                    logger.warning(f"NVD search failed for {keyword}: {e}")
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )

# ============ Coze Platform Fetcher (新增) ============
class CozeFetcher(BaseFetcher):
    """
    Coze/扣子平台动态抓取器
    
    通过Coze平台文档和搜索获取最新更新
    """
    
    PLATFORM_DOC_URL = "https://www.coze.cn/llms.txt"
    BLOG_URL = "https://www.coze.cn/blog"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Coze"
    
    async def fetch_platform_news(self) -> FetchResult:
        """获取Coze平台最新动态"""
        start_time = time.time()
        items = []
        
        try:
            # 尝试读取平台文档变更
            response = self._make_request(self.PLATFORM_DOC_URL)
            
            if response and 'raw' in response:
                content = response['raw']
                
                # 解析文档变更（如果有版本信息）
                lines = content.split('\n')
                for line in lines[:50]:  # 只取前50行
                    if any(keyword in line.lower() for keyword in ['update', 'new', 'change', 'v2', 'v3', 'release']):
                        items.append(NewsItem(
                            source="coze/platform",
                            title=f"平台文档更新: {line[:100]}",
                            url=self.PLATFORM_DOC_URL,
                            timestamp=datetime.now().isoformat(),
                            content=line,
                            tags=["platform", "update"]
                        ))
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )

# ============ HuggingFace Fetcher (新增) ============
class HuggingFaceFetcher(BaseFetcher):
    """
    HuggingFace 抓取器 - 全球最大开源模型社区
    
    API端点:
    - Trending: https://huggingface.co/api/trending
    - Daily Papers: https://huggingface.co/api/daily_papers
    - New Models: https://huggingface.co/api/models?sort=lastModified&direction=-1&limit=10
    
    完全免费，无需API key
    
    信号映射:
    - 新模型发布(参数量/架构突破) → tech_breakthrough
    - 热门模型趋势变化 → ecosystem_change
    - Agent相关模型/框架 → paradigm_shift
    """
    
    BASE_URL = "https://huggingface.co/api"
    
    # Agent/AI相关标签关键词
    AGENT_KEYWORDS = ['agent', 'llm', 'gpt', 'claude', 'autonomous', 'reasoning', 'tool', 'mcp', 'openclaw']
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "HuggingFace"
        self.session_config['timeout'] = 10  # 10秒超时
        self.limit = config.get('limit', 10) if config else 10
    
    def _parse_trending(self, data: Union[List, Dict]) -> List[NewsItem]:
        """解析Trending响应"""
        items = []
        
        # 处理不同响应格式
        if isinstance(data, dict):
            # 可能包含models, spaces, datasets等
            for key in ['models', 'spaces']:
                if key in data and isinstance(data[key], list):
                    items.extend(self._parse_model_list(data[key], source_type=key))
        elif isinstance(data, list):
            items.extend(self._parse_model_list(data))
        
        return items
    
    def _parse_model_list(self, model_list: List, source_type: str = "models") -> List[NewsItem]:
        """解析模型列表"""
        items = []
        
        for model in model_list[:self.limit]:
            model_id = model.get('id', '')
            title = model.get('id', model.get('name', ''))
            
            # 构建URL
            if source_type == "spaces":
                url = f"https://huggingface.co/spaces/{model_id}"
            else:
                url = f"https://huggingface.co/{model_id}"
            
            # 获取描述和指标
            description = model.get('description', '') or model.get('cardData', {}).get('base_model', '')
            likes = model.get('likes', 0)
            downloads = model.get('downloads', 0)
            tags = model.get('tags', [])[:5] if isinstance(model.get('tags'), list) else []
            
            # 检测是否Agent相关
            title_lower = title.lower()
            desc_lower = description.lower()
            tags_str = ' '.join(tags).lower()
            combined = f"{title_lower} {desc_lower} {tags_str}"
            
            is_agent_related = any(kw in combined for kw in self.AGENT_KEYWORDS)
            
            items.append(NewsItem(
                source=f"huggingface/{source_type}",
                title=title,
                url=url,
                author=model.get('author'),
                timestamp=model.get('lastModified', model.get('createdAt')),
                score=int(likes) if likes else None,
                content=description[:300] if description else None,
                tags=tags if tags else [],
                language="en"
            ))
        
        return items
    
    def _parse_papers(self, data: List) -> List[NewsItem]:
        """解析每日论文响应"""
        items = []
        
        for paper in data[:self.limit]:
            paper_id = paper.get('id', '')
            title = paper.get('title', paper.get('id', ''))
            
            # 获取链接和摘要
            url = f"https://huggingface.co/papers/{paper_id}"
            summary = paper.get('summary', paper.get('abstract', ''))
            likes = paper.get('likes', 0)
            published_date = paper.get('publishedDate', paper.get('date'))
            
            # 获取标签
            tags = paper.get('tags', [])[:5] if isinstance(paper.get('tags'), list) else []
            
            items.append(NewsItem(
                source="huggingface/papers",
                title=title,
                url=url,
                timestamp=published_date,
                score=int(likes) if likes else None,
                content=summary[:500] if summary else None,
                tags=tags if tags else ['AI', 'research'],
                language="en"
            ))
        
        return items
    
    async def fetch_trending(self) -> FetchResult:
        """获取HuggingFace热门模型/Spaces"""
        start_time = time.time()
        items = []
        
        try:
            # 获取热门模型
            response = self._make_request(f"{self.BASE_URL}/trending")
            
            if response:
                items = self._parse_trending(response)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'trending', 'count': len(items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_daily_papers(self) -> FetchResult:
        """获取每日论文"""
        start_time = time.time()
        items = []
        
        try:
            response = self._make_request(f"{self.BASE_URL}/daily_papers")
            
            if response and isinstance(response, list):
                items = self._parse_papers(response)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'daily_papers', 'count': len(items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_new_models(self) -> FetchResult:
        """获取最新发布的模型"""
        start_time = time.time()
        items = []
        
        try:
            url = f"{self.BASE_URL}/models?sort=lastModified&direction=-1&limit={self.limit}"
            response = self._make_request(url)
            
            if response and isinstance(response, list):
                items = self._parse_model_list(response)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'new_models', 'count': len(items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_all(self) -> FetchResult:
        """获取所有类型的热门内容（合并）"""
        start_time = time.time()
        all_items = []
        seen_urls = set()
        
        try:
            # 获取Trending
            trending_result = await self.fetch_trending()
            if trending_result.success:
                for item in trending_result.items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        all_items.append(item)
            
            time.sleep(0.5)
            
            # 获取最新模型
            new_models_result = await self.fetch_new_models()
            if new_models_result.success:
                for item in new_models_result.items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        all_items.append(item)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=all_items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'combined', 'count': len(all_items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )


# ============ ModelScope (魔搭) Fetcher (新增) ============
class ModelScopeFetcher(BaseFetcher):
    """
    ModelScope (魔搭) 抓取器 - 中国最大开源模型社区
    
    API端点:
    - 热门模型: https://modelscope.cn/api/v1/models?sort=downloads&direction=-1&limit=10
    
    备选方案: 如API不可用，使用search_web搜索 "modelscope 热门模型 最新"
    
    完全免费，无需API key
    
    信号映射:
    - 国产模型重大更新 → tech_breakthrough
    - 评测排行变化 → ecosystem_change
    - 平台功能更新 → platform_update
    
    重点关注: Qwen, DeepSeek, Yi, 通义, 智谱, 月之暗面等国产大模型
    """
    
    BASE_URL = "https://modelscope.cn/api/v1/models"
    
    # 重点关注的国产模型/厂商
    KEYWAREHOUSE_KEYWORDS = [
        'qwen', '通义', 'deepseek', 'yi', '智谱', 'glm', 'moonshot', '月之暗面',
        'minimax', '书生', 'falcon', 'chatglm', 'baichuan', 'internlm', 'lucida'
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "ModelScope"
        self.session_config['timeout'] = 10  # 10秒超时
        self.limit = config.get('limit', 10) if config else 10
    
    def _parse_model_response(self, data: Dict) -> List[NewsItem]:
        """解析魔搭API响应"""
        items = []
        
        # 处理分页响应格式
        models = []
        if isinstance(data, dict):
            if 'Data' in data and isinstance(data['Data'], list):
                models = data['Data']
            elif 'data' in data and isinstance(data['data'], list):
                models = data['data']
            elif 'models' in data and isinstance(data['models'], list):
                models = data['models']
        
        for model in models[:self.limit]:
            # 提取模型信息（兼容不同字段格式）
            if isinstance(model, dict):
                model_id = model.get('Name', model.get('name', model.get('model_id', '')))
                author = model.get('Path', model.get('path', '')).split('/')[0] if model.get('Path', model.get('path')) else None
                
                # 构建URL
                path = model.get('Path', model.get('path', ''))
                if path:
                    url = f"https://modelscope.cn/{path}"
                else:
                    url = f"https://modelscope.cn/models/{model_id}"
                
                # 获取指标
                downloads = model.get('Downloads', model.get('downloads', model.get('download_count', 0)))
                likes = model.get('Likes', model.get('likes', 0))
                description = model.get('Description', model.get('description', ''))
                tags = model.get('Tags', model.get('tags', []))[:5] if isinstance(model.get('Tags', model.get('tags')), list) else []
                
                # 更新时间
                last_modified = model.get('LastModifyTime', model.get('last_modified', model.get('UpdatedAt')))
                
                items.append(NewsItem(
                    source="modelscope",
                    title=model_id,
                    url=url,
                    author=author,
                    timestamp=last_modified,
                    score=int(downloads) if downloads else None,
                    content=description[:300] if description else None,
                    tags=tags if tags else [],
                    language="zh" if any(kw in (description or '').lower() for kw in ['中文', '中文大模型', '国产']) else "en"
                ))
        
        return items
    
    async def fetch_trending(self) -> FetchResult:
        """获取热门模型"""
        start_time = time.time()
        items = []
        
        try:
            url = f"{self.BASE_URL}?sort=downloads&direction=-1&limit={self.limit}"
            response = self._make_request(url)
            
            if response:
                items = self._parse_model_response(response)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'trending', 'count': len(items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_keywarehouse(self) -> FetchResult:
        """获取重点关注的国产模型（Qwen, DeepSeek等）"""
        start_time = time.time()
        items = []
        
        try:
            # 获取热门模型作为基础
            trending_result = await self.fetch_trending()
            
            if trending_result.success:
                # 过滤出国产相关模型
                for item in trending_result.items:
                    title_lower = (item.title or '').lower()
                    content_lower = (item.content or '').lower()
                    tags_str = ' '.join(item.tags or []).lower()
                    combined = f"{title_lower} {content_lower} {tags_str}"
                    
                    if any(kw in combined for kw in self.KEYWAREHOUSE_KEYWORDS):
                        items.append(item)
            
            return FetchResult(
                source=self.name,
                success=True,
                items=items,
                duration=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={'type': 'keywarehouse', 'count': len(items)}
            )
            
        except Exception as e:
            return FetchResult(
                source=self.name,
                success=False,
                items=[],
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def fetch_all(self) -> FetchResult:
        """获取所有内容"""
        start_time = time.time()
        
        # 直接获取热门
        result = await self.fetch_trending()
        result.duration = time.time() - start_time
        return result


# ============ Signal Processor (新增) ============
class SignalProcessor:
    """
    感知信号处理器 - 将NewsItem转换为PerceptionSignal
    
    信号类型：
    - security_threat: 安全威胁，需立即评估
    - paradigm_shift: 范式变化，评估采纳
    - ecosystem_change: 生态演进，关注跟进
    - platform_update: 平台变更，确认影响
    - tech_breakthrough: 技术突破，知识储备
    - market_signal: 市场信号，用户关注
    """
    
    # 信号分类关键词映射
    SIGNAL_PATTERNS = {
        SignalType.SECURITY_THREAT.value: [
            'vulnerability', 'cve', 'exploit', 'breach', 'hack', 'security',
            'attack', 'malware', 'ransomware', 'phishing', 'zero-day', 'patch',
            '安全漏洞', '安全威胁', '攻击', '泄露'
        ],
        SignalType.PARADIGM_SHIFT.value: [
            'paradigm', 'revolution', 'breakthrough', 'new architecture',
            'foundation model', 'emergent', 'self-evolving', 'autonomous',
            '范式', '革命', '突破', '新架构', '自进化'
        ],
        SignalType.ECOSYSTEM_CHANGE.value: [
            'release', 'launch', 'deprecate', 'open source', 'enterprise',
            'partnership', 'acquisition', 'funding', 'ecosystem',
            '发布', '开源', '合作', '收购', '融资', '生态'
        ],
        SignalType.PLATFORM_UPDATE.value: [
            'api', 'update', 'new feature', 'beta', 'deprecated', 'version',
            'platform', 'coze', '扣子', 'openai', 'anthropic',
            '更新', '新功能', '版本', '平台'
        ],
        SignalType.TECH_BREAKTHROUGH.value: [
            'paper', 'research', 'study', 'arxiv', 'benchmark', 'state-of-art',
            'performance', 'accuracy', 'improvement', 'novel',
            '论文', '研究', '基准', '性能突破'
        ],
        SignalType.MARKET_SIGNAL.value: [
            'stock', 'price', 'market', 'revenue', 'investment', 'IPO',
            'trend', 'forecast', 'report', 'analysis',
            '股价', '市场', '投资', '报告'
        ]
    }
    
    # 安全相关来源
    SECURITY_SOURCES = ['nvd', 'threatpost', 'securityweek', 'krebsonsecurity']
    
    # 学术来源
    RESEARCH_SOURCES = ['arxiv', 'paperswithcode', 'scholar']
    
    def __init__(self):
        self.last_process_time = None
    
    def classify_signal(self, item: NewsItem) -> tuple[str, bool, str]:
        """
        分类信号类型
        
        Returns:
            (signal_type, action_required, relevance)
        """
        title_lower = (item.title or '').lower()
        content_lower = (item.content or '').lower()
        source_lower = (item.source or '').lower()
        tags = ' '.join(item.tags or []).lower()
        
        combined_text = f"{title_lower} {content_lower} {tags}"
        
        # 1. 安全威胁检测（最高优先级）
        if item.source in self.SECURITY_SOURCES:
            severity = self._get_security_severity(item)
            return (
                SignalType.SECURITY_THREAT.value,
                severity in ['critical', 'high'],
                self._get_security_relevance(item)
            )
        
        # 检查标题和内容中的关键词
        matched_type = None
        for sig_type, keywords in self.SIGNAL_PATTERNS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    matched_type = sig_type
                    break
            if matched_type:
                break
        
        if not matched_type:
            # 默认归类为tech_breakthrough
            matched_type = SignalType.TECH_BREAKTHROUGH.value
        
        # 判断行动要求
        action_required = matched_type == SignalType.SECURITY_THREAT.value
        if matched_type == SignalType.PARADIGM_SHIFT.value:
            action_required = any(kw in combined_text for kw in ['self-evolving', 'autonomous', 'revolution', '范式'])
        
        relevance = self._generate_relevance(item, matched_type)
        
        return matched_type, action_required, relevance
    
    def _get_security_severity(self, item: NewsItem) -> str:
        """从安全条目获取严重程度"""
        tags = [t.lower() for t in (item.tags or [])]
        
        if 'critical' in tags:
            return 'critical'
        elif 'high' in tags:
            return 'high'
        elif 'medium' in tags:
            return 'medium'
        elif item.score and item.score >= 7:
            return 'high'
        elif item.score and item.score >= 4:
            return 'medium'
        
        return 'low'
    
    def _get_security_relevance(self, item: NewsItem) -> str:
        """生成安全相关性描述"""
        title_lower = (item.title or '').lower()
        
        if 'mcp' in title_lower:
            return "MCP相关漏洞，可能影响工具集成"
        elif 'openclaw' in title_lower:
            return "OpenClaw相关，需检查控制接口"
        elif 'llm' in title_lower or 'agent' in title_lower:
            return "AI/Agent相关，可能影响系统架构"
        elif 'stdio' in title_lower:
            return "STDIO传输漏洞，可能存在RCE风险"
        
        return "需评估对当前系统的影响"
    
    def _generate_relevance(self, item: NewsItem, signal_type: str) -> str:
        """生成相关性描述"""
        title = item.title or ''
        
        if signal_type == SignalType.SECURITY_THREAT.value:
            return "安全威胁，需立即评估"
        elif signal_type == SignalType.PARADIGM_SHIFT.value:
            return "范式变化，可能需要评估采纳"
        elif signal_type == SignalType.ECOSYSTEM_CHANGE.value:
            return "生态演进，需关注跟进"
        elif signal_type == SignalType.PLATFORM_UPDATE.value:
            if 'coze' in item.source.lower() or '扣子' in title:
                return "扣子平台变更，需确认影响"
            return "平台变更，需确认影响"
        elif signal_type == SignalType.TECH_BREAKTHROUGH.value:
            return "技术突破，知识储备"
        elif signal_type == SignalType.MARKET_SIGNAL.value:
            return "市场信号，用户可能关注"
        
        return "待评估"
    
    def process_results(self, results: Dict[str, FetchResult]) -> List[PerceptionSignal]:
        """
        处理所有抓取结果，转换为感知信号
        
        Args:
            results: Dict[str, FetchResult] - 原始抓取结果
            
        Returns:
            List[PerceptionSignal] - 结构化感知信号列表
        """
        signals = []
        
        for source, result in results.items():
            if not result.success:
                continue
            
            for item in result.items:
                try:
                    signal_type, action_required, relevance = self.classify_signal(item)
                    
                    # 获取严重程度
                    severity = 'info'
                    if signal_type == SignalType.SECURITY_THREAT.value:
                        severity = self._get_security_severity(item)
                    
                    signal = PerceptionSignal(
                        type=signal_type,
                        source=item.source,
                        title=item.title,
                        url=item.url,
                        relevance=relevance,
                        action_required=action_required,
                        severity=severity,
                        summary=item.content[:200] if item.content else item.extracted_summary,
                        timestamp=item.timestamp or datetime.now().isoformat(),
                        original_item=item.to_dict()
                    )
                    
                    signals.append(signal)
                    
                except Exception as e:
                    logger.warning(f"Error processing item: {e}")
                    continue
        
        # 按优先级排序：security_threat > paradigm_shift > others
        priority_order = [
            SignalType.SECURITY_THREAT.value,
            SignalType.PARADIGM_SHIFT.value,
            SignalType.ECOSYSTEM_CHANGE.value,
            SignalType.PLATFORM_UPDATE.value,
            SignalType.TECH_BREAKTHROUGH.value,
            SignalType.MARKET_SIGNAL.value
        ]
        
        signals.sort(key=lambda s: (
            priority_order.index(s.type) if s.type in priority_order else len(priority_order),
            0 if s.action_required else 1,
            -int(s.score or 0) if hasattr(s, 'score') else 0
        ))
        
        self.last_process_time = datetime.now().isoformat()
        return signals
    
    def generate_signal_report(self, signals: List[PerceptionSignal]) -> str:
        """生成感知信号报告"""
        lines = [
            "# Agent感知信号报告",
            "",
            f"**扫描时间**: {datetime.now().isoformat()}",
            f"**信号总数**: {len(signals)}",
            "",
            "---",
            ""
        ]
        
        # 统计
        signal_counts = {}
        action_required_count = 0
        
        for sig in signals:
            signal_counts[sig.type] = signal_counts.get(sig.type, 0) + 1
            if sig.action_required:
                action_required_count += 1
        
        lines.extend([
            "## 信号统计",
            "",
            f"| 信号类型 | 数量 |",
            f"|----------|------|",
        ])
        
        for sig_type, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
            emoji = {
                "security_threat": "🚨",
                "paradigm_shift": "🔄",
                "ecosystem_change": "🌐",
                "platform_update": "📦",
                "tech_breakthrough": "💡",
                "market_signal": "📈"
            }.get(sig_type, "📝")
            lines.append(f"| {emoji} {sig_type} | {count} |")
        
        lines.extend([
            "",
            f"**需要行动**: {action_required_count} 个",
            "",
            "---",
            ""
        ])
        
        # 按类型分组显示
        current_type = None
        for sig in signals:
            if sig.type != current_type:
                current_type = sig.type
                lines.extend([
                    f"## {current_type.upper().replace('_', ' ')}",
                    ""
                ])
            
            lines.append(sig.to_markdown())
            lines.append("")
        
        return "\n".join(lines)
    
    def export_signals_json(self, signals: List[PerceptionSignal], filepath: str):
        """导出信号为JSON"""
        output = {
            'scan_time': datetime.now().isoformat(),
            'total_signals': len(signals),
            'signals': [s.to_dict() for s in signals]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported signals to {filepath}")
    
    def get_action_required_signals(self, signals: List[PerceptionSignal]) -> List[PerceptionSignal]:
        """获取需要立即行动的信号"""
        return [s for s in signals if s.action_required]

# ============ Source Manager (新增) ============
class SourceManager:
    """
    信息源生命周期管理器
    
    功能：
    - 源质量指标追踪：成功率、响应时间、信号数量、行动率
    - 源生命周期管理：新增→试运行→评估→保留/淘汰/降级
    - 目标对齐度评估：源与Agent目标的匹配程度
    - 月度审计支持：评估每个源的质量指标
    """
    
    CONFIG_PATH = Path(__file__).parent / "sources_config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self.CONFIG_PATH
        self.config = self._load_config()
        self._init_fetch_history()
    
    def _load_config(self) -> Dict:
        """加载源配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "_version": "1.0",
            "sources": {},
            "lifecycle_rules": {
                "trial_period_days": 7,
                "min_success_rate": 0.7,
                "min_actionable_ratio": 0.1,
                "degrade_threshold": 0.5,
                "retire_threshold": 0.3
            }
        }
    
    def _init_fetch_history(self):
        """初始化采集历史"""
        for source_id in self.config.get('sources', {}):
            if 'fetch_history' not in self.config['sources'][source_id]:
                self.config['sources'][source_id]['fetch_history'] = []
    
    def _save_config(self):
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def record_fetch_result(self, source_id: str, result: FetchResult):
        """
        记录采集结果
        
        Args:
            source_id: 数据源ID
            result: FetchResult对象
        """
        if source_id not in self.config['sources']:
            # 新数据源，初始化
            self.config['sources'][source_id] = {
                'name': source_id,
                'type': 'unknown',
                'status': 'trial',
                'priority': 3,
                'aligned_goals': [],
                'quality_metrics': {
                    'success_rate': 0.0,
                    'avg_response_time_ms': 0,
                    'signal_count_7d': 0,
                    'actionable_ratio': 0.0
                },
                'last_fetch': None,
                'last_evaluated': datetime.now().date().isoformat(),
                'failure_history': [],
                'fetch_history': []
            }
        
        source = self.config['sources'][source_id]
        
        # 记录历史
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'success': result.success,
            'item_count': len(result.items),
            'duration_ms': int(result.duration * 1000),
            'error': result.error
        }
        source['fetch_history'].append(history_entry)
        
        # 保持历史不超过100条
        if len(source['fetch_history']) > 100:
            source['fetch_history'] = source['fetch_history'][-100:]
        
        source['last_fetch'] = datetime.now().isoformat()
        
        # 更新失败历史
        if not result.success:
            source['failure_history'].append({
                'timestamp': datetime.now().isoformat(),
                'error': result.error
            })
            # 保持失败历史不超过20条
            if len(source['failure_history']) > 20:
                source['failure_history'] = source['failure_history'][-20:]
        else:
            source['failure_history'] = []
        
        # 更新质量指标
        self._update_quality_metrics(source_id)
        
        # 保存
        self._save_config()
    
    def _update_quality_metrics(self, source_id: str):
        """更新质量指标"""
        source = self.config['sources'].get(source_id)
        if not source:
            return
        
        history = source.get('fetch_history', [])
        if not history:
            return
        
        # 计算最近7天的指标
        recent_history = self._get_recent_history(source_id, days=7)
        
        if recent_history:
            # 成功率
            success_count = sum(1 for h in recent_history if h.get('success'))
            success_rate = success_count / len(recent_history)
            
            # 平均响应时间
            durations = [h.get('duration_ms', 0) for h in recent_history if h.get('duration_ms')]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # 信号产出
            signal_count = sum(h.get('item_count', 0) for h in recent_history)
            
            source['quality_metrics'] = {
                'success_rate': round(success_rate, 2),
                'avg_response_time_ms': int(avg_duration),
                'signal_count_7d': signal_count,
                'actionable_ratio': self._calculate_actionable_ratio(source_id)
            }
    
    def _get_recent_history(self, source_id: str, days: int = 7) -> List[Dict]:
        """获取最近N天的历史记录"""
        source = self.config['sources'].get(source_id, {})
        history = source.get('fetch_history', [])
        
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for h in history:
            try:
                ts = datetime.fromisoformat(h['timestamp'])
                if ts >= cutoff:
                    recent.append(h)
            except:
                continue
        
        return recent
    
    def _calculate_actionable_ratio(self, source_id: str) -> float:
        """计算行动率（需要信号的信号数量/总信号数量）"""
        # 简化版本：基于失败率计算
        source = self.config['sources'].get(source_id, {})
        metrics = source.get('quality_metrics', {})
        
        success_rate = metrics.get('success_rate', 0.5)
        
        # 假设成功率高则行动率高
        return round(success_rate * 0.5, 2)
    
    def evaluate_source(self, source_id: str) -> Dict:
        """
        评估单个数据源
        
        Returns:
            评估结果，包含status建议
        """
        source = self.config['sources'].get(source_id, {})
        metrics = source.get('quality_metrics', {})
        rules = self.config.get('lifecycle_rules', {})
        
        success_rate = metrics.get('success_rate', 0)
        actionable_ratio = metrics.get('actionable_ratio', 0)
        current_status = source.get('status', 'active')
        
        # 评估逻辑
        recommendations = []
        new_status = current_status
        
        if success_rate < rules.get('retire_threshold', 0.3):
            new_status = 'retired'
            recommendations.append(f"成功率{success_rate:.1%}低于淘汰阈值{rules['retire_threshold']:.1%}")
        elif success_rate < rules.get('degrade_threshold', 0.5):
            new_status = 'degraded'
            recommendations.append(f"成功率{success_rate:.1%}低于降级阈值{rules['degrade_threshold']:.1%}")
        elif success_rate >= rules.get('auto_promote_threshold', 0.4) and current_status == 'trial':
            new_status = 'active'
            recommendations.append(f"成功率{success_rate:.1%}达到激活阈值，自动升级")
        
        if actionable_ratio < rules.get('min_actionable_ratio', 0.1):
            recommendations.append(f"行动率{actionable_ratio:.1%}低于最低要求{rules['min_actionable_ratio']:.1%}")
        
        return {
            'source_id': source_id,
            'current_status': current_status,
            'recommended_status': new_status,
            'metrics': metrics,
            'recommendations': recommendations,
            'auto_apply': new_status != current_status and new_status in ['degraded', 'retired']
        }
    
    def run_audit(self) -> Dict:
        """
        运行月度审计
        
        Returns:
            审计报告
        """
        audit_results = []
        active_sources = []
        degraded_sources = []
        retired_sources = []
        
        for source_id in self.config.get('sources', {}):
            eval_result = self.evaluate_source(source_id)
            audit_results.append(eval_result)
            
            status = eval_result['recommended_status']
            if status == 'active':
                active_sources.append(source_id)
            elif status == 'degraded':
                degraded_sources.append(source_id)
            elif status == 'retired':
                retired_sources.append(source_id)
            
            # 自动应用状态变更
            if eval_result['auto_apply']:
                self.config['sources'][source_id]['status'] = status
                self.config['sources'][source_id]['last_evaluated'] = datetime.now().date().isoformat()
        
        self._save_config()
        
        return {
            'audit_date': datetime.now().isoformat(),
            'total_sources': len(audit_results),
            'active_count': len(active_sources),
            'degraded_count': len(degraded_sources),
            'retired_count': len(retired_sources),
            'active_sources': active_sources,
            'degraded_sources': degraded_sources,
            'retired_sources': retired_sources,
            'details': audit_results
        }
    
    def get_active_sources(self, goal: Optional[str] = None) -> List[str]:
        """
        获取活跃数据源
        
        Args:
            goal: 目标类型（如security, self_evolution等）
            
        Returns:
            活跃数据源ID列表
        """
        if goal:
            # 按目标获取对应的数据源
            mapping = self.config.get('goal_source_mapping', {})
            goal_sources = mapping.get(goal, {})
            primary = goal_sources.get('primary', [])
            secondary = goal_sources.get('secondary', [])
            
            active = []
            for sid in primary + secondary:
                if self.is_source_active(sid):
                    active.append(sid)
            return active
        
        # 返回所有活跃数据源
        return [
            sid for sid, cfg in self.config.get('sources', {}).items()
            if cfg.get('status') in ['active', 'trial']
        ]
    
    def is_source_active(self, source_id: str) -> bool:
        """检查数据源是否活跃"""
        source = self.config['sources'].get(source_id, {})
        return source.get('status') in ['active', 'trial']
    
    def add_source(self, source_id: str, name: str, source_type: str = 'unknown',
                   aligned_goals: List[str] = None) -> bool:
        """
        添加新数据源
        
        Args:
            source_id: 数据源ID
            name: 数据源名称
            source_type: 类型
            aligned_goals: 对齐的目标
            
        Returns:
            是否添加成功
        """
        if source_id in self.config['sources']:
            logger.warning(f"Source {source_id} already exists")
            return False
        
        self.config['sources'][source_id] = {
            'name': name,
            'type': source_type,
            'status': 'trial',  # 新源进入试运行
            'priority': 3,
            'aligned_goals': aligned_goals or [],
            'quality_metrics': {
                'success_rate': 0.0,
                'avg_response_time_ms': 0,
                'signal_count_7d': 0,
                'actionable_ratio': 0.0
            },
            'last_fetch': None,
            'last_evaluated': datetime.now().date().isoformat(),
            'failure_history': [],
            'fetch_history': [],
            'added_date': datetime.now().date().isoformat()
        }
        
        self._save_config()
        logger.info(f"Added new source: {source_id}")
        return True
    
    def remove_source(self, source_id: str) -> bool:
        """移除数据源"""
        if source_id not in self.config['sources']:
            return False
        
        # 标记为已移除而不是直接删除（保留历史）
        self.config['sources'][source_id]['status'] = 'removed'
        self.config['sources'][source_id]['removed_date'] = datetime.now().date().isoformat()
        
        self._save_config()
        logger.info(f"Removed source: {source_id}")
        return True
    
    def generate_audit_report(self) -> str:
        """生成审计报告"""
        audit = self.run_audit()
        
        lines = [
            "# 信息源月度审计报告",
            "",
            f"**审计日期**: {audit['audit_date']}",
            f"**总数据源**: {audit['total_sources']}",
            "",
            "## 统计概览",
            "",
            f"| 状态 | 数量 |",
            f"|------|------|",
            f"| 🟢 活跃 | {audit['active_count']} |",
            f"| 🟡 降级 | {audit['degraded_count']} |",
            f"| 🔴 淘汰 | {audit['retired_count']} |",
            "",
            "## 活跃数据源",
            ", ".join(audit['active_sources']) or "无",
            "",
            "## 降级数据源",
        ]
        
        for source_id in audit['degraded_sources']:
            details = next((d for d in audit['details'] if d['source_id'] == source_id), None)
            if details:
                lines.append(f"- **{source_id}**: {', '.join(details['recommendations'])}")
        
        lines.extend([
            "",
            "## 淘汰数据源",
        ])
        
        for source_id in audit['retired_sources']:
            details = next((d for d in audit['details'] if d['source_id'] == source_id), None)
            if details:
                lines.append(f"- **{source_id}**: {', '.join(details['recommendations'])}")
        
        lines.extend([
            "",
            "## 质量指标详情",
            "",
            "| 数据源 | 成功率 | 响应时间 | 7天信号 | 行动率 | 状态 |",
            "|------|--------|----------|---------|--------|------|",
        ])
        
        for details in audit['details']:
            m = details['metrics']
            lines.append(f"| {details['source_id']} | {m.get('success_rate', 0):.0%} | {m.get('avg_response_time_ms', 0)}ms | {m.get('signal_count_7d', 0)} | {m.get('actionable_ratio', 0):.0%} | {details['recommended_status']} |")
        
        return "\n".join(lines)

# ============ Main Aggregator (感知增强版) ============
class GlobalInfoAggregator:
    """
    全球信息聚合器 (v3.0 - Agent感知基础设施)
    
    核心升级：
    - 新增感知层数据源：arXiv, NVD/CVE, Coze
    - 感知信号处理：从文章列表到结构化信号
    - 信号驱动自进化：安全威胁自动评估
    - 新增金融数据感知：iTick, AKShare, Binance, FRED
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        self.fetchers = {
            # 原有数据源
            'hackernews': HackerNewsFetcher(self.config.get('hackernews')),
            'reddit': RedditFetcher(self.config.get('reddit')),
            'github_trending': GitHubTrendingFetcher(self.config.get('github')),
            'lobste': LobstersFetcher(self.config.get('lobste')),
            'rss': RSSFetcher(self.config.get('rss')),
            'twitter': TwitterFetcher(self.config.get('twitter')),
            'agent_news': AgentNewsFetcher(self.config.get('agent')),
            # 新增感知数据源
            'arxiv': ArxivFetcher(self.config.get('arxiv')),
            'nvd': NVDFetcher(self.config.get('nvd')),
            'coze': CozeFetcher(self.config.get('coze')),
            # 新增大模型社区数据源
            'huggingface': HuggingFaceFetcher(self.config.get('huggingface')),
            'modelscope': ModelScopeFetcher(self.config.get('modelscope')),
        }
        
        # 初始化金融数据Fetcher
        try:
            from finance_fetcher import FinanceFetcher
            self.finance_fetcher = FinanceFetcher(
                config_path="./skills/global-info-fetcher/sources_config.json",
                secret_path="./SECRET.md"
            )
            logger.info("Finance Fetcher initialized successfully")
        except ImportError as e:
            logger.warning(f"Finance Fetcher not available: {e}")
            self.finance_fetcher = None
        except Exception as e:
            logger.warning(f"Finance Fetcher initialization failed: {e}")
            self.finance_fetcher = None
        
        # 信号处理器
        self.signal_processor = SignalProcessor()
        
        # 源管理器
        self.source_manager = SourceManager()
        
        self.results_cache = {}
        self.cache_duration = self.config.get('cache_duration', 300)
    
    def fetch_finance_data(self, symbols: List[str] = None, market: str = "US") -> Dict[str, Any]:
        """
        获取金融数据
        
        Args:
            symbols: 股票代码列表，默认使用预设观察列表
            market: 市场类型 (US/HK/SH/SZ/CC)
            
        Returns:
            Dict包含 quotes, signals, health
        """
        if not self.finance_fetcher:
            return {
                'success': False,
                'error': 'Finance Fetcher not available',
                'quotes': [],
                'signals': [],
                'health': {}
            }
        
        # 默认观察列表
        default_watchlist = {
            "US": ["AAPL", "GOOGL", "MSFT", "NVDA"],
            "HK": ["00700", "09988"],
            "CC": ["BTCUSDT", "ETHUSDT"],
            "SH": ["600519", "600036"],
            "SZ": ["000001"]
        }
        
        result = {
            'success': True,
            'quotes': [],
            'signals': [],
            'health': self.finance_fetcher.health_check(),
            'timestamp': datetime.now().isoformat()
        }
        
        # 如果指定了symbols和market
        if symbols and market:
            result['quotes'] = self.finance_fetcher.get_market_snapshot(symbols, market)
            
            # 扫描信号
            watchlist = {market: symbols}
            result['signals'] = self.finance_fetcher.scan_signals(watchlist)
        else:
            # 使用默认观察列表扫描所有市场
            all_signals = []
            for mkt, syms in default_watchlist.items():
                quotes = self.finance_fetcher.get_market_snapshot(syms, mkt)
                result['quotes'].extend(quotes)
                
                # 扫描信号
                signals = self.finance_fetcher.scan_signals({mkt: syms})
                all_signals.extend(signals)
            
            result['signals'] = all_signals
        
        return result
    
    def get_finance_report(self, symbols: List[str] = None, market: str = "US") -> str:
        """
        生成金融数据报告
        
        Args:
            symbols: 股票代码列表
            market: 市场类型
            
        Returns:
            Markdown格式报告
        """
        data = self.fetch_finance_data(symbols, market)
        
        lines = [
            "# 金融感知报告",
            "",
            f"**生成时间**: {data.get('timestamp', datetime.now().isoformat())}",
            "",
            "## 数据源健康状态",
            ""
        ]
        
        # 健康状态
        health = data.get('health', {})
        if health:
            lines.extend([
                "| 数据源 | 状态 |",
                "|--------|------|"
            ])
            for source, status in health.items():
                icon = "✅" if status else "❌"
                lines.append(f"| {source} | {icon} |")
        else:
            lines.append("数据源状态不可用")
        
        lines.extend(["", "## 市场行情", ""])
        
        # 行情报价
        quotes = data.get('quotes', [])
        if quotes:
            lines.extend([
                "| 标的 | 名称 | 价格 | 涨跌幅 | 成交量 |",
                "|------|------|------|--------|--------|"
            ])
            for quote in quotes[:20]:  # 最多显示20个
                lines.append(quote.to_markdown())
        else:
            lines.append("暂无行情数据")
        
        lines.extend(["", "## 市场信号", ""])
        
        # 信号
        signals = data.get('signals', [])
        if signals:
            lines.extend([
                "| 类型 | 标的 | 严重程度 | 摘要 |",
                "|------|------|----------|------|"
            ])
            for sig in signals[:10]:  # 最多显示10个
                lines.append(f"| {sig.signal_type} | {sig.symbol} | {sig.severity} | {sig.summary[:50] if sig.summary else ''}... |")
        else:
            lines.append("✅ 未检测到异常信号")
        
        return "\n".join(lines)
    
    def get_finance_signals(self) -> List:
        """
        获取金融信号列表
        
        Returns:
            FinancePerceptionSignal 列表
        """
        data = self.fetch_finance_data()
        return data.get('signals', [])
    
    async def fetch_all(self, sources: Optional[List[str]] = None,
                        extract_content: bool = False,
                        include_perception: bool = True) -> Dict[str, FetchResult]:
        """
        并行获取所有或指定数据源
        
        Args:
            sources: 要获取的数据源列表，None表示全部
            extract_content: 是否提取文章正文（会增加耗时）
            include_perception: 是否包含感知层数据源（arXiv, NVD, Coze）
        """
        import asyncio
        
        if sources is None:
            if include_perception:
                sources = ['hackernews', 'reddit', 'github_trending', 'lobste', 'rss', 'agent_news', 'arxiv', 'nvd', 'coze', 'huggingface', 'modelscope']
            else:
                sources = ['hackernews', 'reddit', 'github_trending', 'lobste', 'rss', 'agent_news', 'huggingface', 'modelscope']
        
        # 过滤有效源
        active_sources = [s for s in sources if s in self.fetchers and s != 'twitter']
        
        # 并行执行
        tasks = []
        for source in active_sources:
            fetcher = self.fetchers[source]
            if source == 'hackernews':
                tasks.append(fetcher.fetch_top_stories(30, extract_content=extract_content))
            elif source == 'reddit':
                tasks.append(fetcher.fetch_all(20))
            elif source == 'github_trending':
                lang = self.config.get('github', {}).get('language', '')
                tasks.append(fetcher.fetch_trending(language=lang, since='daily'))
            elif source == 'lobste':
                tasks.append(fetcher.fetch_hot(30))
            elif source == 'rss':
                tasks.append(fetcher.fetch_all(extract_content=extract_content))
            elif source == 'agent_news':
                tasks.append(fetcher.fetch_all())
            elif source == 'arxiv':
                tasks.append(fetcher.fetch_multi_keywords())
            elif source == 'nvd':
                tasks.append(fetcher.fetch_high_severity())
            elif source == 'coze':
                tasks.append(fetcher.fetch_platform_news())
            elif source == 'huggingface':
                tasks.append(fetcher.fetch_all())
            elif source == 'modelscope':
                tasks.append(fetcher.fetch_all())
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for i, source in enumerate(active_sources):
            if isinstance(results_list[i], Exception):
                result = FetchResult(
                    source=source,
                    success=False,
                    items=[],
                    error=str(results_list[i]),
                    duration=0.0,
                    timestamp=datetime.now().isoformat()
                )
            else:
                result = results_list[i]
            
            output[source] = result
            
            # 记录到源管理器
            self.source_manager.record_fetch_result(source, result)
        
        self.results_cache = output
        return output
    
    def get_perception_signals(self, results: Optional[Dict[str, FetchResult]] = None) -> List[PerceptionSignal]:
        """
        获取感知信号（从原始结果转换为结构化信号）
        
        Args:
            results: 原始抓取结果，None使用缓存结果
            
        Returns:
            List[PerceptionSignal] - 感知信号列表
        """
        if results is None:
            results = self.results_cache
        
        return self.signal_processor.process_results(results)
    
    def get_action_required_signals(self, results: Optional[Dict[str, FetchResult]] = None) -> List[PerceptionSignal]:
        """获取需要立即行动的信号"""
        signals = self.get_perception_signals(results)
        return self.signal_processor.get_action_required_signals(signals)
    
    def generate_perception_report(self, results: Optional[Dict[str, FetchResult]] = None) -> str:
        """生成感知信号报告"""
        signals = self.get_perception_signals(results)
        return self.signal_processor.generate_signal_report(signals)
    
    def export_perception_json(self, filepath: str, results: Optional[Dict[str, FetchResult]] = None):
        """导出感知信号为JSON"""
        signals = self.get_perception_signals(results)
        self.signal_processor.export_signals_json(signals, filepath)
    
    def get_combined_feed(self, results: Optional[Dict[str, FetchResult]] = None, 
                          sort_by: str = 'score') -> List[NewsItem]:
        """合并所有数据源的新闻"""
        if results is None:
            results = self.results_cache
        
        all_items = []
        for result in results.values():
            if result.success:
                all_items.extend(result.items)
        
        if sort_by == 'score':
            all_items.sort(key=lambda x: x.score or 0, reverse=True)
        elif sort_by == 'time':
            all_items.sort(key=lambda x: x.timestamp or '', reverse=True)
        
        return all_items
    
    def export_to_json(self, results: Dict[str, FetchResult], filepath: str):
        """导出结果为JSON"""
        output = {}
        for source, result in results.items():
            output[source] = result.to_dict()
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported results to {filepath}")
    
    def export_to_markdown(self, results: Dict[str, FetchResult], 
                           filepath: str,
                           include_content: bool = False):
        """导出结果为Markdown (LLM友好格式)"""
        lines = [
            "# Global Tech News Report",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Sources**: {', '.join(results.keys())}",
            "",
            "---",
            ""
        ]
        
        total_items = 0
        for source, result in results.items():
            lines.append(result.to_markdown())
            lines.append("")
            total_items += len(result.items)
        
        lines.extend([
            "---",
            "",
            f"**Total Items**: {total_items}",
            "",
            "*Generated by Global Info Fetcher v2.0*"
        ])
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        logger.info(f"Exported Markdown to {filepath}")
    
    def generate_report(self, results: Dict[str, FetchResult], 
                        format: OutputFormat = OutputFormat.MARKDOWN) -> str:
        """生成测试报告"""
        if format == OutputFormat.JSON:
            return json.dumps({k: v.to_dict() for k, v in results.items()}, 
                             ensure_ascii=False, indent=2)
        
        # Markdown格式（默认）
        report = ["# Global Info Fetcher v2.0 - Test Report", ""]
        report.append(f"**Generated**: {datetime.now().isoformat()}")
        report.append("")
        report.append("## Summary")
        report.append("")
        
        total_items = 0
        success_count = 0
        
        for source, result in results.items():
            status = "✅" if result.success else "❌"
            report.append(f"- **{source}**: {status}")
            if result.success:
                report.append(f"  - Items: {len(result.items)}")
                report.append(f"  - Duration: {result.duration:.2f}s")
                total_items += len(result.items)
                success_count += 1
            else:
                report.append(f"  - Error: {result.error}")
        
        report.extend([
            "",
            f"**Total Items**: {total_items}",
            f"**Success Rate**: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)",
            "",
            "---",
            "",
            "## Detailed Results"
        ])
        
        for source, result in results.items():
            report.append("")
            report.append(result.to_markdown())
        
        return "\n".join(report)

# ============ CLI Interface (感知版) ============
async def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Global Info Fetcher v3.0 - Agent感知基础设施',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 获取所有数据源（包含感知层）
  python global_info_fetcher.py --report
  
  # 仅获取原始数据源（不含感知层）
  python global_info_fetcher.py --no-perception --report
  
  # 获取特定数据源
  python global_info_fetcher.py --sources hackernews reddit
  
  # 生成感知信号报告（Agent自进化驱动）
  python global_info_fetcher.py --perception-report --output ./signals.json
  
  # 获取安全威胁信号
  python global_info_fetcher.py --security-only
  
  # 提取文章正文（会增加耗时）
  python global_info_fetcher.py --extract-content --report
  
  # 获取金融数据
  python global_info_fetcher.py --finance --symbols AAPL GOOGL --market US
  
  # 生成金融感知报告
  python global_info_fetcher.py --finance-report --output ./finance-report.md
        """
    )
    parser.add_argument('--sources', nargs='+', default=None,
                       help='数据源: hackernews, reddit, github_trending, lobste, rss, agent_news, arxiv, nvd, coze')
    parser.add_argument('--output', '-o', default='./output/news.json',
                       help='输出文件路径 (默认: ./output/news.json)')
    parser.add_argument('--format', '-f', choices=['markdown', 'json', 'simple'], 
                       default='markdown', help='输出格式')
    parser.add_argument('--report', '-r', action='store_true',
                       help='生成测试报告')
    parser.add_argument('--extract-content', '-e', action='store_true',
                       help='使用Jina Reader提取文章正文')
    parser.add_argument('--twitter-info', '-t', action='store_true',
                       help='显示Twitter/X替代方案说明')
    parser.add_argument('--no-perception', action='store_true',
                       help='不包含感知层数据源（arXiv, NVD, Coze）')
    parser.add_argument('--perception-report', '-p', action='store_true',
                       help='生成感知信号报告（驱动自进化）')
    parser.add_argument('--security-only', '-s', action='store_true',
                       help='仅获取安全威胁信号')
    parser.add_argument('--audit', '-a', action='store_true',
                       help='运行信息源月度审计')
    
    # 金融数据参数
    parser.add_argument('--finance', action='store_true',
                       help='获取金融数据')
    parser.add_argument('--finance-report', action='store_true',
                       help='生成金融感知报告')
    parser.add_argument('--symbols', nargs='+', default=None,
                       help='股票代码列表，如: AAPL GOOGL')
    parser.add_argument('--market', default='US',
                       help='市场类型 (US/HK/SH/SZ/CC)，默认: US')
    
    args = parser.parse_args()
    
    # Twitter方案说明
    if args.twitter_info:
        twitter = TwitterFetcher()
        print(twitter.get_recommendation())
        return
    
    # 审计模式（不获取数据）
    if args.audit:
        print("🔍 运行信息源月度审计...")
        source_manager = SourceManager()
        report = source_manager.generate_audit_report()
        print("\n" + report)
        
        # 导出审计报告
        report_path = './source-audit-report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📝 审计报告已保存: {report_path}")
        return
    
    aggregator = GlobalInfoAggregator()
    
    print("🌐 Global Info Fetcher v3.0 - Agent感知基础设施")
    
    # 感知模式 vs 传统模式
    include_perception = not args.no_perception
    
    # 获取数据
    results = await aggregator.fetch_all(
        args.sources, 
        extract_content=args.extract_content,
        include_perception=include_perception
    )
    
    # 感知信号报告模式
    if args.perception_report:
        print("\n🔮 生成感知信号报告...")
        report = aggregator.generate_perception_report(results)
        print("\n" + report)
        
        # 导出感知信号JSON
        output_path = args.output.replace('.json', '-signals.json') if args.output else './signals.json'
        aggregator.export_perception_json(output_path, results)
        print(f"\n📡 感知信号已导出: {output_path}")
        
        # 提示需要行动的信号
        action_signals = aggregator.get_action_required_signals(results)
        if action_signals:
            print(f"\n🚨 需要立即关注的信号 ({len(action_signals)} 个):")
            for sig in action_signals[:5]:
                print(f"  - [{sig.type}] {sig.title[:60]}...")
        return
    
    # 金融数据模式
    if args.finance or args.finance_report:
        print("\n💹 获取金融数据...")
        
        # 生成金融报告
        finance_report = aggregator.get_finance_report(
            symbols=args.symbols,
            market=args.market
        )
        print("\n" + finance_report)
        
        # 导出金融报告
        output_path = args.output if args.output else './finance-report.md'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(finance_report)
        print(f"\n💾 金融报告已保存: {output_path}")
        return
    
    # 安全威胁模式
    if args.security_only:
        print("\n🚨 获取安全威胁信号...")
        signals = aggregator.get_perception_signals(results)
        security_signals = [s for s in signals if s.type == SignalType.SECURITY_THREAT.value]
        
        if security_signals:
            print(f"\n发现 {len(security_signals)} 个安全威胁:")
            for sig in security_signals:
                print(f"\n{sig.to_markdown()}")
        else:
            print("未发现安全威胁 ✅")
        return
    
    # 生成报告
    if args.report:
        fmt = OutputFormat.MARKDOWN if args.format == 'markdown' else OutputFormat.JSON
        report = aggregator.generate_report(results, fmt)
        print("\n" + report)
        
        report_path = './test-report.md' if args.format != 'json' else './test-report.json'
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\n📝 Report saved to {report_path}")
    
    # 导出
    if args.format == 'markdown':
        aggregator.export_to_markdown(results, args.output, include_content=args.extract_content)
    else:
        aggregator.export_to_json(results, args.output)
    
    # 合并输出
    combined = aggregator.get_combined_feed(results)
    print(f"\n📊 Total items fetched: {len(combined)}")
    print(f"💾 Results saved to: {args.output}")
    
    # 显示感知信号摘要
    if include_perception:
        signals = aggregator.get_perception_signals(results)
        action_signals = aggregator.get_action_required_signals(results)
        print(f"\n🔮 感知信号: {len(signals)} 个 (需行动: {len(action_signals)})")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
