import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import urllib.parse
import time
import os

# API key for NewsAPI
NEWSAPI_KEY = "0c407fb8c127459da2f04a5682190681"

def fetch_news_for_stock(symbol, company_name=None):
    """
    Fetch news articles using NewsAPI with simple session state caching
    """
    # Basic cache key
    cache_key = f"news_cache_{symbol}"
    
    # Simple cache expiry - 2 hours for all stocks
    cache_expiry = 2 * 60 * 60
    current_time = time.time()
    
    # Check session state cache
    if cache_key in st.session_state:
        cached_data = st.session_state[cache_key]
        if current_time - cached_data['timestamp'] < cache_expiry:
            return cached_data['articles']
    
    # If cache missed, fetch fresh data
    all_articles = []
    
    # Basic search queries
    simple_queries = [
        symbol,
        f"{symbol} stock"
    ]
    
    # Add company name if available
    if company_name:
        simple_queries.append(company_name)
    
    # Try each query
    seen_urls = set()
    for query in simple_queries:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://newsapi.org/v2/everything?q={encoded_query}&apiKey={NEWSAPI_KEY}&pageSize=10"
            
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            
            response = requests.get(url, headers=headers)
            
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
            
            # If we found enough articles, don't try more queries
            if len(all_articles) >= 5:
                break
                
        except Exception:
            # Silently continue on errors
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
    """
    Display latest news for the selected stock in a visually appealing format
    """    
    try:
        # Load external CSS for news styling
        css_path = 'assets/news.css'
        if os.path.exists(css_path):
            with open(css_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception:
        pass  # CSS failing shouldn't block the news display
    
    # Display news header
    st.markdown(f"""
    <div class="news-header">
        <h2>Latest News for {symbol}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Get company name for better search results
    company_name = get_company_name_from_symbol(symbol)
    
    # Fetch news articles with simple caching
    news_articles = fetch_news_for_stock(symbol, company_name)
    
    if not news_articles:
        st.markdown(f"""
        <div class="no-news-container">
            <h3>No recent news found for {symbol}</h3>
            <p>Try checking back later for updates.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sort articles by date (descending order - newest first)
    one_year_ago = datetime.now() - timedelta(days=365)
    
    filtered_articles = []
    for article in news_articles:
        try:
            pub_date = parse_date(article.get('publishedAt', ''))
            # Wide date range filter
            if pub_date >= one_year_ago:
                filtered_articles.append(article)
        except:
            # Include articles with unparseable dates
            filtered_articles.append(article)
    
    sorted_articles = sorted(
        filtered_articles,
        key=lambda x: parse_date(x.get('publishedAt', '')),
        reverse=True
    )
    
    # Display summary of news sources
    st.markdown(f"""<div class="news-count">Showing {len(sorted_articles)} news articles for {symbol}</div>""", unsafe_allow_html=True)
    
    # Display news articles in modern, compact cards with smaller images
    st.markdown('<div class="news-container">', unsafe_allow_html=True)
    for article in sorted_articles:
        # Format the date for display
        try:
            published_date = parse_date(article.get('publishedAt', ''))
            date_display = published_date.strftime("%d %b %Y")
            
            # Calculate days ago for better context
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
        
        # Image handling with placeholder for missing images - FIXED INDENTATION HERE
        image_url = article.get('image', '')
        if not image_url:
            image_url = "https://via.placeholder.com/120x120/2a2a3d/c8d8f7?text=No+Image"
            
        # Create a compact news card with smaller image
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

    # Show a note about the data sources with dark theme footer
    st.markdown("""
    <div class="news-footer">
        News data powered by <a href="https://newsapi.org/" target="_blank">NewsAPI</a>
    </div>
    """, unsafe_allow_html=True)