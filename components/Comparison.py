# filepath: c:\Users\Acer\Desktop\INVEST GLANCE\components\forecast.py
import streamlit as st
import pandas as pd
import yfinance as yf
import time
import google.generativeai as genai
from components.Charts import display_charts
from components.Reports import fetch_screener_data, extract_quarterly_data, extract_profit_loss_data, extract_balance_sheet_data

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
            
        # Create a cache key for this industry
        cache_key = f"peer_analysis_{stock_industry}"

        # Setup session state for caching if not exists
        if "comparison_cache" not in st.session_state:
            st.session_state.comparison_cache = {}

        # Check if we have cached analysis for this industry
        peer_analysis = None
        current_time = time.time()
        cache_expiry = 24 * 60 * 60  # 24 hours in seconds

        # Get peer data from cache if available and not expired
        if (cache_key in st.session_state.comparison_cache and 
            current_time - st.session_state.comparison_cache[cache_key]['timestamp'] < cache_expiry):
            peer_analysis = st.session_state.comparison_cache[cache_key]['data']
        else:
            # Get price data and analyze performance for all peers if not cached
            with st.spinner("Analyzing peer performance and ranking stocks..."):
                peer_analysis = analyze_peers_with_gemini(peers['Symbol'].tolist(), stock_industry)
                
                # Save to session state cache
                st.session_state.comparison_cache[cache_key] = {
                    'data': peer_analysis,
                    'timestamp': current_time
                }
        
        # Add the "Selected" flag to the peers dataframe - this is always done regardless of cache
        peers['Is_Selected'] = peers['Symbol'] == symbol
        
        # Create columns for rank, grade, price data
        peers['rank'] = 999  # Default high rank (worst)
        peers['grade'] = "Low"
        peers['price'] = 'N/A'
        peers['trend'] = 'neutral'
        peers['percent_change'] = 0.0
        
        # Store insights in a separate dictionary since DataFrame doesn't handle lists well
        peer_insights = {}
        
        # Add ranking and insights data to peers dataframe (properly handling the insights list)
        for idx, row in peers.iterrows():
            sym = row['Symbol']
            if sym in peer_analysis:
                data = peer_analysis[sym]
                peers.loc[idx, 'rank'] = data['rank']
                peers.loc[idx, 'grade'] = data['grade']
                peers.loc[idx, 'price'] = data['price']
                peers.loc[idx, 'trend'] = data['trend']
                peers.loc[idx, 'percent_change'] = data['percent_change']
                # Store insights in separate dict
                peer_insights[sym] = data['insights']
        
        # Sort by rank
        peers = peers.sort_values('rank').reset_index(drop=True)
        
        # Display ranked peers
        display_ranked_peers(peers, peer_insights)
        
    except Exception as e:
        st.error(f"Error analyzing peer performance: {str(e)}")

