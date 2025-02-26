import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_extras.app_logo import add_logo
import streamlit.components.v1 as components

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

# Configure the page to use full width and remove padding
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# Load external CSS
with open('assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

with open('assets/dashboard.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Remove whitespace from the top of the page and sidebar
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            padding-top: 0rem;
        }
        .main > div {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        [data-testid="stSidebarNav"] {
            padding-top: 0rem;
        }
        [data-testid="collapsedControl"] {
            display: none
        }
        #MainMenu {display: none;}
        footer {display: none;}
        /* Reduce gap between sidebar and main content */
        [data-testid="stSidebarContent"] {
            gap: 0rem;
        }
    </style>
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
    st.session_state.selected_stock = nifty50_data.iloc[0]['Symbol'] if not nifty50_data.empty else None
    st.rerun()

if col2.button("NEXT50", type="secondary" if next50_selected else "primary", key="next50_btn"):
    st.session_state.selected_market = "NEXT50"
    # Set default stock to first stock in NEXT50
    st.session_state.selected_stock = next50_data.iloc[0]['Symbol'] if not next50_data.empty else None
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
        st.sidebar.markdown("""
            <div style='text-align: center; padding: 20px; color: #808080; font-family: Inter, sans-serif;'>
                No stocks found matching your search criteria.
            </div>
        """, unsafe_allow_html=True)
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
            
            # Enhanced header with modern styling and badges directly at the top
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
            
            # Create the tab buttons
            with col1:
                if st.button(f"{tab_data['Charts']}\nCharts", key="tab_Charts", 
                           type="secondary" if st.session_state.selected_tab == "Charts" else "primary"):
                    st.session_state.selected_tab = "Charts"
                    st.rerun()
                    
            with col2:
                if st.button(f"{tab_data['Reports']}\nReports", key="tab_Reports",
                           type="secondary" if st.session_state.selected_tab == "Reports" else "primary"):
                    st.session_state.selected_tab = "Reports"
                    st.rerun()
                    
            with col3:
                if st.button(f"{tab_data['Forecast']}\nForecast", key="tab_Forecast",
                           type="secondary" if st.session_state.selected_tab == "Forecast" else "primary"):
                    st.session_state.selected_tab = "Forecast"
                    st.rerun()
                    
            with col4:
                if st.button(f"{tab_data['News']}\nNews", key="tab_News",
                           type="secondary" if st.session_state.selected_tab == "News" else "primary"):
                    st.session_state.selected_tab = "News"
                    st.rerun()
            
# Close the tab container
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
    st.markdown("""
        <div style='text-align: center; padding: 50px; color: #666; font-family: Inter, sans-serif;'>
            👈 Select a stock from the sidebar to view its dashboard
        </div>
    """, unsafe_allow_html=True)
