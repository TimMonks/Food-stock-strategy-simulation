import os
import hashlib
import requests
import pandas as pd
import io
import json
import re

# Create a directory for caching
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Helper function to extract the API endpoint, ticker, and api_token from the URL
def extract_info_from_url(url):
    # Extract the part after /api/ and before the query parameters (API path)
    api_path_match = re.search(r'/api/([^?]+)', url)
    api_path = api_path_match.group(1).replace('/', '_') if api_path_match else "unknown"
    
    # Try to extract the ticker symbol from the query parameters (like symbols=AAPL.US)
    ticker_match = re.search(r'symbols?=([A-Za-z0-9._-]+)', url)
    
    # If no ticker found in the query, extract it from the path (like /eod/AAPL.US, /div/AAPL.US)
    if not ticker_match:
        ticker_path_match = re.search(r'/api/[^/]+/([A-Za-z0-9._-]+)', url)
        ticker = ticker_path_match.group(1) if ticker_path_match else "unknown"
    else:
        ticker = ticker_match.group(1)
    
    # Extract the API token from the query parameters
    api_token_match = re.search(r'api_token=([A-Za-z0-9.]+)', url)
    api_token = api_token_match.group(1) if api_token_match else "unknown_token"
    
    return api_path, ticker, api_token

# Helper function to download data and cache it
def download_and_cache_json(url, cache_dir=CACHE_DIR):
    # Extract the API path, ticker, and api_token from the URL
    api_path, ticker, api_token = extract_info_from_url(url)
    
    # Ensure that the ticker is properly identified, otherwise skip caching
    if ticker == "unknown":
        print(f"Warning: Ticker not found in URL {url}. Skipping cache.")
        return None, 404  # Return None and a status code indicating "Not Found"
    
    # Create subfolder for the ticker first, then the api_path (e.g., eod, calendar_earnings)
    ticker_dir = os.path.join(cache_dir, ticker)
    api_path_dir = os.path.join(ticker_dir, api_path)
    os.makedirs(api_path_dir, exist_ok=True)
    
    # Create a descriptive filename using the cleaned query parameters, excluding the api_token and api_path
    filename_parts = url.split('?')[1].replace('&', '_').replace('=', '_').replace('.', '_')  # Clean the query parameters
    filename_parts = re.sub(r'api_token=[^&]+', '', filename_parts)  # Remove api_token from filename
    filename = f"{filename_parts}.json".strip('_')  # Ensure the filename doesn't start or end with underscores
    
    # Define the full cache file path
    cache_file = os.path.join(api_path_dir, filename)

    # Check if the file exists in the cache
    if os.path.exists(cache_file):
        print(f"Loading from cache: {cache_file}")
        with open(cache_file, 'r') as f:
            data = json.load(f)
        return data, 200  # Return cached data with a 200 status code

    # If not in cache, download the data
    print(f"Downloading from URL: {url}")
    response = requests.get(url)
    
    # Check if response is empty or invalid JSON
    if response.status_code == 200:
        try:
            data = response.json()  # Try to parse the JSON response
        except requests.exceptions.JSONDecodeError:
            print(f"Error decoding JSON from {url}. Response was not JSON.")
            return None, response.status_code  # Return None if JSON parsing fails

        # Save the response JSON to cache
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        return data, response.status_code
    else:
        return None, response.status_code


# Helper function to download price data from the API with caching
def fetch_price_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/eod/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    data, status_code = download_and_cache_json(url)
    
    if status_code == 200 and data:
        prices = pd.read_json(io.StringIO(json.dumps(data)))
        prices['date'] = pd.to_datetime(prices['date'])
        prices.set_index('date', inplace=True)
        return prices[['adjusted_close']], status_code  # Return data and status code
    else:
        print(f"Error fetching prices for {ticker}: {status_code}")
        return pd.DataFrame(), status_code  # Return empty DataFrame and status code

    
# Helper function to download earnings data from the API with caching
def fetch_earnings_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/calendar/earnings?api_token={api_key}&from={start_date}&to={end_date}&symbols={ticker}&fmt=json"
    data, status_code = download_and_cache_json(url)
    
    if status_code == 200 and data:
        try:
            # Extract the earnings list from the JSON response
            earnings_list = data.get('earnings', [])
            # Extract report dates and ensure they are unique
            earnings_dates = pd.Series([pd.to_datetime(item['report_date']) for item in earnings_list if 'report_date' in item]).dropna().unique()
            return earnings_dates, status_code  # Return unique data and status code
        except Exception as e:
            print(f"Error processing earnings data for {ticker}: {e}")
            return [], status_code  # Return empty list and status code
    else:
        print(f"Error fetching earnings for {ticker}: {status_code}")
        return [], status_code  # Return empty list and status code


# Helper function to download dividend data from the API with caching
def fetch_dividend_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/div/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    data, status_code = download_and_cache_json(url)
    
    if status_code == 200 and data:
        dividend_dates = [pd.to_datetime(item['date']) for item in data if 'date' in item]
        return dividend_dates, status_code  # Return data and status code
    else:
        print(f"Error fetching dividends for {ticker}: {status_code}")
        return [], status_code  # Return empty list and status code

# Fetch market cap data and return with status code
def fetch_market_cap_data(ticker, start_date, end_date, api_key):
    ticker_to_request = ticker
    if ticker_to_request == 'NESN.SW':
        ticker_to_request = 'NSRGY.US'

    url = f"https://eodhd.com/api/historical-market-cap/{ticker_to_request}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    data, status_code = download_and_cache_json(url)
    
    if status_code == 200 and data:
        market_caps = pd.DataFrame.from_records(list(data.values()))
        market_caps['date'] = pd.to_datetime(market_caps['date'])
        market_caps.set_index('date', inplace=True)
        return market_caps[['value']], status_code  # Return data and status code
    else:
        print(f"Error fetching market cap data for {ticker}: {status_code}")
        return pd.DataFrame(), status_code  # Return empty DataFrame and status code


def download_data(api_key, tickers, start_date, end_date):
    # Placeholder for downloaded data and status codes
    downloaded_data = {}

    # Fetch prices, earnings, dividends, and market caps for each stock
    for ticker in tickers:
        print(f"\nFetching data for {ticker}...")

        # Fetch the prices, earnings, dividends, and market cap
        prices_df, price_status = fetch_price_data(ticker, start_date, end_date, api_key)
        earnings_dates, earnings_status = fetch_earnings_data(ticker, start_date, end_date, api_key)
        dividend_dates, dividend_status = fetch_dividend_data(ticker, start_date, end_date, api_key)
        market_cap_df, market_cap_status = fetch_market_cap_data(ticker, start_date, end_date, api_key)

        # Store the fetched data along with the status codes for each component
        downloaded_data[ticker] = {
            'prices': prices_df,
            'price_status': price_status,
            'earnings_dates': earnings_dates,
            'earnings_status': earnings_status,
            'dividends': dividend_dates,
            'dividends_status': dividend_status,
            'market_cap': market_cap_df,
            'market_cap_status': market_cap_status
        }

    print("\nData retrieval completed!")

    return downloaded_data