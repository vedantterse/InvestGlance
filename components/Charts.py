import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def display_charts(symbol):
    if not symbol:
        st.warning("No stock selected")
        return
    
    # Initialize session state for time frame if not exists or reset if stock changes
    if 'selected_timeframe' not in st.session_state:
        st.session_state.selected_timeframe = "1mo"  # Default to 1 month
    
    # Track the current stock to detect changes
    if 'current_chart_stock' not in st.session_state:
        st.session_state.current_chart_stock = symbol
    # If stock has changed, reset timeframe to default (1mo)
    elif st.session_state.current_chart_stock != symbol:
        st.session_state.selected_timeframe = "1mo"  # Reset to default when stock changes
        st.session_state.current_chart_stock = symbol  # Update current stock
    
    # Fetch and display data
    ticker_symbol = f"{symbol}.NS"
    
    # Get longer period data to ensure moving averages are calculated properly
    # We'll filter to the selected timeframe later
    try:
        with st.spinner(f"Loading {symbol} data..."):
            # Determine the period to fetch based on selected timeframe
            if st.session_state.selected_timeframe in ["1wk", "1mo"]:
                fetch_period = "6mo"  # Enough data for short timeframes
            elif st.session_state.selected_timeframe in ["3mo", "6mo", "1y"]:
                fetch_period = "1y"   # More data for medium timeframes
            elif st.session_state.selected_timeframe == "3y":
                fetch_period = "3y"   # Fetch 3 years of data
            else:  # 5y
                fetch_period = "5y"   # Fetch 5 years of data
                
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=fetch_period)
            
            if hist.empty:
                st.error(f"No data available for {symbol}.")
                return
            
            # Calculate beginner-friendly moving averages that work across timeframes
            # 20-day SMA - Short-term trend
            # 50-day SMA - Medium-term trend
            hist['SMA20'] = hist['Close'].rolling(window=20).mean()
            hist['SMA50'] = hist['Close'].rolling(window=50).mean()
            
            # Filter data based on selected timeframe
            if st.session_state.selected_timeframe == "1wk":
                hist = hist.iloc[-7:]
            elif st.session_state.selected_timeframe == "1mo":
                hist = hist.iloc[-30:]
            elif st.session_state.selected_timeframe == "3mo":
                hist = hist.iloc[-90:]
            elif st.session_state.selected_timeframe == "6mo":
                hist = hist.iloc[-180:]
            elif st.session_state.selected_timeframe == "1y":
                hist = hist.iloc[-365:]
            elif st.session_state.selected_timeframe == "3y":
                # Keep all data for 3y (we fetched exactly 3y)
                pass
            elif st.session_state.selected_timeframe == "5y":
                # Keep all data for 5y (we fetched exactly 5y)
                pass
            
            # Create chart figure
            fig = go.Figure()
            
            # Add candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name="Price",
                    increasing_line_color='#26a69a', 
                    decreasing_line_color='#ef5350'
                )
            )
            
            # Add volume chart with brighter color for better visibility
            volume_color = 'rgba(100, 149, 237, 0.6)'
            fig.add_trace(
                go.Bar(
                    x=hist.index,
                    y=hist['Volume'],
                    name="Volume",
                    marker=dict(color=volume_color),
                    yaxis="y2"
                )
            )
            
            # Add moving average lines
            if 'SMA20' in hist.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist['SMA20'],
                        name="20-day SMA",
                        line=dict(color='#FF9800', width=2),  # Orange line
                        opacity=0.9
                    )
                )
            
            if 'SMA50' in hist.columns:
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist['SMA50'],
                        name="50-day SMA",
                        line=dict(color='#2196F3', width=2),  # Blue line
                        opacity=0.9
                    )
                )
            
            # Detect crossovers for buy/sell signals
            if len(hist) > 1 and 'SMA20' in hist.columns and 'SMA50' in hist.columns:
                # Create crossover signals
                hist['SMA20_above_SMA50'] = (hist['SMA20'] > hist['SMA50']).astype(int)
                hist['buy_signal'] = (hist['SMA20_above_SMA50'].diff() == 1).astype(bool)
                hist['sell_signal'] = (hist['SMA20_above_SMA50'].diff() == -1).astype(bool)
                
                # Add buy signals (20 SMA crosses above 50 SMA)
                buy_signals = hist[hist['buy_signal']]
                if not buy_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_signals.index,
                            y=buy_signals['SMA20'],
                            mode='markers',
                            marker=dict(
                                symbol='triangle-up',
                                size=12,
                                color='#4CAF50',  # Green
                                line=dict(width=2, color='#FFFFFF')
                            ),
                            name='Buy Signal',
                            hoverinfo='text',
                            text=['Buy Signal: 20-day SMA crossed above 50-day SMA' for _ in range(len(buy_signals))],
                        )
                    )
                
                # Add sell signals (20 SMA crosses below 50 SMA)
                sell_signals = hist[hist['sell_signal']]
                if not sell_signals.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_signals.index,
                            y=sell_signals['SMA20'],
                            mode='markers',
                            marker=dict(
                                symbol='triangle-down',
                                size=12,
                                color='#F44336',  # Red
                                line=dict(width=2, color='#FFFFFF')
                            ),
                            name='Sell Signal',
                            hoverinfo='text',
                            text=['Sell Signal: 20-day SMA crossed below 50-day SMA' for _ in range(len(sell_signals))],
                        )
                    )
            
            # Update layout
            fig.update_layout(
                title=f"{symbol} Stock Price with Trend Signals",
                xaxis_title="Date",
                yaxis_title="Price (₹)",
                height=600,
                margin=dict(l=50, r=50, t=80, b=50),
                xaxis_rangeslider_visible=False,
                yaxis=dict(domain=[0.3, 1.0]),
                yaxis2=dict(
                    domain=[0, 0.2],
                    title="Volume",
                    showgrid=True
                ),
                template="plotly_dark",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
          
        # Timeframe selection buttons below the chart
        st.write("Select Time Frame:")
        cols = st.columns(7)
        time_frames = {
            "1wk": "1W", "1mo": "1M", "3mo": "3M",
            "6mo": "6M", "1y": "1Y", "3y": "3Y", "5y": "5Y"
        }
        
        for i, (tf_code, tf_name) in enumerate(time_frames.items()):
            with cols[i]:
                # Use different styling for active timeframe
                is_active = st.session_state.selected_timeframe == tf_code
                button_type = "secondary" if is_active else "primary"
                
                # Create a unique key for each button
                if st.button(
                    tf_name,
                    key=f"tf_button_{tf_code}",
                    type=button_type,
                    use_container_width=True
                ):
                    st.session_state.selected_timeframe = tf_code
                    st.rerun()
                            
    except Exception as e:
        st.error(f"Error fetching stock data: {e}")