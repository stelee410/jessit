"""
Market Pulse Observer - 市场脉搏观察者
自动收集和分析多个网站的趋势数据，跟踪叙事转变和信号强度
"""

import json
import time
import logging
import threading
import queue
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re

try:
    from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from src.utils.path_utils import resolve_path

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class TrendItem:
    """趋势项"""
    title: str
    source: str
    url: str
    timestamp: str
    category: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral


@dataclass
class AnalysisResult:
    """分析结果"""
    date: str
    trends: List[TrendItem]
    narrative_shifts: List[str]
    recurring_topics: List[Tuple[str, int]]  # (topic, count)
    first_appearances: List[str]
    sentiment_changes: Dict[str, str]  # topic -> change direction
    signal_strength: int  # 1-5


@dataclass
class HistoricalData:
    """历史数据"""
    date: str
    trends: List[TrendItem]
    topics: List[str]
    sentiment: Dict[str, str]


class BrowserCollector:
    """浏览器数据收集器（使用 Playwright）"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._thread = None
        self._queue = None
        self._result_queue = None
        self._in_thread = False
        
    def _init_playwright(self):
        """初始化 Playwright（必须在创建它的线程中调用）"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright 未安装，请运行: pip install playwright && playwright install chromium")
        
        try:
            self.playwright = sync_playwright().start()
            # 启动浏览器，设置超时和选项
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            # 创建页面，设置超时和用户代理
            context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            self.page = context.new_page()
            # 设置默认超时（Playwright 会自动等待元素）
            self.page.set_default_timeout(30000)  # 30秒
            self.page.set_default_navigation_timeout(30000)  # 30秒
        except Exception as e:
            logger.error(f"无法启动浏览器: {e}")
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
            raise
    
        
    def __enter__(self):
        # 检查是否在 asyncio 事件循环中
        try:
            loop = asyncio.get_running_loop()
            # 如果在事件循环中，需要在新线程中运行所有操作
            logger.debug("检测到 asyncio 事件循环，将在新线程中运行所有 Playwright 操作")
            self._in_thread = True
            self._queue = queue.Queue()
            self._result_queue = queue.Queue()
            self._exception = None
            self._init_complete = threading.Event()
            
            def thread_worker():
                """工作线程：运行所有 Playwright 操作"""
                try:
                    # 在新线程中初始化
                    self._init_playwright()
                    self._init_complete.set()
                    
                    # 处理队列中的操作
                    while True:
                        try:
                            item = self._queue.get(timeout=1)
                            if item is None:  # 退出信号
                                break
                            
                            op_type, func, args, kwargs, result_container = item
                            if op_type == "call":
                                try:
                                    result = func(*args, **kwargs)
                                    result_container["result"] = result
                                except Exception as e:
                                    result_container["exception"] = e
                                finally:
                                    result_container["event"].set()
                        except queue.Empty:
                            continue
                except Exception as e:
                    self._exception = e
                    self._init_complete.set()
                finally:
                    # 清理资源
                    try:
                        if self.page:
                            self.page.close()
                    except:
                        pass
                    try:
                        if self.browser:
                            self.browser.close()
                    except:
                        pass
                    try:
                        if self.playwright:
                            self.playwright.stop()
                    except:
                        pass
            
            self._thread = threading.Thread(target=thread_worker, daemon=False)
            self._thread.start()
            self._init_complete.wait()
            
            if self._exception:
                raise self._exception
        except RuntimeError:
            # 没有运行的事件循环，直接运行
            self._init_playwright()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._in_thread and self._thread:
            # 发送退出信号
            self._queue.put(None)
            self._thread.join(timeout=10)  # 等待线程结束
        else:
            # 直接清理
            try:
                if self.page:
                    try:
                        self.page.close()
                    except:
                        pass
                if self.browser:
                    try:
                        self.browser.close()
                    except Exception as e:
                        logger.warning(f"关闭浏览器时出错: {e}")
                if self.playwright:
                    try:
                        self.playwright.stop()
                    except Exception as e:
                        logger.warning(f"停止 Playwright 时出错: {e}")
            finally:
                self.page = None
                self.browser = None
                self.playwright = None
    
    def _collect_x_trending_impl(self) -> List[TrendItem]:
        """收集 X.com 趋势数据的实际实现（在 Playwright 线程中运行）"""
        trends = []
        try:
            logger.info("正在收集 X.com 趋势数据...")
            try:
                # Playwright 会自动等待页面加载
                self.page.goto("https://x.com/explore/tabs/trending", wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("页面加载超时，继续尝试提取数据...")
            
            # Playwright 自动等待，只需短暂延迟让动态内容加载
            try:
                self.page.wait_for_selector("body", timeout=5000)
            except PlaywrightTimeoutError:
                logger.warning("等待页面元素超时，继续尝试...")
            
            # 等待一小段时间让动态内容加载
            self.page.wait_for_timeout(2000)
            
            # 尝试多种选择器来获取趋势项
            selectors = [
                "article[data-testid='tweet']",
                "[data-testid='trend']",
                "div[role='article']",
                ".trend-item"
            ]
            
            elements = []
            for selector in selectors:
                try:
                    # Playwright 的 query_selector_all 返回元素列表
                    elements = self.page.query_selector_all(selector)
                    if elements:
                        break
                except:
                    continue
            
            for i, element in enumerate(elements[:20]):  # 限制前20个
                try:
                    # 提取文本内容
                    text_content = element.text_content()
                    if text_content:
                        title = text_content.strip()[:200]  # 限制长度
                    else:
                        # 尝试从子元素获取文本
                        text_elem = element.query_selector("span, a, div")
                        title = text_elem.text_content().strip()[:200] if text_elem else ""
                    
                    # 尝试获取链接
                    url = ""
                    try:
                        # 先尝试查找内部的链接
                        link_elem = element.query_selector("a[href]")
                        if link_elem:
                            url = link_elem.get_attribute("href") or ""
                        
                        # 如果没有，尝试查找父级链接
                        if not url:
                            parent_a = element.evaluate("el => { const a = el.closest('a'); return a ? a.href : null; }")
                            if parent_a:
                                url = parent_a
                    except:
                        pass
                    
                    if title:
                        trends.append(TrendItem(
                            title=title,
                            source="X.com",
                            url=url or f"https://x.com/explore/tabs/trending",
                            timestamp=datetime.now().isoformat(),
                            category="trending"
                        ))
                except Exception as e:
                    logger.debug(f"提取趋势项失败: {e}")
                    continue
            
            logger.info(f"收集到 {len(trends)} 个 X.com 趋势项")
            
        except Exception as e:
            logger.error(f"收集 X.com 趋势数据失败: {e}")
        
        return trends
    
    def collect_x_trending(self) -> List[TrendItem]:
        """收集 X.com (Twitter) 趋势数据"""
        if self._in_thread:
            result_container = {"result": None, "exception": None, "event": threading.Event()}
            self._queue.put(("call", self._collect_x_trending_impl, (), {}, result_container))
            result_container["event"].wait()
            if result_container["exception"]:
                raise result_container["exception"]
            return result_container["result"]
        else:
            return self._collect_x_trending_impl()
    
    def _collect_financial_news_impl(self) -> List[TrendItem]:
        """收集金融新闻首页数据的实际实现（在 Playwright 线程中运行）"""
        trends = []
        
        # 金融新闻网站列表
        news_sites = [
            ("Bloomberg", "https://www.bloomberg.com"),
            ("Reuters", "https://www.reuters.com"),
            ("Financial Times", "https://www.ft.com"),
            ("WSJ", "https://www.wsj.com"),
        ]
        
        for site_name, url in news_sites:
            try:
                logger.info(f"正在收集 {site_name} 新闻...")
                try:
                    self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except PlaywrightTimeoutError:
                    logger.warning(f"{site_name} 页面加载超时，继续尝试提取数据...")
                
                # Playwright 自动等待元素
                try:
                    self.page.wait_for_selector("body", timeout=8000)
                except PlaywrightTimeoutError:
                    logger.warning(f"{site_name} 等待页面元素超时，继续尝试...")
                
                # 等待动态内容加载
                self.page.wait_for_timeout(2000)
                
                # 尝试多种选择器
                selectors = [
                    "article h1, article h2, article h3",
                    ".headline, .title",
                    "[data-module='Article'] h1, [data-module='Article'] h2",
                    "a[href*='/article/'], a[href*='/news/']"
                ]
                
                headlines = []
                for selector in selectors:
                    try:
                        elements = self.page.query_selector_all(selector)
                        for elem in elements[:10]:  # 每个网站限制10条
                            text = elem.text_content()
                            if text:
                                text = text.strip()
                                if text and len(text) > 10:  # 过滤太短的文本
                                    # 尝试获取链接
                                    url_link = ""
                                    try:
                                        # 尝试查找父级链接或元素本身的链接
                                        href = elem.evaluate("el => { const a = el.closest('a') || (el.tagName === 'A' ? el : null); return a ? a.href : null; }")
                                        if href:
                                            url_link = href
                                    except:
                                        pass
                                    
                                    if not url_link:
                                        url_link = url
                                    headlines.append((text[:200], url_link))
                        if headlines:
                            break
                    except:
                        continue
                
                for title, link in headlines[:5]:  # 每个网站最多5条
                    trends.append(TrendItem(
                        title=title,
                        source=site_name,
                        url=link,
                        timestamp=datetime.now().isoformat(),
                        category="financial_news"
                    ))
                
                logger.info(f"从 {site_name} 收集到 {len(headlines)} 条新闻")
                
            except Exception as e:
                logger.warning(f"收集 {site_name} 新闻失败: {e}")
                continue
        
        return trends
    
    def collect_financial_news(self) -> List[TrendItem]:
        """收集金融新闻首页数据"""
        if self._in_thread:
            result_container = {"result": None, "exception": None, "event": threading.Event()}
            self._queue.put(("call", self._collect_financial_news_impl, (), {}, result_container))
            result_container["event"].wait()
            if result_container["exception"]:
                raise result_container["exception"]
            return result_container["result"]
        else:
            return self._collect_financial_news_impl()
    
    def _collect_ai_media_impl(self) -> List[TrendItem]:
        """收集 AI 特定媒体数据的实际实现（在 Playwright 线程中运行）"""
        trends = []
        
        ai_sites = [
            ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence"),
            ("TechCrunch AI", "https://techcrunch.com/tag/artificial-intelligence/"),
        ]
        
        for site_name, url in ai_sites:
            try:
                logger.info(f"正在收集 {site_name} 数据...")
                try:
                    self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except PlaywrightTimeoutError:
                    logger.warning(f"{site_name} 页面加载超时，继续尝试提取数据...")
                
                # Playwright 自动等待元素
                try:
                    self.page.wait_for_selector("body", timeout=8000)
                except PlaywrightTimeoutError:
                    logger.warning(f"{site_name} 等待页面元素超时，继续尝试...")
                
                # 等待动态内容加载
                self.page.wait_for_timeout(2000)
                
                selectors = [
                    "article h1, article h2",
                    ".headline, .title",
                    "a[href*='/ai/'], a[href*='/artificial-intelligence/']"
                ]
                
                headlines = []
                for selector in selectors:
                    try:
                        elements = self.page.query_selector_all(selector)
                        for elem in elements[:10]:
                            text = elem.text_content()
                            if text:
                                text = text.strip()
                                if text and len(text) > 10:
                                    # 尝试获取链接
                                    url_link = ""
                                    try:
                                        # 尝试查找父级链接或元素本身的链接
                                        href = elem.evaluate("el => { const a = el.closest('a') || (el.tagName === 'A' ? el : null); return a ? a.href : null; }")
                                        if href:
                                            url_link = href
                                    except:
                                        pass
                                    
                                    if not url_link:
                                        url_link = url
                                    headlines.append((text[:200], url_link))
                        if headlines:
                            break
                    except:
                        continue
                
                for title, link in headlines[:5]:
                    trends.append(TrendItem(
                        title=title,
                        source=site_name,
                        url=link,
                        timestamp=datetime.now().isoformat(),
                        category="ai_media"
                    ))
                
            except Exception as e:
                logger.warning(f"收集 {site_name} 数据失败: {e}")
                continue
        
        return trends
    
    def collect_ai_media(self) -> List[TrendItem]:
        """收集 AI 特定媒体数据"""
        if self._in_thread:
            result_container = {"result": None, "exception": None, "event": threading.Event()}
            self._queue.put(("call", self._collect_ai_media_impl, (), {}, result_container))
            result_container["event"].wait()
            if result_container["exception"]:
                raise result_container["exception"]
            return result_container["result"]
        else:
            return self._collect_ai_media_impl()


class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_topics(self, trends: List[TrendItem]) -> List[str]:
        """从趋势中提取主题"""
        # 简单的关键词提取（可以后续改进为更复杂的NLP方法）
        all_text = " ".join([t.title for t in trends]).lower()
        
        # 常见金融和科技关键词
        keywords = [
            "ai", "artificial intelligence", "machine learning",
            "crypto", "bitcoin", "ethereum", "blockchain",
            "stock", "market", "trading", "investment",
            "fed", "federal reserve", "interest rate",
            "inflation", "recession", "economy",
            "tech", "technology", "startup", "ipo",
            "regulation", "policy", "government"
        ]
        
        topics = []
        for keyword in keywords:
            if keyword in all_text:
                topics.append(keyword)
        
        # 提取常见短语（2-3个词）
        words = re.findall(r'\b\w+\b', all_text)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
        
        # 统计频率
        phrase_counts = Counter(bigrams + trigrams)
        common_phrases = [phrase for phrase, count in phrase_counts.most_common(10) if count >= 2]
        topics.extend(common_phrases[:5])
        
        return list(set(topics))
    
    def detect_narrative_shifts(self, current: List[TrendItem], historical: Optional[HistoricalData]) -> List[str]:
        """检测叙事转变"""
        shifts = []
        
        if not historical:
            return ["首次运行，无历史数据可比较"]
        
        current_topics = set(self.extract_topics(current))
        historical_topics = set(historical.topics)
        
        # 新出现的主题
        new_topics = current_topics - historical_topics
        if new_topics:
            shifts.append(f"新出现的主题: {', '.join(list(new_topics)[:5])}")
        
        # 消失的主题
        disappeared = historical_topics - current_topics
        if disappeared:
            shifts.append(f"消失的主题: {', '.join(list(disappeared)[:5])}")
        
        return shifts
    
    def find_recurring_topics(self, trends: List[TrendItem]) -> List[Tuple[str, int]]:
        """找出重复出现的主题"""
        topics = self.extract_topics(trends)
        topic_counts = Counter(topics)
        return topic_counts.most_common(10)
    
    def find_first_appearances(self, current: List[TrendItem], historical: Optional[HistoricalData]) -> List[str]:
        """找出首次出现的信号"""
        if not historical:
            return [t.title for t in current[:5]]  # 首次运行，返回前5个
        
        current_topics = set(self.extract_topics(current))
        historical_topics = set(historical.topics)
        new_topics = current_topics - historical_topics
        
        # 找到包含新主题的趋势项
        first_appearances = []
        for trend in current:
            trend_topics = set(self.extract_topics([trend]))
            if trend_topics & new_topics:
                first_appearances.append(trend.title)
                if len(first_appearances) >= 5:
                    break
        
        return first_appearances
    
    def calculate_signal_strength(self, trends: List[TrendItem], historical: Optional[HistoricalData]) -> int:
        """计算信号强度 (1-5)"""
        score = 1
        
        # 基于趋势数量
        if len(trends) > 20:
            score += 1
        elif len(trends) > 10:
            score += 0.5
        
        # 基于新主题数量
        if historical:
            current_topics = set(self.extract_topics(trends))
            new_topics = current_topics - set(historical.topics)
            if len(new_topics) > 5:
                score += 1
            elif len(new_topics) > 2:
                score += 0.5
        
        # 基于多源一致性
        sources = set([t.source for t in trends])
        if len(sources) >= 3:
            score += 1
        
        # 基于重复主题
        recurring = self.find_recurring_topics(trends)
        if len([t for t, c in recurring if c >= 3]) > 0:
            score += 1
        
        return min(5, max(1, int(score)))
    
    def load_historical_data(self) -> Optional[HistoricalData]:
        """加载历史数据"""
        # 查找最近的历史文件
        history_files = sorted(self.data_dir.glob("history_*.json"), reverse=True)
        
        if not history_files:
            return None
        
        try:
            with open(history_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                return HistoricalData(**data)
        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
            return None
    
    def save_historical_data(self, trends: List[TrendItem], topics: List[str]):
        """保存历史数据"""
        filename = f"history_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.data_dir / filename
        
        historical = HistoricalData(
            date=datetime.now().isoformat(),
            trends=[asdict(t) for t in trends],
            topics=topics,
            sentiment={}
        )
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(historical), f, ensure_ascii=False, indent=2)
        
        logger.info(f"历史数据已保存到: {filepath}")


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, analysis: AnalysisResult) -> str:
        """生成报告"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("市场脉搏观察报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {analysis.date}")
        report_lines.append("")
        
        # 执行摘要
        report_lines.append("【执行摘要】")
        report_lines.append("-" * 80)
        report_lines.append(f"收集到 {len(analysis.trends)} 条趋势数据")
        report_lines.append(f"检测到 {len(analysis.narrative_shifts)} 个叙事转变")
        report_lines.append(f"识别出 {len(analysis.recurring_topics)} 个重复主题")
        report_lines.append(f"发现 {len(analysis.first_appearances)} 个首次出现信号")
        report_lines.append(f"信号强度评级: {analysis.signal_strength}/5")
        report_lines.append("")
        
        # 叙事转变
        if analysis.narrative_shifts:
            report_lines.append("【叙事转变】")
            report_lines.append("-" * 80)
            for shift in analysis.narrative_shifts:
                report_lines.append(f"• {shift}")
            report_lines.append("")
        
        # 重复主题
        if analysis.recurring_topics:
            report_lines.append("【重复主题（趋势热图）】")
            report_lines.append("-" * 80)
            for topic, count in analysis.recurring_topics:
                bar = "█" * min(count, 10)  # 最多10个字符
                report_lines.append(f"{topic:30s} {bar} ({count})")
            report_lines.append("")
        
        # 首次出现信号
        if analysis.first_appearances:
            report_lines.append("【首次出现信号】")
            report_lines.append("-" * 80)
            for i, signal in enumerate(analysis.first_appearances, 1):
                report_lines.append(f"{i}. {signal}")
            report_lines.append("")
        
        # 详细趋势列表
        report_lines.append("【详细趋势列表】")
        report_lines.append("-" * 80)
        by_source = defaultdict(list)
        for trend in analysis.trends:
            by_source[trend.source].append(trend)
        
        for source, trends in by_source.items():
            report_lines.append(f"\n{source}:")
            for i, trend in enumerate(trends[:10], 1):  # 每个来源最多10条
                report_lines.append(f"  {i}. {trend.title}")
                if trend.url:
                    report_lines.append(f"     链接: {trend.url}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"market_pulse_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        logger.info(f"报告已保存到: {report_file}")
        
        return report_text


def market_pulse_observer(
    schedule: str = "manual",
    sources: Optional[Dict[str, bool]] = None,
    output_path: str = "桌面/market_pulse_reports"
) -> Dict[str, Any]:
    """
    市场脉搏观察者 - 自动收集和分析多个网站的趋势数据
    
    Args:
        schedule: 执行计划 ('manual', 'daily', 'weekly')
        sources: 数据源配置
        output_path: 报告输出路径
    
    Returns:
        执行结果字典
    """
    try:
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "success": False,
                "error": "playwright 未安装。请运行: pip install playwright && playwright install chromium"
            }
        
        # 默认数据源配置
        if sources is None:
            sources = {
                "x_trending": True,
                "financial_news": True,
                "ai_media": False
            }
        
        # 处理 sources 参数：如果是字符串，尝试解析为字典
        if isinstance(sources, str):
            original_source_str = sources  # 保存原始字符串用于日志
            try:
                # 尝试解析 JSON 字符串
                sources = json.loads(sources)
            except (json.JSONDecodeError, ValueError):
                # 如果不是 JSON，尝试作为单个数据源名称处理
                # 例如 "financial_news" -> {"financial_news": True, "x_trending": False, "ai_media": False}
                source_name = original_source_str.lower()
                sources = {
                    "x_trending": source_name == "x_trending",
                    "financial_news": source_name == "financial_news",
                    "ai_media": source_name == "ai_media"
                }
                logger.info(f"将字符串 '{original_source_str}' 转换为数据源配置: {sources}")
        
        # 确保 sources 是字典类型
        if not isinstance(sources, dict):
            return {
                "success": False,
                "error": f"sources 参数必须是字典或字符串，但收到了 {type(sources).__name__}"
            }
        
        # 解析输出路径
        output_dir = resolve_path(output_path)
        data_dir = output_dir / "data"
        
        logger.info(f"开始执行市场脉搏观察，计划: {schedule}")
        logger.info(f"数据源配置: {sources}")
        logger.info(f"输出目录: {output_dir}")
        
        # 收集数据
        all_trends = []
        
        try:
            with BrowserCollector(headless=True) as collector:
                if sources.get("x_trending", True):
                    logger.info("开始收集 X.com 趋势数据...")
                    try:
                        trends = collector.collect_x_trending()
                        all_trends.extend(trends)
                        logger.info(f"✓ X.com 数据收集完成，获得 {len(trends)} 条")
                    except Exception as e:
                        logger.error(f"✗ X.com 数据收集失败: {e}")
                        # 继续收集其他数据源
                
                if sources.get("financial_news", True):
                    logger.info("开始收集金融新闻数据...")
                    try:
                        trends = collector.collect_financial_news()
                        all_trends.extend(trends)
                        logger.info(f"✓ 金融新闻数据收集完成，获得 {len(trends)} 条")
                    except Exception as e:
                        logger.error(f"✗ 金融新闻数据收集失败: {e}")
                        # 继续收集其他数据源
                
                if sources.get("ai_media", False):
                    logger.info("开始收集 AI 媒体数据...")
                    try:
                        trends = collector.collect_ai_media()
                        all_trends.extend(trends)
                        logger.info(f"✓ AI 媒体数据收集完成，获得 {len(trends)} 条")
                    except Exception as e:
                        logger.error(f"✗ AI 媒体数据收集失败: {e}")
                        # 继续收集其他数据源
        except Exception as e:
            logger.error(f"浏览器收集器初始化或执行失败: {e}")
            # 即使浏览器失败，也尝试返回已收集的数据
        
        if not all_trends:
            return {
                "success": False,
                "error": "未能收集到任何趋势数据"
            }
        
        logger.info(f"共收集到 {len(all_trends)} 条趋势数据")
        
        # 分析数据
        analyzer = TrendAnalyzer(data_dir)
        historical = analyzer.load_historical_data()
        
        topics = analyzer.extract_topics(all_trends)
        narrative_shifts = analyzer.detect_narrative_shifts(all_trends, historical)
        recurring_topics = analyzer.find_recurring_topics(all_trends)
        first_appearances = analyzer.find_first_appearances(all_trends, historical)
        signal_strength = analyzer.calculate_signal_strength(all_trends, historical)
        
        # 保存历史数据
        analyzer.save_historical_data(all_trends, topics)
        
        # 生成分析结果
        analysis = AnalysisResult(
            date=datetime.now().isoformat(),
            trends=all_trends,
            narrative_shifts=narrative_shifts,
            recurring_topics=recurring_topics,
            first_appearances=first_appearances,
            sentiment_changes={},
            signal_strength=signal_strength
        )
        
        # 生成报告
        generator = ReportGenerator(output_dir)
        report_text = generator.generate_report(analysis)
        
        return {
            "success": True,
            "message": "市场脉搏观察完成",
            "summary": {
                "total_trends": len(all_trends),
                "narrative_shifts": len(narrative_shifts),
                "recurring_topics": len(recurring_topics),
                "first_appearances": len(first_appearances),
                "signal_strength": signal_strength
            },
            "report": report_text,
            "output_path": str(output_dir)
        }
        
    except ImportError as e:
        return {
            "success": False,
            "error": f"依赖缺失: {str(e)}"
        }
    except Exception as e:
        logger.exception("执行市场脉搏观察失败")
        return {
            "success": False,
            "error": f"执行失败: {str(e)}"
        }


if __name__ == "__main__":
    # 测试
    result = market_pulse_observer(
        schedule="manual",
        sources={"x_trending": True, "financial_news": True, "ai_media": False}
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
