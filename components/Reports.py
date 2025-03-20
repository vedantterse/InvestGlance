import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from io import StringIO

def fetch_screener_data(company_code):
    url = f'https://www.screener.in/company/{company_code}/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.content, 'html.parser')

def clean_dataframe(df):
    # Create a copy of the DataFrame
    df = df.copy()
    
    # Clean up the data
    if len(df.columns) > 0:
        # If the first row contains the column names
        if isinstance(df.iloc[0], pd.Series) and df.iloc[0].astype(str).str.contains('Mar|Sep|Dec|Jun').any():
            df.columns = df.iloc[0]
            df = df.iloc[1:].copy()
        
        # Set the first column as index if it's not already
        if not df.index.name:
            df = df.set_index(df.columns[0])
        
        # Convert numeric values
        for col in df.columns:
            try:
                # First check if it's a percentage
                if df[col].astype(str).str.contains('%').any():
                    df[col] = df[col].astype(str).replace('%', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    # Remove commas and convert to numeric
                    df[col] = df[col].astype(str).replace(',', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass  # Keep as is if conversion fails
    
    return df

def extract_quarterly_data(soup):
    quarterly_table = soup.find('section', id='quarters')
    if quarterly_table:
        html_content = StringIO(str(quarterly_table))
        df = pd.read_html(html_content)[0]
        return clean_dataframe(df)
    return None

def extract_profit_loss_data(soup):
    profit_loss_section = soup.find('section', id='profit-loss')
    if profit_loss_section:
        html_content = StringIO(str(profit_loss_section))
        df = pd.read_html(html_content)[0]
        return clean_dataframe(df)
    return None

def extract_balance_sheet_data(soup):
    balance_sheet_section = soup.find('section', id='balance-sheet')
    if balance_sheet_section:
        try:
            table = balance_sheet_section.find('table')
            if table:
                df = pd.read_html(StringIO(str(table)))[0]
                if not df.empty:
                    df = df.dropna(how='all').dropna(axis=1, how='all')
                    df = df.set_index(df.columns[0])
                    for col in df.columns:
                        df[col] = df[col].astype(str).replace(',', '', regex=True)
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    return df
        except Exception as e:
            st.error(f"Error processing balance sheet data: {str(e)}")
    return None

def extract_shareholding_data(soup):
    """Extract shareholding pattern data from screener.in.
    Prioritizes trying to get the yearly shareholding data."""
    
    shareholding_section = soup.find('section', id='shareholding')
    if shareholding_section:
        try:
            # First, look specifically for the yearly-shp container which is normally hidden
            yearly_container = shareholding_section.find('div', {'data-tab-id': 'yearly-shp'})
            
            # If found, use the yearly data table
            if yearly_container and yearly_container.find('table'):
                table = yearly_container.find('table')
            else:
                # Try to find all the tables in the shareholding section
                tables = shareholding_section.find_all('table')
                
                # If multiple tables, the first one is typically quarterly, second one yearly
                if len(tables) > 1:
                    table = tables[1]  # Try to get the yearly data table
                else:
                    # Fallback to using whatever table is available
                    table = shareholding_section.find('table')
            
            if table:
                # Parse the table into a DataFrame
                df = pd.read_html(StringIO(str(table)))[0]
                if not df.empty:
                    df = df.dropna(how='all').dropna(axis=1, how='all')
                    df = df.set_index(df.columns[0])
                    
                    # Clean percentage values
                    for col in df.columns:
                        df[col] = df[col].astype(str).replace('%', '', regex=True)
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    return df
        except Exception as e:
            st.error(f"Error processing shareholding data: {str(e)}")
    return None

def get_company_id(soup):
    """Extract company ID from page if available for API access"""
    try:
        # Try to find company ID in meta tags or script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and 'var company' in script.string:
                for line in script.string.split('\n'):
                    if 'var company' in line and 'id:' in line:
                        # Extract ID value from the line like: var company = {id: 123456, ...}
                        id_part = line.split('id:')[1].split(',')[0].strip()
                        return id_part
    except:
        pass
    return None

def plot_financial_metrics(df, title, metrics):
    if df is None or df.empty:
        return None
        
    fig = make_subplots(
        rows=len(metrics), cols=1,
        subplot_titles=tuple(metric['title'] for metric in metrics),
        vertical_spacing=0.12
    )

    for i, metric in enumerate(metrics, 1):
        for item in metric['items']:
            if item['name'] in df.index:
                try:
                    y_data = df.loc[item['name']]
                    if item.get('strip_percent', False):
                        y_data = y_data.astype(str).replace('%', '', regex=True)
                        y_data = pd.to_numeric(y_data, errors='ignore')
                    fig.add_trace(
                        go.Scatter(x=df.columns, y=y_data, name=item['label'],
                                line=dict(color=item['color'])), row=i, col=1)
                except Exception as e:
                    st.warning(f"Could not plot {item['name']}: {str(e)}")
                    continue

    fig.update_layout(
        height=300 * len(metrics),
        title_text=title,
        showlegend=True
    )

    for i in range(1, len(metrics) + 1):
        fig.update_yaxes(title_text=metrics[i-1]['y_label'], row=i, col=1)

    return fig

def display_reports(symbol):
    """Display financial reports and analysis for the selected stock"""
    st.markdown(f"<h2>Financial Reports for {symbol}</h2>", unsafe_allow_html=True)
    
    with st.spinner("Fetching financial data..."):
        try:
            soup = fetch_screener_data(symbol)
            
            # Extract quarterly data
            quarterly_data = extract_quarterly_data(soup)
            profit_loss_data = extract_profit_loss_data(soup)
            
            # Function to find the best match for a metric name - reuse for all metrics
            def find_best_match(target, available_list):
                if target in available_list:
                    return target
                
                # Try without the plus sign
                base_name = target.replace(' +', '')
                for item in available_list:
                    if base_name in item:
                        return item
                
                # Try with variations
                variations = {
                    'Sales +': ['Sales', 'Revenue', 'Income', 'Total Income', 'Net Sales'],
                    'Expenses +': ['Expenses', 'Total Expenses', 'Cost', 'Operating Cost'],
                    'Operating Profit': ['Operating Profit', 'EBIT', 'EBITDA', 'Profit Before Tax', 'PBT'],
                    'Borrowings +': ['Borrowings', 'Total Borrowings', 'Debt', 'Total Debt'],
                    'Other Liabilities +': ['Other Liabilities', 'Total Liabilities', 'Current Liabilities'],
                    'Fixed Assets +': ['Fixed Assets', 'Total Fixed Assets', 'Net Block', 'Gross Block'],
                    'Investments': ['Investments', 'Total Investments', 'Long Term Investments']
                }
                
                if target in variations:
                    for var in variations[target]:
                        for item in available_list:
                            if var in item:
                                return item
                
                # Special case for Operating Profit - if not found, try "Profit before tax"
                if target == 'Operating Profit':
                    for item in available_list:
                        if 'profit before tax' in item.lower() or 'pbt' in item.lower():
                            return item
                
                return None
            
            if quarterly_data is not None and not quarterly_data.empty:
                # Create two columns for Quarterly and Annual data
                col1, col2 = st.columns(2)
                
                # Get available metrics for debugging
                quarterly_metrics_list = quarterly_data.index.tolist()
                
                with col1:
                    st.markdown("## Quarterly Results")
                    
                    # Define colors for quarterly metrics
                    colors = {
                        'Sales +': '#2196F3',       # Blue
                        'Expenses +': '#FF4444',    # Red
                        'Operating Profit': '#4CAF50'  # Green
                    }
                    
                    # Create the quarterly figure
                    quarterly_fig = go.Figure()
                    
                    # Add traces for quarterly metrics
                    metrics_to_plot = ['Sales +', 'Expenses +', 'Operating Profit']
                    plotted_items = 0
                    
                    for metric in metrics_to_plot:
                        match = find_best_match(metric, quarterly_metrics_list)
                        if match:
                            try:
                                # Set the label - use PBT if we're using Profit before tax as a fallback
                                label = metric
                                if metric == 'Operating Profit' and ('profit before tax' in match.lower() or 'pbt' in match.lower()):
                                    label = 'PBT'
                                
                                quarterly_fig.add_trace(
                                    go.Scatter(
                                        x=quarterly_data.columns, 
                                        y=quarterly_data.loc[match],
                                        name=label,  # Use the appropriate label
                                        line=dict(color=colors[metric])
                                    )
                                )
                                plotted_items += 1
                            except Exception as e:
                                st.warning(f"Could not plot quarterly {match}: {str(e)}")
                        else:
                            st.warning(f"Could not find a match for {metric} in quarterly data")
                    
                    # Add a placeholder trace if no metrics were plotted
                    if plotted_items == 0:
                        quarterly_fig.add_trace(
                            go.Scatter(
                                x=quarterly_data.columns,
                                y=[0] * len(quarterly_data.columns),
                                name="No Quarterly Data",
                                line=dict(color="#888888", dash="dash")
                            )
                        )
                    
                    # Update layout
                    quarterly_fig.update_layout(
                        title="Quarterly Performance",
                        height=350,
                        margin=dict(t=50, b=50, l=40, r=40),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        hovermode="x unified",
                        yaxis_title="Amount (Cr)"
                    )
                    
                    st.plotly_chart(quarterly_fig, use_container_width=True)
                
                with col2:
                    # Extract and plot profit & loss data
                    if profit_loss_data is not None and not profit_loss_data.empty:
                        st.markdown("## Year-on-Year Performance")
                        
                        # Get available metrics for profit_loss
                        annual_metrics_list = profit_loss_data.index.tolist()
                        
                        # Create the annual figure
                        annual_fig = go.Figure()
                        
                        # Add traces for annual metrics
                        plotted_items = 0
                        
                        for metric in metrics_to_plot:  # Reuse the same metrics list
                            match = find_best_match(metric, annual_metrics_list)
                            if match:
                                try:
                                    # Set the label - use PBT if we're using Profit before tax as a fallback
                                    label = metric
                                    if metric == 'Operating Profit' and ('profit before tax' in match.lower() or 'pbt' in match.lower()):
                                        label = 'PBT'
                                    
                                    annual_fig.add_trace(
                                        go.Scatter(
                                            x=profit_loss_data.columns, 
                                            y=profit_loss_data.loc[match],
                                            name=label,  # Use the appropriate label
                                            line=dict(color=colors[metric])
                                        )
                                    )
                                    plotted_items += 1
                                except Exception as e:
                                    st.warning(f"Could not plot annual {match}: {str(e)}")
                            else:
                                st.warning(f"Could not find a match for {metric} in annual data")
                        
                        # Add a placeholder trace if no metrics were plotted
                        if plotted_items == 0:
                            annual_fig.add_trace(
                                go.Scatter(
                                    x=profit_loss_data.columns,
                                    y=[0] * len(profit_loss_data.columns),
                                    name="No Annual Data",
                                    line=dict(color="#888888", dash="dash")
                                )
                            )
                        
                        # Update layout
                        annual_fig.update_layout(
                            title="Annual Performance",
                            height=350,
                            margin=dict(t=50, b=50, l=40, r=40),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            hovermode="x unified",
                            yaxis_title="Amount (Cr)"
                        )
                        
                        st.plotly_chart(annual_fig, use_container_width=True)
                    else:
                        st.warning("Annual financial data not available for this company.")
                
                # Add balance sheet metrics section - This remains full width
                balance_sheet_data = extract_balance_sheet_data(soup)
                if balance_sheet_data is not None and not balance_sheet_data.empty:
                    st.markdown("## Balance Sheet Components")
                    
                    # Create two columns for Liabilities and Assets
                    bs_col1, bs_col2 = st.columns(2)
                    
                    # First, let's print the available metrics to help debug
                    available_metrics = balance_sheet_data.index.tolist()
                    
                    # Define colors for each metric
                    colors = {
                        'Borrowings +': '#FF6B6B',       # Red
                        'Other Liabilities +': '#FF9E40', # Orange
                        'Fixed Assets +': '#4ECDC4',      # Teal
                        'Investments': '#7A77FF'          # Purple
                    }
                    
                    with bs_col1:
                        # Styled title with custom CSS for LIABILITIES - reduced vertical spacing
                        st.markdown("""
                            <div style="text-align: center; padding: 2px 0; margin-bottom: 2px;">
                                <h3 style="color: white; font-family: 'Arial Black', Gadget, sans-serif; 
                                letter-spacing: 1px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); 
                                margin: 0; font-weight: bold;">LIABILITIES</h3>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Create liabilities figure
                        liabilities_fig = go.Figure()
                        
                        # Add traces for liabilities
                        liability_metrics = ['Borrowings +', 'Other Liabilities +']
                        plotted_items = 0
                        
                        for metric in liability_metrics:
                            match = find_best_match(metric, available_metrics)
                            if match:
                                try:
                                    liabilities_fig.add_trace(
                                        go.Scatter(
                                            x=balance_sheet_data.columns, 
                                            y=balance_sheet_data.loc[match],
                                            name=metric,
                                            line=dict(color=colors[metric])
                                        )
                                    )
                                    plotted_items += 1
                                except Exception as e:
                                    st.warning(f"Could not plot liability {match}: {str(e)}")
                            else:
                                st.warning(f"Could not find a match for {metric} in balance sheet data")
                        
                        # Add a placeholder trace if no metrics were plotted
                        if plotted_items == 0:
                            liabilities_fig.add_trace(
                                go.Scatter(
                                    x=balance_sheet_data.columns,
                                    y=[0] * len(balance_sheet_data.columns),
                                    name="No Liability Data",
                                    line=dict(color="#888888", dash="dash")
                                )
                            )
                        
                        # Update layout
                        liabilities_fig.update_layout(
                            height=350,
                            margin=dict(t=50, b=50, l=40, r=40),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            hovermode="x unified",
                            yaxis_title="Amount (Cr)",
                            font=dict(color='white')
                        )
                        
                        # Add grid lines
                        liabilities_fig.update_xaxes(
                            showgrid=True,
                            gridwidth=0.5,
                            gridcolor='rgba(255,255,255,0.1)'
                        )
                        liabilities_fig.update_yaxes(
                            showgrid=True,
                            gridwidth=0.5,
                            gridcolor='rgba(255,255,255,0.1)'
                        )
                        
                        st.plotly_chart(liabilities_fig, use_container_width=True)
                    
                    with bs_col2:
                        # Styled title with custom CSS for ASSETS - reduced vertical spacing
                        st.markdown("""
                            <div style="text-align: center; padding: 5px 0; margin-bottom: 5px;">
                                <h3 style="color: white; font-family: 'Arial Black', Gadget, sans-serif; 
                                letter-spacing: 1px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); 
                                margin: 0; font-weight: bold;">ASSETS</h3>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Create assets figure
                        assets_fig = go.Figure()
                        
                        # Add traces for assets
                        asset_metrics = ['Fixed Assets +', 'Investments']
                        plotted_items = 0
                        
                        for metric in asset_metrics:
                            match = find_best_match(metric, available_metrics)
                            if match:
                                try:
                                    assets_fig.add_trace(
                                        go.Scatter(
                                            x=balance_sheet_data.columns, 
                                            y=balance_sheet_data.loc[match],
                                            name=metric,
                                            line=dict(color=colors[metric])
                                        )
                                    )
                                    plotted_items += 1
                                except Exception as e:
                                    st.warning(f"Could not plot asset {match}: {str(e)}")
                            else:
                                st.warning(f"Could not find a match for {metric} in balance sheet data")
                        
                        # Add a placeholder trace if no metrics were plotted
                        if plotted_items == 0:
                            assets_fig.add_trace(
                                go.Scatter(
                                    x=balance_sheet_data.columns,
                                    y=[0] * len(balance_sheet_data.columns),
                                    name="No Asset Data",
                                    line=dict(color="#888888", dash="dash")
                                )
                            )
                        
                        # Update layout
                        assets_fig.update_layout(
                            height=350,
                            margin=dict(t=50, b=50, l=40, r=40),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            hovermode="x unified",
                            yaxis_title="Amount (Cr)",
                            font=dict(color='white')
                        )
                        
                        # Add grid lines
                        assets_fig.update_xaxes(
                            showgrid=True,
                            gridwidth=0.5,
                            gridcolor='rgba(255,255,255,0.1)'
                        )
                        assets_fig.update_yaxes(
                            showgrid=True,
                            gridwidth=0.5,
                            gridcolor='rgba(255,255,255,0.1)'
                        )
                        
                        st.plotly_chart(assets_fig, use_container_width=True)
                else:
                    st.warning("Balance sheet data not available for this company.")
                
                # Add shareholding pattern section
                shareholding_data = extract_shareholding_data(soup)
                if shareholding_data is not None and not shareholding_data.empty:
                    st.markdown("## Shareholding Pattern")
                    
                    # Create categories mapping for grouping similar shareholder categories
                    category_mapping = {
                        'Promoters': ['Promoters', 'Promoter', 'Promoter Group', 'Promoter and Promoter Group', 'Promoters +'],
                        'FIIs': ['FII', 'FIIs', 'Foreign Portfolio Investors', 'Foreign Institutional Investors', 'NRIs', 'Foreign Companies', 'FIIs +'],
                        'DIIs': ['DII', 'DIIs', 'Mutual Funds', 'Financial Institutions', 'Banks', 'Insurance Companies', 'Domestic Institutional Investors', 'DIIs +'],
                        'Public': ['Public', 'Other Public', 'Non Institutions', 'Individuals', 'Retail', 'Public +']
                    }
                    
                    # Function to map a row index to a standard category
                    def map_to_category(idx):
                        for category, patterns in category_mapping.items():
                            if any(pattern.lower() in str(idx).lower() for pattern in patterns):
                                return category
                        return None
                    
                    # Process shareholding data
                    if not shareholding_data.empty:
                        # Get all available dates/quarters
                        dates = shareholding_data.columns.tolist()
                        
                        # Create mapping dictionary here before it's used
                        category_mapping_dict = {idx: map_to_category(idx) for idx in shareholding_data.index}
                        
                        # Filter out dates that might not be actual dates
                        valid_dates = []
                        for date in dates:
                            # Include all dates that have year information - expanded to include 2017
                            if isinstance(date, str) and any(year in date for year in ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']):
                                valid_dates.append(date)
                            elif not isinstance(date, str):
                                valid_dates.append(date)
                        
                        if valid_dates:
                            # Use a container to ensure consistent spacing
                            shareholding_container = st.container()
                            with shareholding_container:
                                # Create two columns with slightly wider right column for the bar chart
                                sh_col1, sh_col2 = st.columns([0.48, 0.52])
                                
                                with sh_col1:
                                    st.write("#### Annual Shareholding by Category")
                                    
                                    # Create a container for the pie chart
                                    pie_container = st.container()
                                    
                                    # Create a more aesthetically pleasing and compact date selector
                                    slider_container = st.container()
                                    with slider_container:
                                        s_col1, s_col2, s_col3 = st.columns([0.15, 0.7, 0.15])
                                        
                                        with s_col2:
                                            # Format dates to show year clearly for annual data
                                            def format_date(date_idx):
                                                date_str = str(valid_dates[date_idx])
                                                
                                                # Format for yearly data - extract the year part
                                                if '-' in date_str:
                                                    parts = date_str.split('-')
                                                    if len(parts) >= 1:
                                                        # For date like 2022-03-31, just show Mar '22
                                                        return f"Mar '{parts[0][-2:]}"
                                                
                                                # For simple year format
                                                if len(date_str) == 4 and date_str.isdigit():
                                                    return date_str
                                                    
                                                # If there's a month in the string
                                                for month in ['Mar', 'Jun', 'Sep', 'Dec']:
                                                    if month in date_str:
                                                        parts = date_str.split()
                                                        for part in parts:
                                                            if part.isdigit() and len(part) == 4:
                                                                return f"{month} '{part[-2:]}"
                                                
                                                # Default fallback
                                                return date_str
                                            
                                            # Create slider with yearly labels
                                            date_options = list(range(len(valid_dates)))
                                            selected_idx = st.select_slider(
                                                "Year",
                                                options=date_options,
                                                format_func=format_date,
                                                value=len(valid_dates)-1,
                                                label_visibility="collapsed"
                                            )
                                            
                                            # Show selected year prominently
                                            selected_date = valid_dates[selected_idx]
                                            formatted_date = format_date(selected_idx)
                                        
                                    
                                    # Now aggregate data based on the selected date
                                    aggregated_data = {}
                                    for idx, row in shareholding_data.iterrows():
                                        category = category_mapping_dict.get(idx)
                                        if category and selected_date in shareholding_data.columns:
                                            value = row[selected_date]
                                            if not pd.isna(value):
                                                if category in aggregated_data:
                                                    aggregated_data[category] += value
                                                else:
                                                    aggregated_data[category] = value
                                    
                                    # Create and display the pie chart with the aggregated data
                                    with pie_container:
                                        if aggregated_data:
                                            # Create pie chart with improved styling
                                            fig = go.Figure()
                                            
                                            # Define vibrant, distinct colors for each category
                                            colors = {
                                                'Promoters': '#FF6B6B',  # Vibrant red
                                                'FIIs': '#4ECDC4',       # Teal
                                                'DIIs': '#FFD166',       # Yellow
                                                'Public': '#118AB2'      # Blue
                                            }
                                            
                                            # Sort data for consistency
                                            sorted_categories = sorted(aggregated_data.keys())
                                            values = [aggregated_data[cat] for cat in sorted_categories]
                                            
                                            # Create pie chart with annual data formatting
                                            fig.add_trace(go.Pie(
                                                labels=sorted_categories,
                                                values=values,
                                                hole=0.3,
                                                textinfo='label+percent',
                                                textposition='inside',
                                                insidetextorientation='radial',
                                                textfont=dict(color='white', size=12),  # Ensuring all text is white
                                                marker=dict(
                                                    colors=[colors[cat] for cat in sorted_categories],
                                                    line=dict(color='#1F1F1F', width=2)
                                                ),
                                                hoverinfo='label+percent+value',
                                                hovertemplate='%{label}: %{percent} (%{value:.2f}%)<br>Year: ' + formatted_date + '<extra></extra>'
                                            ))
                                            
                                            # Update layout with title showing annual data
                                            fig.update_layout(
                                                height=350,
                                                title={
                                                    'text': f"Annual Holdings - {formatted_date}",
                                                    'y': 0.95,
                                                    'x': 0.5,
                                                    'xanchor': 'center',
                                                    'yanchor': 'top',
                                                    'font': {'size': 16, 'color': 'white'}
                                                },
                                                legend=dict(
                                                    orientation="h",
                                                    yanchor="top",
                                                    y=-0.1,
                                                    xanchor="center",
                                                    x=0.5,
                                                    font=dict(color='white')
                                                ),
                                                font=dict(
                                                    family="Arial, sans-serif",
                                                    color="white"
                                                ),
                                                margin=dict(t=50, b=60, l=20, r=20),  # Increased top margin for title
                                                paper_bgcolor='rgba(40,40,40,0.0)',
                                                plot_bgcolor='rgba(40,40,40,0.0)'
                                            )
                                            
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.warning(f"No shareholding data available for {formatted_date}")
                                
                                with sh_col2:
                                    st.write("#### Annual Shareholder Count Trend")
                                    
                                    # Look for the "No. of Shareholders" row in the shareholding data
                                    shareholder_count_row = None
                                    for idx in shareholding_data.index:
                                        if 'shareholder' in str(idx).lower() or 'number' in str(idx).lower() or 'no. of' in str(idx).lower():
                                            shareholder_count_row = idx
                                            break
                                    
                                    if shareholder_count_row is not None:
                                        # Extract the shareholder count data across all dates
                                        shareholder_counts = shareholding_data.loc[shareholder_count_row, valid_dates]
                                        
                                        # Format x-axis labels for yearly data
                                        x_labels = [format_date(i) for i in range(len(valid_dates))]
                                        
                                        # Create a bar chart specifically for yearly data
                                        bar_fig = go.Figure()
                                        
                                        # Add the bar trace with clean, modern styling
                                        bar_fig.add_trace(go.Bar(
                                            x=x_labels,
                                            y=shareholder_counts,
                                            marker_color='rgba(78, 205, 196, 0.85)',  # Teal with slight transparency
                                            text=shareholder_counts.round(0).astype(int),
                                            textposition='outside',
                                            hovertemplate='Year: %{x}<br>Shareholders: %{y:,}<extra></extra>'
                                        ))
                                        
                                        # Calculate appropriate y-axis range with headroom
                                        max_value = max(shareholder_counts) if len(shareholder_counts) > 0 else 0
                                        y_max = max_value * 1.25  # Add 25% headroom for text labels
                                        
                                        # Update layout optimized for yearly data with adjusted y-axis
                                        bar_fig.update_layout(
                                            height=430,  # Increased height for better visual balance
                                            autosize=True,
                                            title={
                                                'text': "Annual Shareholder Count",
                                                'y': 0.95,
                                                'x': 0.5,
                                                'xanchor': 'center', 
                                                'yanchor': 'top',
                                                'font': {'size': 16, 'color': 'white'}
                                            },
                                            yaxis=dict(
                                                title="Number of Shareholders",
                                                range=[0, y_max],  # Set y-axis range from 0 to calculated max
                                                tickformat=',d'    # Format tick labels with commas
                                            ),
                                            font=dict(color='white'),
                                            margin=dict(t=50, b=50, l=40, r=10),  # Reduced right margin
                                            bargap=0.25,  # Slightly wider gaps between bars for modern look
                                            paper_bgcolor='rgba(40,40,40,0.0)',
                                            plot_bgcolor='rgba(40,40,40,0.0)'
                                        )
                                        
                                        # Improved grid lines for modern look
                                        bar_fig.update_yaxes(
                                            showgrid=True,
                                            gridwidth=0.5,
                                            gridcolor='rgba(255,255,255,0.1)',
                                            zeroline=True,
                                            zerolinecolor='rgba(255,255,255,0.2)',
                                            zerolinewidth=1
                                        )
                                        
                                        # Update x-axis for better readability
                                        bar_fig.update_xaxes(
                                            tickangle=0,
                                            tickmode='array',
                                            tickvals=x_labels,
                                            ticktext=x_labels
                                        )
                                        
                                        # Simplified, clean bar styling
                                        bar_fig.update_traces(
                                            marker=dict(
                                                line=dict(width=0),  # Remove outline entirely
                                                opacity=1
                                            ),
                                            texttemplate='%{y:,.0f}',  # Format with commas, no decimal
                                            textposition='outside',
                                            textfont=dict(size=10, color='rgba(255,255,255,0.9)')
                                        )
                                        
                                        # Show the bar chart with consistent width
                                        st.plotly_chart(bar_fig, use_container_width=True)
                                    else:
                                        st.warning("No shareholder count data available")
                            # Add a bit of spacing after the section
                            st.write("")
                        else:
                            st.warning("No valid yearly shareholding data found")
                    else:
                        st.warning("Shareholding data is empty")
                else:
                    st.warning("Shareholding data not available for this company")
            
            else:
                st.error("Quarterly data not available for this company.")
        except Exception as e:
            st.error(f"Failed to fetch financial data: {str(e)}")

