import requests, time 
import pandas as pd
from datetime import datetime

def datetotimestamp(date):
    time_tuple= date.timetuple()
    timestamp = round(time.mktime(time_tuple))
    return timestamp 

start=datetotimestamp(datetime(2024,1,1))
end=datetotimestamp(datetime.today())
min5=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=5&from={start}&to={end}&countback=328&currencyCode=INR"
min15=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=15&from={start}&to={end}&countback=328&currencyCode=INR"
min30=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=30&from={start}&to={end}&countback=328&currencyCode=INR"
hour=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=60&from={start}&to={end}&countback=328&currencyCode=INR"
day=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=1D&from={start}&to={end}&countback=328&currencyCode=INR"
month=f"https://priceapi.moneycontrol.com/techCharts/indianMarket/stock/history?symbol=RELIANCE&resolution=1M&from={start}&to={end}&countback=328&currencyCode=INR"
print(hour)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def timestamptodate(timestamp):
    return datetime.fromtimestamp(timestamp) 
response = requests.get(month, headers=headers)
res = response.json()
data = pd.DataFrame(res)
print(data)
date=[]
for i in data['t']:
    date.append(timestamptodate(i))

# Create a new DataFrame with all columns properly aligned
final_data = pd.DataFrame({
    'DateTime': date,
    'Open': data['o'],
    'High': data['h'],
    'Low': data['l'],
    'Close': data['c'],
    'Volume': data['v']
})

print(final_data)