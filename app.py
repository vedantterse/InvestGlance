import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_extras.app_logo import add_logo
import streamlit.components.v1 as components
import yfinance as yf
import time
from datetime import datetime, timedelta

# Read the CSV files
nifty50_data = pd.read_csv('details_50.csv')
next50_data = pd.read_csv('details_nxt50.csv')

# Initialize session states
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None
if 'selected_market' not in st.session_state:
    st.session_state.selected_market = "NIFTY50"
if 'selected_tab' not in st.session_state:  # Add this initialization
    st.session_state.selected_tab = "Charts"
# Add price cache to session state
if 'price_cache' not in st.session_state:
    st.session_state.price_cache = {}
# Add previous stock tracking to detect changes
if 'previous_stock' not in st.session_state:
    st.session_state.previous_stock = None

# Function to get stock price with caching and trend calculation
def get_stock_price_with_trend(symbol):
    current_time = time.time()
    cache_expiry = 60 * 60  # Cache for 1 hour to save API calls
    
    # Check cache first
    if symbol in st.session_state.price_cache:
        cached_data = st.session_state.price_cache[symbol]
        if (current_time - cached_data['timestamp']) < cache_expiry:
            return cached_data
    
    try:
        # Use yfinance to get 5 days of data (to ensure we have at least 3 trading days)
        ticker_symbol = f"{symbol}.NS"
        ticker_data = yf.Ticker(ticker_symbol)
        hist = ticker_data.history(period="5d")
        
        if (hist.empty):
            return {
                'price': "N/A",
                'trend': "neutral",
                'timestamp': current_time
            }
        
        # Get the latest closing price (most recent day)
        latest_price = hist['Close'].iloc[-1]
        
        # Calculate 3-day average (excluding the latest day)
        if len(hist) >= 4:  # We need at least 4 days to have 3 previous days
            three_day_avg = hist['Close'].iloc[-4:-1].mean()  # Last 3 days excluding today
        elif len(hist) >= 2:  # If we have at least 2 days
            three_day_avg = hist['Close'].iloc[:-1].mean()  # All previous days excluding today
        else:
            three_day_avg = latest_price  # Fallback if we only have today
        
        # Determine trend
        if latest_price > three_day_avg:
            trend = "up"
        elif latest_price < three_day_avg:
            trend = "down"
        else:
            trend = "neutral"
        
        # Cache the result
        result = {
            'price': latest_price,
            'trend': trend,
            'timestamp': current_time
        }
        st.session_state.price_cache[symbol] = result
        
        return result
        
    except Exception as e:
        # In case of error, return N/A
        return {
            'price': "N/A",
            'trend': "neutral",
            'timestamp': current_time
        }

