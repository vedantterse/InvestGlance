# filepath: c:\Users\Acer\Desktop\INVEST GLANCE\components\forecast.py
import streamlit as st
import pandas as pd
import yfinance as yf
import time

def display_comparison(symbol):
    """
    Display stock comparison with peers in the same industry
    """
    # Load external CSS file for comparison styling
    with open('assets/comparison.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
    # More professional, short and modern heading
    st.markdown(f"""
        <div class="comparison-header">
            <h2>{symbol} <span class="comparison-subtitle">Peer Analysis</span></h2>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        # Load both stock lists
        nifty50_data = pd.read_csv('details_50.csv')
        next50_data = pd.read_csv('details_nxt50.csv')
        
        # Combine both dataframes for searching
        all_stocks = pd.concat([nifty50_data, next50_data]).reset_index(drop=True)
        
        # Find the selected stock information
        selected_stock_info = all_stocks[all_stocks['Symbol'] == symbol]
        
        if selected_stock_info.empty:
            st.error(f"Stock {symbol} not found in the database.")
            return
            
        # Get industry of the selected stock
        stock_industry = selected_stock_info.iloc[0]['Industry']
        
        # Find all peers in the same industry
        peers = all_stocks[all_stocks['Industry'] == stock_industry].reset_index(drop=True)
        
        if len(peers) <= 1:  # Just the stock itself
            st.info(f"No other peer stocks found in the {stock_industry} industry.")
            return
            
        # Get price data for all peers
        with st.spinner("Fetching current prices for peer comparison..."):
            peer_prices = get_peer_prices(peers['Symbol'].tolist())
            
        # Add the "Selected" flag to the peers dataframe
        peers['Is_Selected'] = peers['Symbol'] == symbol
        
        # Reorder so selected stock is at the top
        peers = pd.concat([
            peers[peers['Symbol'] == symbol],
            peers[peers['Symbol'] != symbol]
        ]).reset_index(drop=True)
            
        # Display peers in a new tube-like layout
        display_peer_comparison_tubes(peers, peer_prices)
        
    except Exception as e:
        st.error(f"Error loading comparison data: {str(e)}")

def get_peer_prices(symbols):
    """Get current prices for all peer stocks"""
    price_data = {}
    
    for symbol in symbols:
        try:
            # Create ticker symbol with NS suffix for NSE
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Get 5 days of data to calculate trend
            hist = ticker.history(period="5d")
            
            if (hist.empty):
                price_data[symbol] = {
                    "price": "N/A",
                    "trend": "neutral",
                    "percent_change": 0.0
                }
                continue
                
            # Get latest closing price
            latest_price = hist['Close'].iloc[-1]
            
            # Calculate trend
            if len(hist) >= 4:  # Need at least 4 days for 3-day average
                three_day_avg = hist['Close'].iloc[-4:-1].mean()
            elif len(hist) >= 2:
                three_day_avg = hist['Close'].iloc[:-1].mean()
            else:
                three_day_avg = latest_price
                
            if latest_price > three_day_avg:
                trend = "up"
            elif latest_price < three_day_avg:
                trend = "down"
            else:
                trend = "neutral"
                
            # Calculate percent change (safely)
            percent_change = 0.0
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                if prev_close > 0:  # Prevent division by zero
                    percent_change = ((latest_price - prev_close) / prev_close) * 100
            
            price_data[symbol] = {
                "price": latest_price,
                "trend": trend,
                "percent_change": percent_change
            }
            
        except Exception as e:
            # Provide default values when an error occurs
            price_data[symbol] = {
                "price": "N/A",
                "trend": "neutral",
                "percent_change": 0.0
            }
    
    return price_data

def display_peer_comparison_tubes(peers, price_data):
    """Display peer comparison in horizontal tube-like layout"""
    
    # Add industry header with unique amber/gold color scheme
    st.markdown(f"""
        <div class="comparison-wrapper">
            <div class="industry-header">
                <h3 class="industry-title">{peers.iloc[0]['Industry']}</h3>
            </div>
    """, unsafe_allow_html=True)
    
    # Create tubes for each peer
    for i, (_, peer) in enumerate(peers.iterrows()):
        symbol = peer['Symbol']
        price_info = price_data.get(symbol, {})
        
        # Safely get values with defaults
        price = price_info.get('price', 'N/A')
        trend = price_info.get('trend', 'neutral')
        percent_change = price_info.get('percent_change', 0.0)
        
        # Format price display
        if isinstance(price, (int, float)):
            price_display = f"₹{price:,.2f}"
            percent_display = f"{percent_change:.2f}%"
        else:
            price_display = "Not Available"
            percent_display = "--"
        
        # Set trend class and indicator
        trend_class = f"price-trend-{trend}"
        if trend == 'up' and isinstance(price, (int, float)):
            percent_display = f"▲ {percent_display}"
        elif trend == 'down' and isinstance(price, (int, float)):
            percent_display = f"▼ {percent_display}"
        
        # Set selected class
        selected_class = " selected" if peer['Is_Selected'] else ""
        
        # Create a proper HTML link that works as a button for reliable redirection
        # target="_self" ensures it happens in the same tab
        st.markdown(f"""
        <a href="/?stock={symbol}&tab=charts" target="_self" class="peer-tube-container" style="text-decoration: none; cursor: pointer; display: block;">
            <div class="peer-tube{selected_class}">
                <div class="peer-index">{i+1}</div>
                <div class="peer-name-container">
                    <div class="peer-name">{peer['Company Name']}</div>
                    <div class="peer-symbol">{symbol}</div>
                </div>
                <div class="price-info">
                    <div class="peer-price {trend_class}">{price_display}</div>
                    <div class="peer-change {trend_class}">{percent_display}</div>
                </div>
            </div>
        </a>
        """, unsafe_allow_html=True)
    
    # Close wrapper
    st.markdown('</div>', unsafe_allow_html=True)
