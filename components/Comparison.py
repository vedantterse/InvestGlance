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
            hist = ticker.history(period="4mo")  # Get 4 months of data for quarterly comparison
            
            if (hist.empty):
                continue
                
            # Get latest price
            latest_price = hist['Close'].iloc[-1]
            
            # Calculate quarterly price change (approximately 63 trading days)
            quarterly_price_change = None
            if len(hist) >= 63:
                price_3m_ago = hist['Close'].iloc[-63]
                quarterly_price_change = ((latest_price - price_3m_ago) / price_3m_ago) * 100
            
            # Calculate trend
            sma20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) > 20 else None
            sma50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) > 50 else None
            
            if sma20 is not None and sma50 is not None:
                trend = "up" if sma20 > sma50 else "down"
            else:
                # Fallback to comparing with recent average
                avg_price = hist['Close'].iloc[-10:].mean() if len(hist) > 10 else hist['Close'].mean()
                trend = "up" if latest_price > avg_price else "down"
                
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
                "percent_change": quarterly_price_change if quarterly_price_change is not None else 0.0
            }
            
            # 2. Get fundamental data using Reports.py functions
            try:
                soup = fetch_screener_data(symbol)
                quarterly_data = extract_quarterly_data(soup)
                profit_loss = extract_profit_loss_data(soup)
                # balance_sheet = extract_balance_sheet_data(soup) # Keep commented for now

                peer_data[symbol]["fundamental"] = {
                    "quarterly_data_available": quarterly_data is not None and not quarterly_data.empty,
                    "profit_loss_available": profit_loss is not None and not profit_loss.empty,
                    # "balance_sheet_available": balance_sheet is not None and not balance_sheet.empty
                }

                # Extract key metrics if available
                q_sales_growth = None
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
                            q_sales_growth = calculate_growth(
                                quarterly_data.loc[sales_row, dates[-1]], 
                                quarterly_data.loc[sales_row, dates[-2]]
                            )
                            peer_data[symbol]["fundamental"]["quarterly_sales_growth"] = q_sales_growth

                a_profit_growth = None
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
                            a_profit_growth = calculate_growth(
                                profit_loss.loc[profit_row, years[-1]],
                                profit_loss.loc[profit_row, years[-2]]
                            )
                            peer_data[symbol]["fundamental"]["annual_profit_growth"] = a_profit_growth
                
                # Add a warning if fundamental data seems missing after trying
                if q_sales_growth is None and a_profit_growth is None:
                     st.warning(f"Could not extract key fundamental growth metrics (Sales/Profit) for {symbol}. Ranking may be less accurate.")


            except Exception as e:
                st.warning(f"Could not fetch or parse fundamental data for {symbol}: {e}") # Make warning more specific
                pass # Continue with technical data only
            
        except Exception as e:
            st.error(f"Error processing data for {symbol}: {e}") # Use st.error for processing errors
            continue
    
    # 3. Send consolidated data to Gemini for analysis
    try:
        api_key = st.secrets["api_keys"]["gemini"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')  # Using flash for speed
        
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
1. Rank these companies from best to worst investment options. **Prioritize fundamental strength (Annual Profit Growth, Quarterly Sales Growth) as the primary driver for ranking.** Technical trends (price momentum, SMA position) should act as secondary factors, confirming or contradicting the fundamental picture. A company with strong fundamentals should rank highly even if recent price action is weak.
2. Give each company a grade: "High", "Medium", or "Low", reflecting this **fundamentals-first** assessment.
3. For each company, provide 3 short, easy-to-understand insights about their performance.

Requirements for Insights (Keep these exactly as specified):
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
            # Explicitly show N/A if data is missing
            q_sales_growth = fund_data.get('quarterly_sales_growth')
            a_profit_growth = fund_data.get('annual_profit_growth')
            prompt += f"Recent quarterly sales growth: {q_sales_growth:.2f}%\n" if q_sales_growth is not None else "Recent quarterly sales growth: N/A\n"
            prompt += f"Annual profit growth: {a_profit_growth:.2f}%\n" if a_profit_growth is not None else "Annual profit growth: N/A\n"
        else:
             prompt += "Fundamental Data: Not Available\n"

    prompt += """
Provide your response in the following JSON format:
{
  "rankings": [
    {
      "symbol": "STOCKA", 
      "rank": 1, 
      "grade": "High", 
      "insights": [
        "POSITIVE: Strong sales growth shows the company is beating competitors.",
        "POSITIVE: Market leader with established customer base and brand recognition.",
        "POSITIVE: Steady profits demonstrate solid business management and planning."
      ]
    },
    {"symbol": "STOCKB", "rank": 2, "grade": "High", "insights": [...]}
  ]
}

IMPORTANT GUIDELINES for Insights (Keep these exactly as specified):
1. Write like you're explaining to a friend, not a financial expert
2. Focus on what makes each company strong or weak as a business
3. Avoid financial jargon and complex terminology
4. Make each insight specific to the company, not generic statements
5. Prefix insights with "POSITIVE:" or "NEGATIVE:" based on the implication for the investor.
6. Keep insights simple and direct - imagine explaining to a beginner investor

Ranking/Grading Guidelines (Reiteration):
- **Fundamentals First:** Base rank and grade primarily on Annual Profit Growth and Quarterly Sales Growth.
- Technicals as Modifiers: Use price trend and momentum (1m/3m change) to adjust the rank slightly or confirm the fundamental view, but they should NOT override strong/weak fundamentals.
- Example: High profit/sales growth + Down trend = Still likely High/Medium rank.
- Example: Low profit/sales growth + Up trend = Still likely Medium/Low rank.
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
                if symbol and symbol in peer_data: # Check if symbol is valid
                    # Fix any mixed grades to standard ones
                    grade = item.get('grade', 'Low')
                    if '/' in grade:
                        grade = grade.split('/')[0]
                    
                    # Ensure grade is standardized
                    valid_grades = ["High", "Medium", "Low"]
                    if grade not in valid_grades:
                        if "high" in grade.lower(): grade = "High"
                        elif "med" in grade.lower(): grade = "Medium"
                        else: grade = "Low"
                    
                    # Process insights, ensuring prefix exists
                    insights = item.get('insights', ["No insights available"])
                    formatted_insights = []
                    
                    # Define patterns to detect problematic insights (Keep this logic)
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
                        
                        # Check if insight contains complex terms or is too long (Keep this logic)
                        contains_complex_terms = any(term in insight.lower() for term in complex_terms)
                        is_too_long = len(insight.split()) > 15
                        needs_simplification = contains_complex_terms or is_too_long
                        
                        # If insight needs simplification, replace with simpler alternatives (Keep this logic)
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
                            else: # Low grade
                                alternatives = [
                                    "Current price may be attractive for bargain hunters.",
                                    "Facing tough challenges in the current market.",
                                    "Needs major improvements to compete effectively.",
                                    "Business results lag behind most competitors.",
                                    "Struggles to maintain customer base against competitors.",
                                    "Current strategy not delivering expected results."
                                ]
                                insight = alternatives[i % len(alternatives)]

                        # Ensure POSITIVE/NEGATIVE prefix is present
                        if not insight.startswith("POSITIVE:") and not insight.startswith("NEGATIVE:"):
                             # Basic guess based on grade and index
                             if grade == "High" or (grade == "Medium" and i < 1):
                                 insight = f"POSITIVE: {insight}"
                             else:
                                 insight = f"NEGATIVE: {insight}"

                        formatted_insights.append(insight)
                    
                    # Ensure exactly 3 insights with prefixes
                    while len(formatted_insights) < 3:
                        if grade == "High":
                            formatted_insights.append("POSITIVE: Company shows potential for future growth.")
                        elif grade == "Medium":
                            formatted_insights.append("NEGATIVE: Faces challenges in improving its market position.")
                        else:
                            formatted_insights.append("NEGATIVE: Significant risks identified in current business model.")
                    
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
                elif symbol:
                     st.warning(f"AI returned analysis for symbol '{symbol}' which was not in the request or peer data. Skipping.")

            # Fallback for missing symbols (if AI missed some)
            for symbol in peer_data.keys():
                if symbol not in results:
                    st.warning(f"AI analysis missing for {symbol}. Using basic ranking data.")
                    basic_rank_data = basic_ranking({symbol: peer_data[symbol]})
                    if symbol in basic_rank_data:
                        results[symbol] = basic_rank_data[symbol]
                        # Assign a fallback rank to ensure it appears last
                        results[symbol]['rank'] = 998 

            # Re-evaluate grades based on final ranks to ensure consistency (optional but good)
            ranked_stocks = sorted(results.items(), key=lambda x: x[1]['rank'])
            num_stocks = len(ranked_stocks)
            if num_stocks > 0:
                high_cutoff_rank = max(1, round(num_stocks * 0.3)) # Top 30% High
                medium_cutoff_rank = max(high_cutoff_rank + 1, round(num_stocks * 0.7)) # Next 40% Medium
                
                for i, (symbol, data) in enumerate(ranked_stocks):
                    rank = data['rank']
                    # Don't override AI grade if it's already High/Medium unless rank dictates Low
                    current_grade = data['grade']
                    new_grade = "Low" # Default
                    if rank <= high_cutoff_rank: new_grade = "High"
                    elif rank <= medium_cutoff_rank: new_grade = "Medium"
                    
                    # Only downgrade if rank suggests it, otherwise keep AI's grade if better
                    if new_grade == "Low": results[symbol]['grade'] = "Low"
                    elif new_grade == "Medium" and current_grade == "Low": results[symbol]['grade'] = "Medium"
                    elif new_grade == "High" and current_grade != "High": results[symbol]['grade'] = "High"
                    # else keep the original grade from AI/basic

            return results
            
    except json.JSONDecodeError as json_err:
        st.error(f"Error parsing AI response (Invalid JSON): {json_err}")
    except Exception as e:
        st.error(f"Unexpected error processing AI response: {str(e)}")
        
    # Fallback to basic ranking if parsing fails or any other error
    st.warning("Falling back to basic ranking due to AI response processing error.")
    return basic_ranking(peer_data)


def basic_ranking(peer_data):
    """Provide a basic ranking if Gemini fails, balancing tech and fundamentals with emphasis on fundamentals"""
    results = {}
    stocks = []
    
    for symbol, data in peer_data.items():
        technical = data.get('technical', {})
        fundamental = data.get('fundamental', {})
        price_data = data.get('price_data', {})
        
        # Adjusted scoring: Prioritize fundamentals heavily
        score = 0
        
        # Fundamental Score (Max ~10 points) - Increased weight significantly
        q_sales = fundamental.get('quarterly_sales_growth')
        a_profit = fundamental.get('annual_profit_growth')

        if q_sales is not None:
            if q_sales > 20: score += 4 # Strong sales growth
            elif q_sales > 10: score += 3
            elif q_sales > 0: score += 2 # Positive sales growth
            elif q_sales < -10: score -= 2 # Penalize significant sales decline
        
        if a_profit is not None:
             if a_profit > 25: score += 5 # Very strong profit growth
             elif a_profit > 15: score += 4
             elif a_profit > 5: score += 3 # Decent profit growth
             elif a_profit > 0: score += 1
             elif a_profit < -15: score -= 3 # Penalize significant profit decline
             
        # Technical Score (Max ~4 points) - Reduced weight, acts as modifier
        trend = price_data.get('trend', 'neutral')
        m3_change = technical.get('3m_change', 0)
        # m1_change = technical.get('1m_change', 0) # Reduce focus on very short term

        if trend == 'up': score += 1 # Small bonus for up trend
        # No penalty for down trend if fundamentals are strong
        
        if m3_change > 15: score += 2 # Bonus for strong sustained momentum
        elif m3_change > 5: score += 1
        elif m3_change < -10 and (a_profit is None or a_profit < 5): score -= 1 # Penalize strong negative momentum only if fundamentals are weak/unknown

        # Volume trend bonus (Max 1 point)
        if technical.get('volume_trend', 1.0) > 1.2: score += 1
             
        # Store in list for sorting
        stocks.append({
            'symbol': symbol,
            'score': score,
            'price_data': price_data,
            'fundamental': fundamental,
            'technical': technical
        })
    
    # Sort by score (descending)
    stocks.sort(key=lambda x: x['score'], reverse=True)
    
    # Determine grades based on rank (more reliable than absolute score)
    num_stocks = len(stocks)
    high_cutoff_rank = max(1, round(num_stocks * 0.3)) # Top 30% High
    medium_cutoff_rank = max(high_cutoff_rank + 1, round(num_stocks * 0.7)) # Next 40% Medium
    
    # Convert to results format
    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        rank = i + 1
        
        # Determine grade based on rank
        if rank <= high_cutoff_rank: grade = "High"
        elif rank <= medium_cutoff_rank: grade = "Medium"
        else: grade = "Low"
        
        # Generate insights using the same logic as before (user liked this)
        insights = []
        fundamental = stock['fundamental'] # Get fundamental data back
        technical = stock['technical'] # Get technical data back
        if grade == "High":
            if fundamental.get('quarterly_sales_growth', 0) > 5: insights.append("POSITIVE: Sales are growing, showing strong customer demand.")
            else: insights.append("POSITIVE: Company has a strong position in its industry.")
        elif grade == "Medium": insights.append("POSITIVE: Business performance is steady but could improve.")
        else:
             if fundamental.get('quarterly_sales_growth', -1) < 0: insights.append("NEGATIVE: Recent sales decline raises concerns about performance.")
             else: insights.append("POSITIVE: Current price may offer value if business improves.")
        if grade == "High": insights.append("POSITIVE: Company stands out as a leader among competitors.")
        elif grade == "Medium":
            if technical.get('volume_trend', 1.0) > 1.1: insights.append("POSITIVE: Increasing investor interest shows growing confidence.")
            else: insights.append("POSITIVE: Holding its own against industry competition.")
        else: insights.append("NEGATIVE: Struggles to keep up with stronger competitors.")
        if grade == "High":
            if fundamental.get('annual_profit_growth', 0) > 10: insights.append("POSITIVE: Strong profit growth supports a positive outlook.")
            else: insights.append("POSITIVE: Strong foundation for continued success and growth.")
        elif grade == "Medium":
            if fundamental.get('annual_profit_growth', 5) < 5 and fundamental.get('annual_profit_growth') is not None: insights.append("NEGATIVE: Profit growth is slow, limiting upside potential.")
            else: insights.append("NEGATIVE: Needs improvements to catch up to industry leaders.")
        else: insights.append("NEGATIVE: Major changes needed to improve business performance.")
        while len(insights) < 3: insights.append("POSITIVE: Further analysis may reveal opportunities.") # Generic filler

        results[symbol] = {
            'rank': rank,
            'grade': grade,
            'insights': insights[:3], # Ensure exactly 3
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
        
        # Calculate quarterly growth for color logic
        latest_price = None
        quarterly_price_change = None
        
        try:
            # Use yfinance to get 4 months of data for quarterly comparison
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="4mo")  # Get 4 months of data to ensure full quarter
            
            if not hist.empty:
                # Get latest price
                latest_price = hist['Close'].iloc[-1]
                
                # Get price from approximately 3 months ago (quarterly comparison)
                # About 63 trading days in 3 months
                if len(hist) >= 63:
                    price_3m_ago = hist['Close'].iloc[-63]
                    if price_3m_ago != 0: # Avoid division by zero
                         quarterly_price_change = ((latest_price - price_3m_ago) / price_3m_ago) * 100
        except Exception as e:
            # st.warning(f"Couldn't fetch historical data for quarterly price change: {e}") # Reduce noise
            quarterly_price_change = None

        # Get price info - prioritize using our calculated quarterly change
        price = peer['price'] if 'price' in peer and not pd.isna(peer['price']) else 'N/A'
        percent_change = quarterly_price_change if quarterly_price_change is not None else peer.get('percent_change', 0.0) # Use peer's percent_change as fallback
        if isinstance(price, (int, float)):
            price_display = f"₹{price:,.2f}"
            percent_display_val = f"{percent_change:.2f}%" if percent_change is not None else "--"
        else:
            price_display = "Not Available"
            percent_display_val = "--"
        if percent_change is not None and percent_change > 0:
            trend_class = "price-trend-up"
            percent_display = f"▲ {percent_display_val}"
        elif percent_change is not None and percent_change < 0:
            trend_class = "price-trend-down"
            percent_display = f"▼ {percent_display_val}"
        else:
            trend_class = "price-trend-neutral"
            percent_display = percent_display_val # Display 0.00% or -- without arrow

        # Set selected class
        selected_class = " selected" if peer.get('Is_Selected', False) else "" # Use get for safety
        medal_class = ""; medal_icon = ""
        valid_rank = isinstance(rank, int) and rank < 900 # Check for valid rank before using
        if valid_rank:
            if rank == 1: medal_class = " gold-medal"; medal_icon = "🥇"
            elif rank == 2: medal_class = " silver-medal"; medal_icon = "🥈"
            elif rank == 3: medal_class = " bronze-medal"; medal_icon = "🥉"
        grade_class = "grade-high" if grade == "High" else "grade-medium" if grade == "Medium" else "grade-low"
        
        # Format insights HTML - Rely on CSS class, remove +/- symbols from text
        insights_html = ""
        for insight in insights:
            if not insight: continue # Skip empty insights
                
            insight_text = insight
            insight_class = "" # Default: no specific color class
            icon = "•" # Default bullet
            
            # Check for POSITIVE/NEGATIVE prefix and set class/icon
            if insight_text.startswith("POSITIVE:"):
                insight_class = "positive-insight" # Assign green class
                insight_text = insight_text.replace("POSITIVE:", "").strip() # Remove prefix
                icon = "✅" # Use checkmark
            elif insight_text.startswith("NEGATIVE:"):
                insight_class = "negative-insight" # Assign red class
                insight_text = insight_text.replace("NEGATIVE:", "").strip() # Remove prefix
                icon = "❌" # Use cross mark
            
            # Add the insight with the determined class and icon
            insights_html += f'<div class="peer-insight {insight_class}"> {icon} {insight_text}</div>'

        # Reminder: Ensure your CSS file (assets/comparison.css) defines distinct styles
        # for .positive-insight (e.g., green text) and .negative-insight (e.g., red text).
        # The base .peer-insight class should have the default text color.
        # Example CSS:
        # .peer-insight.positive-insight { color: #4CAF50 !important; /* Green */ }
        # .peer-insight.negative-insight { color: #F44336 !important; /* Red */ }
        # .peer-insight { /* Default style */ }

        # Create HTML for peer tube with insights
        st.markdown(f"""
        <a href="/?stock={symbol}&tab=charts" target="_self" class="peer-tube-container" style="text-decoration: none; cursor: pointer; display: block;">
            <div class="peer-tube{selected_class}{medal_class}">
                <div class="peer-index">{medal_icon if medal_icon else (rank if valid_rank else '-')}</div>
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
