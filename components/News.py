import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import urllib.parse
import time
import os
import toml

# API key initialization (without using st functions directly)
def load_api_key():
    """Load API key from various locations without using st functions"""
    # Try to load from .streamlit/secrets.toml (recommended)
    try:
        # First try official path
        if os.path.exists('.streamlit/secrets.toml'):
            with open('.streamlit/secrets.toml', 'r') as f:
                return toml.load(f)["api_keys"]["newsapi"]
        # Then try alternate path with absolute directory
        streamlit_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.streamlit')
        if os.path.exists(os.path.join(streamlit_dir, 'secrets.toml')):
            with open(os.path.join(streamlit_dir, 'secrets.toml'), 'r') as f:
                return toml.load(f)["api_keys"]["newsapi"]
        # Fallback to .secrets.toml
        if os.path.exists('.secrets.toml'):
            with open('.secrets.toml', 'r') as f:
                return toml.load(f)["api_keys"]["newsapi"]
    except Exception:
        pass
    return None

# Initialize API key at module level (no st functions)
NEWSAPI_KEY = load_api_key()

def fetch_news_for_stock(symbol, company_name=None):
    """Fetch news articles using NewsAPI with simple session state caching"""
    # Check if API key is available - use st functions here since this runs during app execution
    if not NEWSAPI_KEY:
        # Try to get from Streamlit secrets as a fallback during runtime
        try:
            newsapi_key = st.secrets["api_keys"]["newsapi"]
        except:
            st.error("NewsAPI key not found. News functionality is disabled.")
            return []
    else:
        newsapi_key = NEWSAPI_KEY
    
    # Basic cache key
    cache_key = f"news_cache_{symbol}"
    cache_expiry = 2 * 60 * 60
    current_time = time.time()
    
    # Check session state cache
    if cache_key in st.session_state:
        cached_data = st.session_state[cache_key]
        if current_time - cached_data['timestamp'] < cache_expiry:
            return cached_data['articles']
    
    # If cache missed, fetch fresh data
    all_articles = []
    simple_queries = [symbol, f"{symbol} stock"]
    if company_name:
        simple_queries.append(company_name)
    
    # Try each query
    seen_urls = set()
    for query in simple_queries:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://newsapi.org/v2/everything?q={encoded_query}&apiKey={newsapi_key}&pageSize=10"
            
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                continue
                
            data = response.json()
            if data.get('status') != "ok":
                continue
            
            # Process articles
            for article in data.get("articles", []):
                article_url = article.get('url', '')
                if article_url and article_url not in seen_urls:
                    seen_urls.add(article_url)
                    all_articles.append({
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'url': article_url,
                        'publishedAt': article.get('publishedAt', ''),
                        'source': article.get('source', {}).get('name', 'NewsAPI'),
                        'image': article.get('urlToImage', '')
                    })
            
            if len(all_articles) >= 5:
                break
        except Exception:
            continue
    
    # Update session cache
    st.session_state[cache_key] = {
        'articles': all_articles,
        'timestamp': current_time
    }
    
    return all_articles

def get_company_name_from_symbol(symbol):
    """
    Get company name from symbol using the CSV data
    """
    try:
        # Load both CSV files only once and cache them
        if 'stock_data_cache' not in st.session_state:
            nifty50_data = pd.read_csv('details_50.csv')
            next50_data = pd.read_csv('details_nxt50.csv')
            st.session_state['stock_data_cache'] = pd.concat([nifty50_data, next50_data])
        
        # Look up the company name
        stock_data = st.session_state['stock_data_cache']
        match = stock_data[stock_data['Symbol'] == symbol]
        if not match.empty:
            return match.iloc[0]['Company Name']
    except Exception as e:
        st.error(f"Error retrieving company name: {str(e)}")
    
    return None

def parse_date(date_str):
    """
    Parse date string to datetime object for sorting
    """
    date_formats = [
        "%Y-%m-%dT%H:%M:%SZ",       # Standard ISO format
        "%Y-%m-%dT%H:%M:%S%z",      # ISO with timezone
        "%Y-%m-%dT%H:%M:%S.%fZ",    # ISO with microseconds
        "%a, %d %b %Y %H:%M:%S %Z", # RFC format
        "%Y-%m-%d %H:%M:%S",        # Simple format
        "%Y-%m-%d"                  # Date only
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            continue
    
    # If all formats fail, return current time minus 1 year
    return datetime.now() - timedelta(days=365)

def display_news(symbol):
    """Display latest news for the selected stock"""   
    try:
        css_path = 'assets/news.css'
        if os.path.exists(css_path):
            with open(css_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception:
        pass
    
    st.markdown(f"""
    <div class="news-header">
        <h2>Latest News for {symbol}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if API key is available
    if not NEWSAPI_KEY and 'api_keys' not in st.secrets:
        st.error("NewsAPI key not found. Please configure it in .streamlit/secrets.toml")
        st.markdown("""
        <div class="no-news-container">
            <h3>News feature is disabled</h3>
            <p>API key configuration is missing.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    company_name = get_company_name_from_symbol(symbol)
    news_articles = fetch_news_for_stock(symbol, company_name)
    
    if not news_articles:
        st.markdown(f"""
        <div class="no-news-container">
            <h3>No recent news found for {symbol}</h3>
            <p>Try checking back later for updates.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sort articles by date
    one_year_ago = datetime.now() - timedelta(days=365)
    filtered_articles = []
    
    for article in news_articles:
        try:
            pub_date = parse_date(article.get('publishedAt', ''))
            if pub_date >= one_year_ago:
                filtered_articles.append(article)
        except:
            filtered_articles.append(article)
    
    sorted_articles = sorted(
        filtered_articles,
        key=lambda x: parse_date(x.get('publishedAt', '')),
        reverse=True
    )
    
    # Display news count
    st.markdown(f"""<div class="news-count">Showing {len(sorted_articles)} news articles</div>""", unsafe_allow_html=True)
    
    # Display news articles
    st.markdown('<div class="news-container">', unsafe_allow_html=True)
    
    for article in sorted_articles:
        # Format date
        try:
            published_date = parse_date(article.get('publishedAt', ''))
            date_display = published_date.strftime("%d %b %Y")
            
            days_ago = (datetime.now() - published_date).days
            if days_ago == 0:
                time_ago = "Today"
            elif days_ago == 1:
                time_ago = "Yesterday"
            else:
                time_ago = f"{days_ago} days ago"
                
            date_display = f"{date_display} ({time_ago})"
        except:
            date_display = "Unknown date"
        
        # Image handling
        image_url = article.get('image', '')
        if not image_url:
            image_url = "https://via.placeholder.com/120x120/2a2a3d/c8d8f7?text=No+Image"
            
        # Create news card
        st.markdown(
            f"""
            <div class="news-card">
                <div class="news-img-container">
                    <img src="{image_url}" class="news-img" alt="News image" onerror="this.onerror=null;this.src='https://via.placeholder.com/120x120/2a2a3d/c8d8f7?text=No+Image';">
                </div>
                <div class="news-content">
                    <h3 class="news-title">{article.get('title', 'No title')}</h3>
                    <div class="news-meta">
                        <span class="news-badge">{article.get('source', 'Unknown')}</span>
                        <span class="news-date">{date_display}</span>
                    </div>
                    <p class="news-description">{article.get('description', 'No description available')}</p>
                    <a href="{article.get('url', '#')}" target="_blank" class="news-read-more">Read Full Article</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""<div class="news-footer">News data powered by NewsAPI</div>""", unsafe_allow_html=True)