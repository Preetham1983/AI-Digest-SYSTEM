from typing import List

# RSS Feeds Configuration
DEFAULT_RSS_FEEDS = [
    # High Frequency News
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/artificial-intelligence/index.xml",
    "https://www.wired.com/feed/category/ai/latest/rss",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    
    # Official Research Blogs (Lower Frequency, High Relevance)
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/index.xml", 
    "https://deepmind.google/blog/rss.xml",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
]


# Reddit Subreddits to track (via RSS)
# These are high-signal communities for AI and Tech
DEFAULT_SUBREDDITS = [
    "https://www.reddit.com/r/MachineLearning/.rss",
    "https://www.reddit.com/r/LocalLLaMA/.rss",
]
