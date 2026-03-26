"""
Policy news scraper — searches the entire web and RSS feeds for latest
climate policy developments, emission reduction strategies, and
environmental regulations relevant to CarbonSense.

Sources:
  1. DuckDuckGo Web Search — broad web search with targeted queries
  2. DuckDuckGo News Search — latest news articles
  3. RSS Feeds — Carbon Brief, Climate Home, UNFCCC, Reuters, Dawn, UNEP
  4. Direct Web Scrape — IEA, World Bank
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search queries — rotated each scrape cycle for broad coverage
# ---------------------------------------------------------------------------

# These queries search the ENTIRE web, not just specific sites
SEARCH_QUERIES = {
    # Pakistan-specific (highest priority)
    'pakistan_climate': [
        'Pakistan carbon emission reduction policy 2024 2025 2026',
        'Pakistan climate change policy latest update',
        'Lahore air quality smog policy new measures',
        'Punjab environmental protection new regulations',
        'Pakistan renewable energy solar wind policy update',
        'Pakistan electric vehicle EV policy latest',
        'Pakistan industrial emissions standards new',
        'Pakistan waste management recycling policy',
        'NEECA Pakistan energy efficiency latest',
        'Pakistan NDC climate targets progress',
        'Lahore transport BRT metro emissions',
        'Pakistan green building code energy',
        'Pakistan carbon credit carbon market',
        'Pakistan climate finance green bonds',
        'NEPRA Pakistan net metering solar regulations',
    ],
    # South Asia regional
    'south_asia': [
        'South Asia climate policy emission reduction latest',
        'India clean air programme NCAP update 2025',
        'India renewable energy transition policy latest',
        'Bangladesh climate change adaptation policy',
        'Asian Development Bank climate South Asia',
    ],
    # Global strategies & best practices
    'global_policy': [
        'carbon emission reduction strategy best practices 2025',
        'net zero policy implementation city level',
        'urban air quality improvement policy successful',
        'industrial decarbonization policy latest',
        'transport sector emission reduction electric vehicles policy',
        'building energy efficiency code new regulations',
        'waste to energy circular economy policy latest',
        'carbon pricing carbon tax latest developments',
        'renewable energy policy developing countries',
        'climate adaptation urban developing cities',
    ],
    # Sector-specific innovations
    'sector_innovations': [
        'emission reduction transport sector new technology policy',
        'industrial emission control new methodology',
        'clean energy transition developing countries latest',
        'methane reduction waste sector new approach',
        'green building standards developing countries',
        'smart city emission monitoring IoT latest',
        'carbon capture utilization storage policy update',
    ],
    # International frameworks
    'international': [
        'UNFCCC COP climate negotiations latest outcome',
        'IPCC latest report climate mitigation update',
        'Paris Agreement global stocktake progress',
        'EU Green Deal carbon border adjustment latest',
        'IEA net zero roadmap update energy',
        'World Bank climate finance developing countries',
    ],
}

# ---------------------------------------------------------------------------
# Relevance keywords (same as before)
# ---------------------------------------------------------------------------

RELEVANCE_KEYWORDS = {
    'high': [
        'carbon emission', 'emission reduction', 'climate policy',
        'net zero', 'net-zero', 'decarbonization', 'decarbonisation',
        'paris agreement', 'nationally determined contribution', 'ndc',
        'carbon tax', 'carbon pricing', 'emissions trading',
        'renewable energy policy', 'clean energy transition',
        'green hydrogen', 'electric vehicle policy',
        'air quality policy', 'pollution control',
        'waste management policy', 'circular economy',
        'building energy code', 'energy efficiency standard',
        'climate finance', 'green bond', 'carbon credit',
        'climate adaptation', 'climate mitigation',
    ],
    'medium': [
        'carbon', 'emission', 'climate', 'greenhouse gas',
        'renewable', 'solar', 'wind energy', 'clean energy',
        'electric vehicle', 'ev policy', 'public transport',
        'air quality', 'smog', 'pollution',
        'waste', 'recycling', 'landfill', 'methane',
        'green building', 'energy efficiency',
        'sustainable development', 'environmental regulation',
        'cop28', 'cop29', 'cop30', 'unfccc', 'ipcc',
    ],
    'pakistan': [
        'pakistan', 'lahore', 'punjab', 'karachi', 'islamabad',
        'sindh', 'khyber', 'balochistan',
        'nepra', 'neeca', 'aedb', 'pcca',
        'pakistan climate', 'pakistan energy', 'pakistan transport',
    ],
}

USER_AGENT = 'CarbonSense/1.0 (Climate Policy Monitor; Research)'

# RSS feed sources
RSS_SOURCES = {
    'carbon_brief': {
        'url': 'https://www.carbonbrief.org/feed/',
        'name': 'Carbon Brief',
    },
    'climate_home': {
        'url': 'https://www.climatechangenews.com/feed/',
        'name': 'Climate Home News',
    },
    'unfccc': {
        'url': 'https://unfccc.int/news/feed',
        'name': 'UNFCCC News',
    },
    'reuters_climate': {
        'url': 'https://www.reuters.com/sustainability/climate-energy/rss',
        'name': 'Reuters Climate & Energy',
    },
    'dawn_climate': {
        'url': 'https://www.dawn.com/feeds/home',
        'name': 'Dawn (Pakistan)',
    },
    'unep': {
        'url': 'https://www.unep.org/news-and-stories/rss.xml',
        'name': 'UNEP News',
    },
}

WEB_SOURCES = {
    'iea': {
        'url': 'https://www.iea.org/news',
        'name': 'IEA News',
        'article_selector': 'a.m-news-listing__link',
        'title_selector': '.m-news-listing__title',
        'base_url': 'https://www.iea.org',
    },
    'world_bank': {
        'url': 'https://www.worldbank.org/en/topic/climatechange/news',
        'name': 'World Bank Climate News',
        'article_selector': 'a.url',
        'title_selector': None,
        'base_url': 'https://www.worldbank.org',
    },
}


class PolicyScraper:
    """Searches the web and scrapes climate policy news from multiple sources."""

    def __init__(self, max_age_days=7):
        self.max_age_days = max_age_days
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def scrape_all(self, existing_urls=None):
        """Search the web + scrape RSS feeds + scrape news sites.

        Args:
            existing_urls: Set of URLs already in the database.

        Returns:
            List of article dicts sorted by relevance score.
        """
        existing_urls = existing_urls or set()
        all_articles = []

        # ---- 1. DuckDuckGo Web & News Search (MAIN SOURCE) ----
        web_articles = self._search_web(existing_urls)
        all_articles.extend(web_articles)
        logger.info(f"[web_search] Found {len(web_articles)} articles from web search")

        # ---- 2. RSS Feeds ----
        for source_key, config in RSS_SOURCES.items():
            try:
                articles = self._scrape_rss(source_key, config, existing_urls)
                all_articles.extend(articles)
                logger.info(f"[{source_key}] Fetched {len(articles)} new articles")
            except Exception as e:
                logger.warning(f"[{source_key}] RSS scrape failed: {e}")
            time.sleep(1)

        # ---- 3. Direct Web Scrape ----
        for source_key, config in WEB_SOURCES.items():
            try:
                articles = self._scrape_web_source(source_key, config, existing_urls)
                all_articles.extend(articles)
                logger.info(f"[{source_key}] Fetched {len(articles)} new articles")
            except Exception as e:
                logger.warning(f"[{source_key}] Web scrape failed: {e}")
            time.sleep(1)

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for article in all_articles:
            if article['url'] not in seen_urls and article['url'] not in existing_urls:
                seen_urls.add(article['url'])
                unique.append(article)

        # Filter by relevance and sort
        relevant = [a for a in unique if a['relevance_score'] >= 0.15]
        relevant.sort(key=lambda x: x['relevance_score'], reverse=True)

        logger.info(
            f"Total scraped: {len(all_articles)}, "
            f"Unique: {len(unique)}, "
            f"Relevant (>= 0.15): {len(relevant)}"
        )

        return relevant

    # -----------------------------------------------------------------------
    # DuckDuckGo Web Search
    # -----------------------------------------------------------------------

    def _search_web(self, existing_urls):
        """Search the entire web using DuckDuckGo for climate policy articles."""
        all_results = []
        total_queries = sum(len(q) for q in SEARCH_QUERIES.values())
        query_num = 0

        for category, queries in SEARCH_QUERIES.items():
            logger.info(f"[ddg] Searching category: {category} ({len(queries)} queries)")
            print(f"  Searching: {category} ({len(queries)} queries)...", flush=True)

            for query in queries:
                query_num += 1
                try:
                    # News search only (faster, more relevant than web search)
                    news_results = self._ddg_news_search(query, existing_urls)
                    all_results.extend(news_results)

                    if news_results:
                        print(f"    [{query_num}/{total_queries}] '{query[:45]}' -> {len(news_results)} articles", flush=True)

                    time.sleep(3)

                except Exception as e:
                    logger.warning(f"[ddg] Search failed for '{query[:50]}': {e}")
                    time.sleep(5)

        # Do web search only for the most important queries (Pakistan-specific)
        print(f"  Deep web search for Pakistan-specific content...", flush=True)
        for query in SEARCH_QUERIES.get('pakistan_climate', [])[:5]:
            try:
                web_results = self._ddg_web_search(query, existing_urls)
                all_results.extend(web_results)
                time.sleep(3)
            except Exception:
                time.sleep(5)

        print(f"  Web search complete: {len(all_results)} total results", flush=True)
        return all_results

    def _ddg_news_search(self, query, existing_urls):
        """Search DuckDuckGo News for recent articles."""
        articles = []
        try:
            results = DDGS().news(
                query,
                max_results=8,
                timelimit='m',  # Last month
            )
            results = list(results) if results else []

            for r in results:
                url = r.get('url', '')
                if not url or url in existing_urls:
                    continue

                title = r.get('title', '').strip()
                body = r.get('body', '').strip()
                source = r.get('source', '')
                date_str = r.get('date', '')

                if not title:
                    continue

                # Use the snippet directly — fetching full articles is too slow
                content = body

                full_text = f"{title} {content}".lower()
                relevance = self._compute_relevance(full_text)

                # Parse date
                pub_date = None
                if date_str:
                    try:
                        pub_date = datetime.fromisoformat(
                            date_str.replace('Z', '+00:00')
                        )
                    except Exception:
                        pub_date = datetime.now(timezone.utc)

                articles.append({
                    'title': title[:1000],
                    'url': url,
                    'source': 'custom_rss',  # General web source
                    'content': content[:10000],
                    'published_date': pub_date or datetime.now(timezone.utc),
                    'country': self._detect_country(full_text),
                    'sectors': self._detect_sectors(full_text),
                    'relevance_score': relevance,
                })

        except Exception as e:
            err = str(e)
            if 'No results' not in err:
                logger.warning(f"[ddg_news] Error: {e}")

        return articles

    def _ddg_web_search(self, query, existing_urls):
        """Search DuckDuckGo Web for policy documents and reports."""
        articles = []
        try:
            results = DDGS().text(
                query,
                max_results=5,
                timelimit='m',  # Last month
            )
            results = list(results) if results else []

            for r in results:
                url = r.get('href', '')
                if not url or url in existing_urls:
                    continue

                # Skip PDFs (can't extract easily) and social media
                if any(skip in url for skip in ['.pdf', 'twitter.com', 'facebook.com',
                                                  'youtube.com', 'instagram.com',
                                                  'linkedin.com']):
                    continue

                title = r.get('title', '').strip()
                body = r.get('body', '').strip()

                if not title:
                    continue

                # Fetch full content
                content = body
                full = self._fetch_article_content(url)
                if full and len(full) > len(content):
                    content = full

                if len(content) < 50:
                    content = body

                full_text = f"{title} {content}".lower()
                relevance = self._compute_relevance(full_text)

                if relevance < 0.1:
                    continue  # Skip low-relevance results

                articles.append({
                    'title': title[:1000],
                    'url': url,
                    'source': 'custom_rss',
                    'content': content[:10000],
                    'published_date': datetime.now(timezone.utc),
                    'country': self._detect_country(full_text),
                    'sectors': self._detect_sectors(full_text),
                    'relevance_score': relevance,
                })

        except Exception as e:
            err = str(e)
            if 'No results' not in err:
                logger.warning(f"[ddg_web] Error: {e}")

        return articles

    # -----------------------------------------------------------------------
    # RSS Feed Scraping
    # -----------------------------------------------------------------------

    def _scrape_rss(self, source_key, config, existing_urls):
        """Scrape articles from an RSS feed."""
        feed = feedparser.parse(config['url'])
        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)

        for entry in feed.entries[:30]:
            url = entry.get('link', '')
            if not url or url in existing_urls:
                continue

            pub_date = self._parse_date(entry)
            if pub_date and pub_date < cutoff:
                continue

            title = entry.get('title', '').strip()
            if not title:
                continue

            content = ''
            if 'content' in entry and entry.content:
                content = entry.content[0].get('value', '')
            elif 'summary' in entry:
                content = entry.get('summary', '')

            content = self._strip_html(content)

            if len(content) < 200:
                full_content = self._fetch_article_content(url)
                if full_content:
                    content = full_content

            if len(content) < 100:
                continue

            full_text = f"{title} {content}".lower()
            relevance = self._compute_relevance(full_text)
            country = self._detect_country(full_text)
            sectors = self._detect_sectors(full_text)

            articles.append({
                'title': title[:1000],
                'url': url,
                'source': source_key,
                'content': content[:10000],
                'published_date': pub_date,
                'country': country,
                'sectors': sectors,
                'relevance_score': relevance,
            })

        return articles

    # -----------------------------------------------------------------------
    # Direct Web Source Scraping
    # -----------------------------------------------------------------------

    def _scrape_web_source(self, source_key, config, existing_urls):
        """Scrape articles from a specific web page."""
        try:
            response = self.session.get(config['url'], timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"[{source_key}] Failed to fetch page: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        links = soup.select(config['article_selector'])[:20]

        for link in links:
            href = link.get('href', '')
            if not href:
                continue

            if href.startswith('/'):
                href = config['base_url'] + href

            if href in existing_urls:
                continue

            title_el = link.select_one(config['title_selector']) if config.get('title_selector') else None
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)

            if not title or len(title) < 10:
                continue

            content = self._fetch_article_content(href)
            if not content or len(content) < 100:
                continue

            full_text = f"{title} {content}".lower()
            relevance = self._compute_relevance(full_text)

            if relevance < 0.1:
                continue

            articles.append({
                'title': title[:1000],
                'url': href,
                'source': source_key,
                'content': content[:10000],
                'published_date': datetime.now(timezone.utc),
                'country': self._detect_country(full_text),
                'sectors': self._detect_sectors(full_text),
                'relevance_score': relevance,
            })

            time.sleep(2)

        return articles

    # -----------------------------------------------------------------------
    # Shared Helpers
    # -----------------------------------------------------------------------

    def _fetch_article_content(self, url):
        """Fetch and extract main content from an article URL."""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
        except Exception:
            return ''

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup.select('nav, footer, aside, .sidebar, .ad, .advertisement, script, style, .cookie, .newsletter, .related'):
            tag.decompose()

        content_selectors = [
            'article', '.article-body', '.post-content', '.entry-content',
            '.article-content', '.story-body', '.article__body',
            'main .content', '[role="main"]', '.field--body',
            '.c-article-body', '#article-body', '.article-text',
        ]

        for selector in content_selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator='\n', strip=True)
                if len(text) > 200:
                    return self._clean_text(text)

        paragraphs = soup.find_all('p')
        text = '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        return self._clean_text(text) if len(text) > 200 else ''

    def _compute_relevance(self, text):
        """Compute a relevance score (0-1) based on keyword matching."""
        score = 0.0

        for keyword in RELEVANCE_KEYWORDS['high']:
            if keyword in text:
                score += 0.3

        for keyword in RELEVANCE_KEYWORDS['medium']:
            if keyword in text:
                score += 0.15

        for keyword in RELEVANCE_KEYWORDS['pakistan']:
            if keyword in text:
                score += 0.25

        return min(1.0, round(score / 3.0, 2))

    def _detect_country(self, text):
        """Detect the primary country mentioned in the text."""
        country_keywords = {
            'Pakistan': ['pakistan', 'lahore', 'karachi', 'islamabad', 'punjab province'],
            'India': ['india', 'delhi', 'mumbai', 'new delhi'],
            'Bangladesh': ['bangladesh', 'dhaka'],
            'China': ['china', 'beijing'],
            'EU': ['european union', 'eu commission', 'brussels'],
            'USA': ['united states', 'us congress', 'washington dc', 'epa '],
            'UAE': ['united arab emirates', 'uae', 'dubai', 'abu dhabi'],
            'Saudi Arabia': ['saudi arabia', 'riyadh'],
        }

        counts = {}
        for country, keywords in country_keywords.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > 0:
                counts[country] = count

        return max(counts, key=counts.get) if counts else 'Global'

    def _detect_sectors(self, text):
        """Detect which CarbonSense sectors the article is about."""
        sector_keywords = {
            'transport': ['transport', 'vehicle', 'traffic', 'brt', 'metro', 'railway',
                          'electric vehicle', 'ev policy', 'fuel economy', 'aviation'],
            'industry': ['industrial', 'factory', 'manufacturing', 'cement', 'steel',
                         'brick kiln', 'textile', 'fertilizer'],
            'energy': ['electricity', 'power plant', 'solar', 'wind', 'renewable',
                       'grid', 'coal phase', 'natural gas', 'nuclear'],
            'waste': ['waste', 'landfill', 'recycling', 'composting', 'methane',
                      'circular economy', 'plastic'],
            'buildings': ['building', 'construction', 'hvac', 'insulation',
                          'green building', 'energy code', 'cooling'],
        }

        detected = []
        for sector, keywords in sector_keywords.items():
            if any(kw in text for kw in keywords):
                detected.append(sector)

        return detected if detected else ['energy']

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse date from RSS feed entry."""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
        return None

    def _strip_html(self, text):
        """Remove HTML tags from text."""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def _clean_text(self, text):
        """Clean up extracted text."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            if len(line) < 20:
                continue
            if line.count('|') > 3 or line.count('•') > 3:
                continue
            cleaned.append(line)
        return '\n'.join(cleaned)
