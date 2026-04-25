"""
AI News Daily — 設定ファイル
ニュース収集パイプライン全体の定数・API設定・ソース定義
"""

import os

# === API Keys ===
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# === 出力設定 ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
REPORTS_JSON = os.path.join(DATA_DIR, "reports.json")

# === 収集設定 ===
MAX_ARTICLES_PER_SOURCE = 10
MAX_FINAL_ARTICLES = 20
FETCH_TIMEOUT = 15  # seconds
LOOKBACK_HOURS = 48  # 直近48時間のニュースを収集

# === AIキーワードフィルタ（一般テック媒体からAI記事を絞り込む） ===
AI_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "large language model", "GPT", "Claude", "Gemini", "Llama",
    "neural network", "transformer", "diffusion", "generative",
    "OpenAI", "Anthropic", "DeepMind", "Mistral", "Hugging Face",
    "agent", "autonomous", "MCP", "tool use",
    "人工知能", "機械学習", "深層学習", "生成AI", "大規模言語モデル",
    "エージェント", "自律", "チャットボット",
]

# === カテゴリ定義（サイトのCSSクラスと対応） ===
CATEGORIES = {
    "model_research": {
        "label": "モデル・研究",
        "tag_class": "tag-model",
        "keywords": ["model", "benchmark", "paper", "research", "training", "fine-tune",
                      "parameter", "token", "context window", "モデル", "論文", "ベンチマーク"],
    },
    "agent_ai": {
        "label": "エージェントAI",
        "tag_class": "tag-agent",
        "keywords": ["agent", "autonomous", "tool use", "MCP", "function calling",
                      "workflow", "automation", "エージェント", "自律", "自動化"],
    },
    "business": {
        "label": "ビジネス",
        "tag_class": "tag-biz",
        "keywords": ["funding", "revenue", "enterprise", "partnership", "acquisition",
                      "IPO", "valuation", "billion", "資金調達", "買収", "提携", "売上"],
    },
    "security": {
        "label": "セキュリティ",
        "tag_class": "tag-sec",
        "keywords": ["security", "safety", "regulation", "policy", "ban", "lawsuit",
                      "leak", "vulnerability", "compliance", "セキュリティ", "規制", "安全性"],
    },
    "startup": {
        "label": "スタートアップ",
        "tag_class": "tag-startup",
        "keywords": ["startup", "launch", "seed", "series A", "Y Combinator",
                      "founding", "スタートアップ", "新興", "ローンチ"],
    },
}

# === RSSフィード定義 ===
# tier: 1=通信社/最重要, 2=大手テックメディア, 3=企業ブログ, 4=日本語メディア, 5=アグリゲータ
RSS_FEEDS = [
    # --- Tier 1: 通信社 ---
    {"name": "Reuters Technology", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best", "tier": 1, "lang": "en", "ai_filter": True},

    # --- Tier 2: 大手テックメディア ---
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "tier": 2, "lang": "en", "ai_filter": False},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "tier": 2, "lang": "en", "ai_filter": False},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "tier": 2, "lang": "en", "ai_filter": False},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "tier": 2, "lang": "en", "ai_filter": True},
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "tier": 2, "lang": "en", "ai_filter": False},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "tier": 2, "lang": "en", "ai_filter": True},

    # --- Tier 3: 企業ブログ ---
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/rss.xml", "tier": 3, "lang": "en", "ai_filter": False},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "tier": 3, "lang": "en", "ai_filter": False},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "tier": 3, "lang": "en", "ai_filter": False},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "tier": 3, "lang": "en", "ai_filter": False},
    {"name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/feed/", "tier": 3, "lang": "en", "ai_filter": False},
    {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/feed/", "tier": 3, "lang": "en", "ai_filter": True},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "tier": 3, "lang": "en", "ai_filter": False},

    # --- Tier 4: 日本語メディア ---
    {"name": "ITmedia AI+", "url": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml", "tier": 4, "lang": "ja", "ai_filter": False},
    {"name": "Impress Watch", "url": "https://www.watch.impress.co.jp/data/rss/1.0/ipw/feed.rdf", "tier": 4, "lang": "ja", "ai_filter": True},
    {"name": "ledge.ai", "url": "https://ledge.ai/feed", "tier": 4, "lang": "ja", "ai_filter": False},
]

# === ソースティアの重み（ランキング用） ===
TIER_WEIGHTS = {
    1: 2.0,   # 通信社
    2: 1.5,   # 大手テックメディア
    3: 1.0,   # 企業ブログ
    4: 1.0,   # 日本語メディア
    5: 0.5,   # アグリゲータ
}
