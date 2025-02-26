# filepath: c:\Users\Acer\Desktop\INVEST GLANCE\components\news.py
import streamlit as st

def display_news(symbol):
    """
    Display latest news for the selected stock
    """
    st.markdown(f"<h2>Latest News for {symbol}</h2>", unsafe_allow_html=True)
    st.info("Latest market news and updates coming soon! 📰")
    
    # Placeholder content
    st.markdown("""
        ## Coming Soon
        - Company News
        - Recent Press Releases
        - Market Analysis
        - Sector Updates
        - Social Media Sentiment
    """)