# Configure the page to use full width and remove padding
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# Load external CSS
with open('assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

with open('assets/dashboard.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Add JavaScript for button styling
st.markdown("""
<script>
    // Use mutation observer to apply styles to buttons after they're rendered
    const observer = new MutationObserver(() => {
        const buttons = document.querySelectorAll('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"]');
        buttons.forEach(button => {
            button.classList.add('compact-tab-button');
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Also apply immediately in case elements already exist
    const buttons = document.querySelectorAll('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"]');
    buttons.forEach(button => {
        button.classList.add('compact-tab-button');
    });
</script>
""", unsafe_allow_html=True)

# Sidebar header
st.sidebar.markdown("<h1 style='font-family: Poppins, sans-serif; font-weight: 600; font-size: 24px; margin-bottom: 20px;'>Stock Markets</h1>", unsafe_allow_html=True)

# Market selector buttons
col1, col2 = st.sidebar.columns([1, 1])
nifty50_selected = st.session_state.selected_market == "NIFTY50"
next50_selected = st.session_state.selected_market == "NEXT50"

if col1.button("NIFTY50", type="secondary" if nifty50_selected else "primary", key="nifty50_btn"):
    st.session_state.selected_market = "NIFTY50"
    # Set default stock to first stock in NIFTY50
    new_stock = nifty50_data.iloc[0]['Symbol'] if not nifty50_data.empty else None
    # If stock changes, reset tab to Charts
    if st.session_state.selected_stock != new_stock:
        st.session_state.selected_tab = "Charts"
    st.session_state.selected_stock = new_stock
    st.rerun()

if col2.button("NEXT50", type="secondary" if next50_selected else "primary", key="next50_btn"):
    st.session_state.selected_market = "NEXT50"
    # Set default stock to first stock in NEXT50
    new_stock = next50_data.iloc[0]['Symbol'] if not next50_data.empty else None
    # If stock changes, reset tab to Charts
    if st.session_state.selected_stock != new_stock:
        st.session_state.selected_tab = "Charts"
    st.session_state.selected_stock = new_stock
    st.rerun()

# Add spacing after buttons
st.sidebar.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# Search functionality
search_query = st.sidebar.text_input("Search", value="", placeholder="🔍 Search stocks...", label_visibility="collapsed")

def create_stock_card(container, row, symbol):
    # Add is_selected flag to identify the currently selected stock
    is_selected = st.session_state.selected_stock == symbol
    button_type = "secondary" if is_selected else "primary"
    
    # Use a simpler approach with clean text formatting
    if container.button(
        f"{row['Company Name']}\n📈 {symbol} | 🏢 {row['Industry']}",
        key=f"stock_{symbol}",
        use_container_width=True,
        type=button_type  # Use secondary type for selected stock
    ):
        # If selecting a different stock, reset tab to Charts
        if st.session_state.selected_stock != symbol:
            st.session_state.selected_tab = "Charts"
        st.session_state.selected_stock = symbol
        st.rerun()

def display_stocks(data, search_query):
    filtered_data = data
    
    if search_query:
        # Convert search query to lowercase and strip spaces
        search_query = search_query.lower().strip()
        
        # Search in Company Name, Symbol and Industry
        mask = (
            data['Company Name'].str.lower().str.contains(search_query, na=False) |
            data['Symbol'].str.lower().str.contains(search_query, na=False) |
            data['Industry'].str.lower().str.contains(search_query, na=False)
        )
        filtered_data = data[mask].copy()
    
    if len(filtered_data) == 0:
        st.sidebar.markdown('<div class="no-results-message">No stocks found matching your search criteria.</div>', unsafe_allow_html=True)
        return
    
    # Display each matching stock
    for _, row in filtered_data.iterrows():
        symbol = row['Symbol']
        create_stock_card(st.sidebar, row, symbol)

# Display stocks in sidebar
current_data = nifty50_data if st.session_state.selected_market == "NIFTY50" else next50_data
current_market_name = "NIFTY 50" if st.session_state.selected_market == "NIFTY50" else "NIFTY NEXT 50"
st.sidebar.markdown(f"<h3>{current_market_name} Stocks</h3>", unsafe_allow_html=True)
display_stocks(current_data, search_query)

# Make sure selected stock is in the current market
if st.session_state.selected_stock:
    # Check if selected stock exists in current market data
    if st.session_state.selected_stock not in current_data['Symbol'].values:
        # If not, select the first stock in the current market
        st.session_state.selected_stock = current_data.iloc[0]['Symbol'] if not current_data.empty else None

# Set default selected stock if none is selected
if st.session_state.selected_stock is None and not current_data.empty:
    st.session_state.selected_stock = current_data.iloc[0]['Symbol']

# Before displaying the dashboard, check if stock has changed
# This handles direct URL access or session resumption cases
if st.session_state.selected_stock and st.session_state.previous_stock != st.session_state.selected_stock:
    # If the stock has changed since last render, reset the tab
    if st.session_state.previous_stock is not None:
        st.session_state.selected_tab = "Charts"
    # Update the previous stock
    st.session_state.previous_stock = st.session_state.selected_stock

# Add dashboard display with improved badges and direct tab buttons
selected_stock = st.session_state.get('selected_stock')
if selected_stock:
    try:
        stock_data = current_data[current_data['Symbol'] == selected_stock]
        
        if stock_data.empty:
            st.error(f"Stock data for {selected_stock} not found.")
            st.session_state.selected_stock = current_data.iloc[0]['Symbol']
            st.rerun()
        else:
            stock_info = stock_data.iloc[0]
            
            # Fetch price data only once when stock is selected, with 1-hour cache
            price_data = get_stock_price_with_trend(selected_stock)
            
            # Format price display based on data
            if isinstance(price_data['price'], (int, float)):
                price_display = f"₹{price_data['price']:,.2f}"
                trend_class = f"trend-{price_data['trend']}"
            else:
                price_display = "Not Available"
                trend_class = "trend-neutral"
            
            # Enhanced header with modern styling, badges, and price display
            st.markdown(f"""
                <div class="modern-dashboard-header">
                    <div class="badge-container">
                        <div class="stock-badge purple-glow">
                            <div class="badge-content">
                                <span class="badge-value">{selected_stock}</span>
                            </div>
                        </div>
                        <div class="stock-badge cyan-glow">
                            <div class="badge-content">
                                <span class="badge-value">{stock_info['Industry']}</span>
                            </div>
                        </div>
                    </div>
                    <h1 class="gradient-header">{stock_info['Company Name']}</h1>
                    <div class="price-display {trend_class}">
                        <span class="price-label">Current Price</span>
                        {price_display}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Tab buttons without the container - directly using columns
            col1, col2, col3, col4 = st.columns(4)
            
            # Define tab data with icons
            tab_data = {
                "Charts": "📈",
                "Reports": "📊", 
                "Forecast": "🔮",
                "News": "📰"
            }
            
            # Apply custom CSS to make columns more compact
            for i, col in enumerate([col1, col2, col3, col4]):
                col.markdown('<div class="tab-button-container"></div>', unsafe_allow_html=True)
            
            # Create the tab buttons with icons inline with text
            with col1:
                if st.button(f"{tab_data['Charts']} Charts", key="tab_Charts", 
                           type="secondary" if st.session_state.selected_tab == "Charts" else "primary",
                           use_container_width=True):
                    st.session_state.selected_tab = "Charts"
                    st.rerun()
                    
            with col2:
                if st.button(f"{tab_data['Reports']} Reports", key="tab_Reports",
                           type="secondary" if st.session_state.selected_tab == "Reports" else "primary",
                           use_container_width=True):
                    st.session_state.selected_tab = "Reports"
                    st.rerun()
                    
            with col3:
                if st.button(f"{tab_data['Forecast']} Forecast", key="tab_Forecast",
                           type="secondary" if st.session_state.selected_tab == "Forecast" else "primary",
                           use_container_width=True):
                    st.session_state.selected_tab = "Forecast"
                    st.rerun()
                    
            with col4:
                if st.button(f"{tab_data['News']} News", key="tab_News",
                           type="secondary" if st.session_state.selected_tab == "News" else "primary",
                           use_container_width=True):
                    st.session_state.selected_tab = "News"
                    st.rerun()
            
            # Display content based on selected tab
            if st.session_state.selected_tab == "Charts":
                st.info("Interactive price charts will be available soon! 📊")
            elif st.session_state.selected_tab == "Reports":
                st.info("Financial reports and analysis coming soon! 📊")
            elif st.session_state.selected_tab == "Forecast":
                st.info("AI-powered price predictions coming soon! 🔮")
            else:  # News tab
                st.info("Latest market news and updates coming soon! 📰")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        st.session_state.selected_stock = current_data.iloc[0]['Symbol']
        st.rerun()
else:
    st.markdown('<div class="empty-dashboard-message">👈 Select a stock from the sidebar to view its dashboard</div>', unsafe_allow_html=True)
