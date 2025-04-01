# InvestGlance

InvestGlance is a financial data visualization and analysis tool for NIFTY50 and NIFTY-NEXT50 stocks. It provides an educational interface for exploring stock market data, reports, and news in an accessible format.

## Features

- **Interactive Charts**: Technical price analysis with moving averages and trend signals
- **Financial Reports**: Visualized quarterly and annual financial data scraped from public sources
- **Peer Comparison**: AI-powered analysis of companies within the same industry
- **News Integration**: Latest stock-related news aggregated in one place

## How It Works

**InvestGlance fetches data from multiple sources:**
- ***Historical prices via Yahoo Finance API***
- ***Financial reports scraped from Screener.in***
- ***News from NewsAPI***

**The peer comparison feature implements a pragmatic approach similar to Retrieval-Augmented Generation (RAG):**

1. ***Data Collection***: Retrieves both technical metrics (price trends, moving averages) and fundamental data (quarterly growth, profit margins) for stocks in the same industry
2. ***Structured Formatting***: Organizes this data into a consistent, context-rich prompt
3. ***AI Processing***: Uses Google's Gemini LLM to analyze company performance relative to peers
4. ***Post-Processing***: Standardizes the output into clear rankings, grades, and accessible insights

## Installation

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/vedantterse/InvestGlance
   ```
   ```bash
   cd InvestGlance
   ```

2. Set up API keys:
   ```bash
   mkdir -p .streamlit
   ```
   ```bash
   echo '[api_keys]' > .streamlit/secrets.toml
   echo 'gemini = "YOUR_GEMINI_API_KEY"' >> .streamlit/secrets.toml
   echo 'newsapi = "YOUR_NEWSAPI_KEY"' >> .streamlit/secrets.toml
   ```

#### 3. Choone of the followinge one of the following installation 

 #### Option 1: Using Docker

```bash
# Build and run the container
docker compose up
```
#### Option 2: Local Installation

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```
#### 4. Access the application at http://localhost:8501

## Usage

1. Select a market (NIFTY50 or NEXT50) from the sidebar
2. Choose a stock from the list
3. Navigate between tabs to explore different aspects of the selected stock:
   - Charts: Technical analysis with price history and indicators
   - Reports: Financial statements and shareholding patterns
   - Comparison: Peer analysis within the same industry
   - News: Latest news related to the selected stock

## Disclaimer

InvestGlance is designed for educational purposes only. The analysis, rankings, and insights provided should not be considered as investment advice. Always conduct thorough research and consult qualified financial advisors before making investment decisions.