def analyze_peers_with_gemini(symbols, industry):
    """
    Analyze peer stocks using data from Charts.py and Reports.py
    Send consolidated data to Gemini for ranking and insights
    """
    peer_data = {}
    analysis_results = {}
    
    # 1. Collect technical data for each symbol
    for symbol in symbols:
        try:
            # Initialize data structure
            peer_data[symbol] = {
                "technical": {},
                "fundamental": {},
                "price_data": {}
            }
            
            # Get price data
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="3mo")  # Get 3 months of data
            
            if (hist.empty):
                continue
                
            # Get latest price
            latest_price = hist['Close'].iloc[-1]
            
            # Calculate trend
            sma20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) > 20 else None
            sma50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) > 50 else None
            
            if sma20 is not None and sma50 is not None:
                trend = "up" if sma20 > sma50 else "down"
            else:
                # Fallback to comparing with recent average
                avg_price = hist['Close'].iloc[-10:].mean() if len(hist) > 10 else hist['Close'].mean()
                trend = "up" if latest_price > avg_price else "down"
                
            # Calculate percent change
            percent_change = 0.0
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                if prev_close > 0:
                    percent_change = ((latest_price - prev_close) / prev_close) * 100
            
            # Save technical data
            peer_data[symbol]["technical"] = {
                "latest_price": latest_price,
                "1m_change": ((latest_price - hist['Close'].iloc[-22]) / hist['Close'].iloc[-22] * 100) if len(hist) > 22 else 0,
                "3m_change": ((latest_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100) if len(hist) > 0 else 0,
                "volume_trend": hist['Volume'].iloc[-10:].mean() / hist['Volume'].iloc[-30:-10].mean() if len(hist) > 30 else 1.0,
                "sma20": sma20,
                "sma50": sma50
            }
            
            # Save price data
            peer_data[symbol]["price_data"] = {
                "price": latest_price,
                "trend": trend,
                "percent_change": percent_change
            }
            
            # 2. Get fundamental data using Reports.py functions
            try:
                soup = fetch_screener_data(symbol)
                quarterly_data = extract_quarterly_data(soup)
                profit_loss = extract_profit_loss_data(soup)
                balance_sheet = extract_balance_sheet_data(soup)
                
                peer_data[symbol]["fundamental"] = {
                    "quarterly_data_available": quarterly_data is not None and not quarterly_data.empty,
                    "profit_loss_available": profit_loss is not None and not profit_loss.empty,
                    "balance_sheet_available": balance_sheet is not None and not balance_sheet.empty
                }
                
                # Extract key metrics if available
                if quarterly_data is not None and not quarterly_data.empty:
                    # Try to find sales/revenue row
                    sales_row = None
                    for idx in quarterly_data.index:
                        if 'sales' in str(idx).lower() or 'revenue' in str(idx).lower():
                            sales_row = idx
                            break
                            
                    if sales_row is not None:
                        dates = quarterly_data.columns.tolist()
                        if len(dates) >= 2:
                            peer_data[symbol]["fundamental"]["quarterly_sales_growth"] = calculate_growth(
                                quarterly_data.loc[sales_row, dates[-1]], 
                                quarterly_data.loc[sales_row, dates[-2]]
                            )
                
                # Extract annual profit growth if available
                if profit_loss is not None and not profit_loss.empty:
                    # Try to find profit row
                    profit_row = None
                    for idx in profit_loss.index:
                        if 'profit after tax' in str(idx).lower() or 'pat' in str(idx).lower():
                            profit_row = idx
                            break
                            
                    if profit_row is not None:
                        years = profit_loss.columns.tolist()
                        if len(years) >= 2:
                            peer_data[symbol]["fundamental"]["annual_profit_growth"] = calculate_growth(
                                profit_loss.loc[profit_row, years[-1]],
                                profit_loss.loc[profit_row, years[-2]]
                            )
            
            except Exception as e:
                # Continue with technical data only
                pass
            
        except Exception as e:
            # Skip this symbol on error
            continue
    
    # 3. Send consolidated data to Gemini for analysis
    try:
        api_key = st.secrets["api_keys"]["gemini"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')  # Using flash for speed
        
        # Prepare data for Gemini
        prompt = generate_ranking_prompt(peer_data, industry)
        response = model.generate_content(prompt)
        
        # Process Gemini response
        analysis_results = parse_gemini_response(response.text, peer_data)
        
    except Exception as e:
        st.warning(f"Could not get AI insights: {str(e)}. Using basic ranking instead.")
        # Fallback to basic ranking
        analysis_results = basic_ranking(peer_data)
    
    return analysis_results

def generate_ranking_prompt(peer_data, industry):
    """Generate a prompt for Gemini to rank stocks and provide insights"""
    prompt = f"""Analyze these {industry} companies and provide simple, clear insights that any investor can understand.

Your task:
1. Rank these companies from best to worst investment options
2. Give each company a grade: "High", "Medium", or "Low"
3. For each company, provide 3 short, easy-to-understand insights about their performance

Requirements:
- Use simple, everyday language - avoid complex finance terms
- Focus on the most important strengths and weaknesses
- Talk about the business itself, not just stock price movements
- Keep each insight short (8-12 words)
- Use concrete facts rather than vague statements
- Do not include percentages or specific numbers in the insights

Stock Data:
"""
    
    for symbol, data in peer_data.items():
        prompt += f"\n--- {symbol} ---\n"
        
        # Add price data
        price_info = data.get("price_data", {})
        prompt += f"Current price: {price_info.get('price', 'N/A')}\n"
        prompt += f"Recent trend: {price_info.get('trend', 'N/A')}\n"
        prompt += f"1-day change: {price_info.get('percent_change', 0):.2f}%\n"
        
        # Add technical data
        tech_data = data.get("technical", {})
        prompt += f"1-month change: {tech_data.get('1m_change', 0):.2f}%\n"
        prompt += f"3-month change: {tech_data.get('3m_change', 0):.2f}%\n"
        prompt += f"Volume trend: {tech_data.get('volume_trend', 1):.2f}x\n"
        
        # Add fundamental data if available
        fund_data = data.get("fundamental", {})
        if fund_data:
            if 'quarterly_sales_growth' in fund_data:
                prompt += f"Recent quarterly sales growth: {fund_data['quarterly_sales_growth']:.2f}%\n"
            if 'annual_profit_growth' in fund_data:
                prompt += f"Annual profit growth: {fund_data['annual_profit_growth']:.2f}%\n"
    
    prompt += """
Provide your response in the following JSON format:
{
  "rankings": [
    {
      "symbol": "STOCKA", 
      "rank": 1, 
      "grade": "High", 
      "insights": [
        "Strong sales growth shows the company is beating competitors.",
        "Market leader with established customer base and brand recognition.",
        "Steady profits demonstrate solid business management and planning."
      ]
    },
    {"symbol": "STOCKB", "rank": 2, "grade": "High", "insights": [...]}
  ]
}

IMPORTANT GUIDELINES:
1. Write like you're explaining to a friend, not a financial expert
2. Focus on what makes each company strong or weak as a business
3. Avoid financial jargon and complex terminology
4. Make each insight specific to the company, not generic statements
5. Top 2 companies should be "High" grade if performance justifies it
6. Keep insights simple and direct - imagine explaining to a beginner investor
"""
    return prompt

def parse_gemini_response(response_text, peer_data):
    """Parse JSON response from Gemini into structured data"""
    import json
    import re
    
    # Try to extract JSON from response
    try:
        # Find json block within the response
        json_match = re.search(r'(\{[\s\S]*\})', response_text)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            # Process rankings
            results = {}
            for item in data.get('rankings', []):
                symbol = item.get('symbol')
                if symbol:
                    # Fix any mixed grades to standard ones
                    grade = item.get('grade', 'Low')
                    if '/' in grade:
                        grade = grade.split('/')[0]
                    
                    # Ensure grade is standardized
                    if grade not in ["High", "Medium", "Low"]:
                        if "high" in grade.lower():
                            grade = "High"
                        elif "med" in grade.lower():
                            grade = "Medium"
                        else:
                            grade = "Low"
                    
                    # Ensure insights are simple and accessible
                    insights = item.get('insights', ["No insights available"])
                    formatted_insights = []
                    
                    # Define patterns to detect problematic insights
                    complex_terms = [
                        'diversification', 'integration', 'commodity', 'volatility', 
                        'restructuring', 'strategic', 'governance', 'infrastructure',
                        'portfolio', 'reputational', 'acquisition', 'sentiment', 'trajectory',
                        'fundamentals', 'operational excellence', 'execution'
                    ]
                    
                    # Process each insight
                    for i, insight in enumerate(insights[:3]):
                        # Make sure insight ends with a period
                        if insight and not insight.endswith(('.', '!', '?')):
                            insight += '.'
                        
                        # Check if insight contains complex terms
                        contains_complex_terms = any(term in insight.lower() for term in complex_terms)
                        is_too_long = len(insight.split()) > 15
                        
                        # Determine if we need to simplify the insight
                        needs_simplification = contains_complex_terms or is_too_long
                        
                        # If insight needs simplification, replace with simpler alternatives
                        if needs_simplification:
                            if grade == "High":
                                alternatives = [
                                    "Company leads the industry with strong business performance.",
                                    "Growing market share shows competitive strength.",
                                    "Steady profit growth shows good business management.",
                                    "Product quality and innovation drive customer loyalty.",
                                    "Strong brand gives the company pricing power.",
                                    "Smart leadership makes good decisions for long-term growth."
                                ]
                                insight = alternatives[i % len(alternatives)]
                            elif grade == "Medium":
                                alternatives = [
                                    "Steady business performance with room to improve.",
                                    "Good position in the market but faces strong competition.",
                                    "Working on improvements to catch up to industry leaders.",
                                    "Business is stable but needs more growth.",
                                    "Some strengths but also has clear weaknesses.",
                                    "Making progress but still behind top competitors."
                                ]
                                insight = alternatives[i % len(alternatives)]
                            else:
                                alternatives = [
                                    "Current price may be attractive for bargain hunters.",
                                    "Facing tough challenges in the current market.",
                                    "Needs major improvements to compete effectively.",
                                    "Business results lag behind most competitors.",
                                    "Struggles to maintain customer base against competitors.",
                                    "Current strategy not delivering expected results."
                                ]
                                insight = alternatives[i % len(alternatives)]
                        
                        # Add appropriate prefix based on grade and position
                        if grade == "High" or (grade == "Medium" and i < 2):
                            formatted_insights.append(f"POSITIVE: {insight}")
                        else:
                            formatted_insights.append(f"NEGATIVE: {insight}")
                    
                    # Ensure we have exactly 3 insights
                    while len(formatted_insights) < 3:
                        if grade == "High":
                            formatted_insights.append("POSITIVE: Strategic positioning provides sustainable long-term growth potential.")
                        elif grade == "Medium":
                            formatted_insights.append("NEGATIVE: Performance gaps relative to sector leaders limit immediate upside potential.")
                        else:
                            formatted_insights.append("NEGATIVE: Structural challenges require substantial strategic shifts to improve trajectory.")
                    
                    # Add to results
                    results[symbol] = {
                        'rank': item.get('rank', 999),
                        'grade': grade,
                        'insights': formatted_insights[:3],
                        # Add price data from our original collection
                        'price': peer_data.get(symbol, {}).get('price_data', {}).get('price', 'N/A'),
                        'trend': peer_data.get(symbol, {}).get('price_data', {}).get('trend', 'neutral'),
                        'percent_change': peer_data.get(symbol, {}).get('price_data', {}).get('percent_change', 0.0)
                    }
            
            # Ensure top 2 ranks have High grade if there are at least 2 stocks
            ranked_stocks = sorted(results.items(), key=lambda x: x[1]['rank'])
            if len(ranked_stocks) >= 2:
                # Set top 2 to High grade
                for i in range(min(2, len(ranked_stocks))):
                    symbol = ranked_stocks[i][0]
                    results[symbol]['grade'] = "High"
            
            return results
            
    except Exception as e:
        st.warning(f"Error parsing Gemini response: {str(e)}")
        
    # Fallback to basic ranking if parsing fails
    return basic_ranking(peer_data)

def basic_ranking(peer_data):
    """Provide a basic ranking if Gemini fails"""
    results = {}
    
    # Convert to list for sorting
    stocks = []
    for symbol, data in peer_data.items():
        technical = data.get('technical', {})
        
        # Create a simple score based on available metrics
        score = 0
        
        # Add points for positive trend
        if data.get('price_data', {}).get('trend') == 'up':
            score += 2
        
        # Add points for positive changes
        m1_change = technical.get('1m_change', 0)
        m3_change = technical.get('3m_change', 0)
        
        if m1_change > 5:  # Strong 1-month performance
            score += 2
        elif m1_change > 0:
            score += 1
        
        if m3_change > 10:  # Strong 3-month performance
            score += 2
        elif m3_change > 0:
            score += 1
            
        # Check fundamental data
        fundamental = data.get('fundamental', {})
        if fundamental.get('quarterly_sales_growth', 0) > 10:
            score += 2
        elif fundamental.get('quarterly_sales_growth', 0) > 0:
            score += 1
            
        if fundamental.get('annual_profit_growth', 0) > 15:
            score += 2
        elif fundamental.get('annual_profit_growth', 0) > 0:
            score += 1
            
        # Store in list for sorting
        stocks.append({
            'symbol': symbol,
            'score': score,
            'price_data': data.get('price_data', {})
        })
    
    # Sort by score (descending)
    stocks.sort(key=lambda x: x['score'], reverse=True)
    
    # Calculate grade thresholds dynamically based on score distribution
    scores = [stock['score'] for stock in stocks]
    if scores:
        max_score = max(scores)
        high_threshold = max_score * 0.75
        medium_threshold = max_score * 0.5
    else:
        high_threshold = 6
        medium_threshold = 3
    
    # Convert to results format
    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        rank = i + 1
        score = stock['score']
        
        # Determine grade based on absolute score, not just rank
        if score >= high_threshold:
            grade = "High"
        elif score >= medium_threshold:
            grade = "Medium"
        else:
            grade = "Low"
        
        # Ensure top 2 are High if at least 2 stocks
        if i < 2 and len(stocks) >= 2:
            grade = "High"
        
        # Generate clear, simple insights
        insights = []
        
        # First insight - about business performance
        if grade == "High":
            if fundamental.get('quarterly_sales_growth', 0) > 0:
                insights.append("POSITIVE: Sales are growing, showing strong customer demand.")
            else:
                insights.append("POSITIVE: Company has a strong position in its industry.")
        elif grade == "Medium":
            insights.append("POSITIVE: Business performance is steady but could improve.")
        else:
            insights.append("POSITIVE: Current price may offer value if business improves.")
        
        # Second insight - about market position
        if grade == "High":
            insights.append("POSITIVE: Company stands out as a leader among competitors.")
        elif grade == "Medium":
            if technical.get('volume_trend', 1.0) > 1.0:
                insights.append("POSITIVE: Increasing investor interest shows growing confidence.")
            else:
                insights.append("POSITIVE: Holding its own against industry competition.")
        else:
            insights.append("NEGATIVE: Struggles to keep up with stronger competitors.")
        
        # Third insight - about future outlook
        if grade == "High":
            insights.append("POSITIVE: Strong foundation for continued success and growth.")
        elif grade == "Medium":
            insights.append("NEGATIVE: Needs improvements to catch up to industry leaders.")
        else:
            insights.append("NEGATIVE: Major changes needed to improve business performance.")
        
        # Add to results
        results[symbol] = {
            'rank': rank,
            'grade': grade,
            'insights': insights,
            'price': stock['price_data'].get('price', 'N/A'),
            'trend': stock['price_data'].get('trend', 'neutral'),
            'percent_change': stock['price_data'].get('percent_change', 0.0)
        }
    
    return results

def calculate_growth(current, previous):
    """Calculate percentage growth between two values"""
    try:
        if isinstance(current, (int, float)) and isinstance(previous, (int, float)) and previous != 0:
            return ((current - previous) / abs(previous)) * 100
        return 0
    except:
        return 0

def display_ranked_peers(peers, peer_insights):
    """Display ranked peers with medals and insights"""
    
    # Add industry header
    st.markdown(f"""
        <div class="comparison-wrapper">
            <div class="industry-header">
                <h3 class="industry-title">{peers.iloc[0]['Industry']} Performance Ranking</h3>
            </div>
    """, unsafe_allow_html=True)
    
    # Create tubes for each peer
    for i, (_, peer) in enumerate(peers.iterrows()):
        symbol = peer['Symbol']
        rank = int(peer['rank']) if not pd.isna(peer['rank']) else 999
        grade = peer['grade'] if not pd.isna(peer['grade']) else "Low"
        
        # Get insights from separate dictionary
        insights = peer_insights.get(symbol, ["No insights available"])
        insights = insights[:3]  # Limit to 3 insights
            
        # Pad insights list if it's too short
        while len(insights) < 3:
            insights.append("")
        
        # Get price info
        price = peer['price'] if 'price' in peer and not pd.isna(peer['price']) else 'N/A'
        trend = peer['trend'] if 'trend' in peer and not pd.isna(peer['trend']) else 'neutral'
        percent_change = peer['percent_change'] if 'percent_change' in peer and not pd.isna(peer['percent_change']) else 0.0
        
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
        
        # Apply medal styling for top 3
        medal_class = ""
        medal_icon = ""
        
        if rank == 1:
            medal_class = " gold-medal"
            medal_icon = "🥇"
        elif rank == 2:
            medal_class = " silver-medal"
            medal_icon = "🥈"
        elif rank == 3:
            medal_class = " bronze-medal"
            medal_icon = "🥉"
        
        # Determine grade class
        grade_class = "grade-high" if grade == "High" else "grade-medium" if grade == "Medium" else "grade-low"
        
        # Format insights HTML with + for positive and - for negative, but make them more professional
        insights_html = ""
        for insight in insights:
            if not insight:  # Skip empty insights
                continue
                
            insight_text = insight
            insight_class = ""
            
            # Check for POSITIVE/NEGATIVE prefix and style accordingly
            if "POSITIVE:" in insight_text:
                insight_class = "positive-insight"
                insight_text = insight_text.replace("POSITIVE:", "").strip()
                insight_text = f"+ {insight_text}"
            elif "NEGATIVE:" in insight_text:
                insight_class = "negative-insight"
                insight_text = insight_text.replace("NEGATIVE:", "").strip()
                insight_text = f"- {insight_text}"
                
            insights_html += f'<div class="peer-insight {insight_class}">{insight_text}</div>'
        
        # Create HTML for peer tube with insights
        st.markdown(f"""
        <a href="/?stock={symbol}&tab=charts" target="_self" class="peer-tube-container" style="text-decoration: none; cursor: pointer; display: block;">
            <div class="peer-tube{selected_class}{medal_class}">
                <div class="peer-index">{medal_icon if medal_icon else rank}</div>
                <div class="peer-info-container">
                    <div class="peer-header">
                        <div class="peer-name">{peer['Company Name']}</div>
                        <div class="peer-symbol-with-grade">
                            <span class="peer-symbol">{symbol}</span>
                            <span class="peer-grade {grade_class}">{grade}</span>
                        </div>
                    </div>
                    <div class="peer-insights-container">
                        {insights_html}
                    </div>
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
