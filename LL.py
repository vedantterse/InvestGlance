import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, time as datetime_time
import pytz
import ta

##########################################################################################
## PART 1: Define Functions for Pulling, Processing, and Creating Techincial Indicators ##
##########################################################################################

def is_market_open():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    # NSE market hours: 9:15 AM - 3:30 PM IST, Monday to Friday
    market_start = datetime_time(9, 15)
    market_end = datetime_time(15, 30)
    return (now.time() >= market_start and 
            now.time() <= market_end and 
            now.weekday() < 5)

# Fetch stock data based on the ticker, period, and interval
def fetch_stock_data(ticker, period, interval):
    try:
        # Format NSE symbol
        ticker = f"{ticker}.NS"
        
        # Simple date range calculation for reliable data
        end_date = datetime.now()
        if period == '1d':
            start_date = end_date - timedelta(days=1)
        elif period == '1wk':
            start_date = end_date - timedelta(days=7)
        elif period == '1mo':
            start_date = end_date - timedelta(days=30)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # max
            start_date = end_date - timedelta(days=365*5)
            
        # Fetch data with basic parameters
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval=interval
        )
        
        if len(data) < 1:
            st.warning(f"No data available for {ticker}")
            return pd.DataFrame()
            
        return data
        
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return pd.DataFrame()

# Process data to ensure it is timezone-aware and has the correct format
def process_data(data):
    try:
        if data.empty:
            return data
            
        # Handle multi-index columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # Convert to IST timezone
        if data.index.tzinfo is None:
            data.index = data.index.tz_localize('UTC')
        data.index = data.index.tz_convert('Asia/Kolkata')
        
        data.reset_index(inplace=True)
        data.rename(columns={'index': 'Datetime', 'Date': 'Datetime'}, inplace=True)
        return data
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return pd.DataFrame()

# Calculate basic metrics from the stock data
def calculate_metrics(data):
    try:
        # Convert to float to ensure proper formatting
        last_close = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[0])
        change = float(last_close - prev_close)
        pct_change = float((change / prev_close) * 100)
        high = float(data['High'].max())
        low = float(data['Low'].min())
        volume = int(data['Volume'].sum())
        return last_close, change, pct_change, high, low, volume
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0

# Add simple moving average (SMA) and exponential moving average (EMA) indicators
def add_technical_indicators(data):
    try:
        # Ensure Close price is a 1D series
        close_prices = data['Close'].squeeze()
        
        # Calculate indicators
        data['SMA_20'] = ta.trend.sma_indicator(close_prices, window=20)
        data['EMA_20'] = ta.trend.ema_indicator(close_prices, window=20)
        
        return data
    except Exception as e:
        st.error(f"Error calculating technical indicators: {str(e)}")
        return data

###############################################
## PART 2: Creating the Dashboard App layout ##
###############################################


# Set up Streamlit page layout
st.set_page_config(layout="wide")
st.title('Real Time Stock Dashboard')


# 2A: SIDEBAR PARAMETERS ############

# Sidebar for user input parameters
st.sidebar.header('Chart Parameters')
# Add dropdown for popular Indian stocks
nifty_stocks = {
    'TATASTEEL': 'Tata Steel',
    'RELIANCE': 'Reliance Industries',
    'HDFCBANK': 'HDFC Bank',
    'TCS': 'Tata Consultancy Services',
    'INFY': 'Infosys',
    'WIPRO': 'Wipro',
    'SBIN': 'State Bank of India',
    'ICICIBANK': 'ICICI Bank',
    'AXISBANK': 'Axis Bank',
    'LT': 'Larsen & Toubro'  # Updated symbol for L&T
}

ticker = st.sidebar.selectbox('Select Stock', 
                            options=list(nifty_stocks.keys()),
                            format_func=lambda x: f"{x} - {nifty_stocks[x]}")
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20'])

# Mapping of time periods to data intervals
interval_mapping = {
    '1d': '15m',   # 15-minute intervals for intraday
    '1wk': '60m',  # Hourly for week
    '1mo': '1d',   # Daily for month
    '1y': '1d',    # Daily for year
    'max': '1wk'   # Weekly for max period
}


# 2B: MAIN CONTENT AREA ############

# Update the dashboard based on user input
if st.sidebar.button('Update'):
    with st.spinner('Fetching data...'):
        data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
        if not data.empty and len(data) > 1:
            data = process_data(data)
            data = add_technical_indicators(data)
            
            last_close, change, pct_change, high, low, volume = calculate_metrics(data)
            
            # Display metrics with INR formatting
            try:
                st.metric(
                    label=f"{ticker} Last Price", 
                    value=f"₹{last_close:,.2f}", 
                    delta=f"₹{change:+,.2f} ({pct_change:+.2f}%)"
                )
                
                col1, col2, col3 = st.columns(3)
                col1.metric("High", f"₹{high:,.2f}")
                col2.metric("Low", f"₹{low:,.2f}")
                col3.metric("Volume", f"{volume:,}")
                
                # Plot the stock price chart
                fig = go.Figure()
                
                # Add price data
                if chart_type == 'Candlestick':
                    fig.add_trace(
                        go.Candlestick(
                            x=data['Datetime'],
                            open=data['Open'],
                            high=data['High'],
                            low=data['Low'],
                            close=data['Close'],
                            name='Price'
                        )
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=data['Datetime'],
                            y=data['Close'],
                            name='Price',
                            line=dict(color='green', width=2)
                        )
                    )
                
                # Add technical indicators
                if 'SMA 20' in indicators:
                    fig.add_trace(
                        go.Scatter(
                            x=data['Datetime'],
                            y=data['SMA_20'],
                            name='SMA 20',
                            line=dict(color='orange', width=1.5)
                        )
                    )
                if 'EMA 20' in indicators:
                    fig.add_trace(
                        go.Scatter(
                            x=data['Datetime'],
                            y=data['EMA_20'],
                            name='EMA 20',
                            line=dict(color='blue', width=1.5)
                        )
                    )

                # Enhanced layout
                fig.update_layout(
                    title=f'{nifty_stocks.get(ticker, ticker)} Stock Price',
                    yaxis_title='Price (INR)',
                    xaxis_title='Date',
                    template='plotly_dark',
                    xaxis_rangeslider_visible=False,  # Disable rangeslider for cleaner look
                    height=600,  # Larger chart
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        bgcolor='rgba(0,0,0,0.5)'
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
                
                # Add additional Indian market context
                st.sidebar.markdown("---")
                st.sidebar.markdown("### Market Information")
                st.sidebar.markdown(f"**Company:** {nifty_stocks.get(ticker, ticker)}")
                st.sidebar.markdown("**Exchange:** NSE")
                st.sidebar.markdown("**Currency:** INR (₹)")
                
            except Exception as e:
                st.error(f"Error displaying metrics: {str(e)}")
                st.error("Debug info:")
                st.write("Data columns:", data.columns.tolist())
        else:
            st.error(f"Unable to fetch data for {ticker}. Please try another stock or time period.")
