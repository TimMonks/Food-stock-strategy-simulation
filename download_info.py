import pandas as pd
import requests
import io

def fetch_market_caps(tickers, start_date, end_date, api_key):
    market_caps_data = {}
    for ticker in tickers:
        
        # todo - replace this with a map of tickers to those with market cap info
        ticker_to_request = ticker
        if ticker_to_request=='NESN.SW':
            ticker_to_request = 'NSRGY.US'

        url = f"https://eodhd.com/api/historical-market-cap/{ticker_to_request}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
        response = requests.get(url)
        print(response, " ", url)  # Debug print
        if response.status_code == 200:
            data = response.json()
            if data:
                market_caps = pd.DataFrame.from_records(list(data.values()))
                market_caps['date'] = pd.to_datetime(market_caps['date'])
                market_caps.set_index('date', inplace=True)
                market_caps_data[ticker] = market_caps
            else:
                market_caps_data[ticker] = pd.DataFrame()
        else:
            print(f"Error fetching market caps for {ticker}: {response.status_code}")
            market_caps_data[ticker] = pd.DataFrame()
    return market_caps_data

# Helper function to download price data from the API
def fetch_price_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/eod/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(url)
    print(response, " ", url)
    
    if response.status_code == 200:
        prices = pd.read_json(io.StringIO(response.text))
        prices['date'] = pd.to_datetime(prices['date'])
        prices.set_index('date', inplace=True)
        return prices[['adjusted_close']]  # Only return the 'adjusted_close' price column
    else:
        print(f"Error fetching prices for {ticker}: {response.status_code}")
        return pd.DataFrame()

# Helper function to download earnings data from the API
def fetch_earnings_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/calendar/earnings?api_token={api_key}&from={start_date}&to={end_date}&symbols={ticker}"
    response = requests.get(url)
    print(response, " ", url)
    
    if response.status_code == 200 and response.text.strip() != "":
        try:
            earnings = pd.read_csv(io.StringIO(response.text))
            earnings_dates = earnings['Report_Date'].dropna().unique()
            # Print diagnostics for earnings dates
            earnings_dates_str = ', '.join(earnings_dates)
            print(f"Earnings Dates for {ticker}: {earnings_dates_str}")
            return earnings_dates
        except Exception as e:
            print(f"Error processing earnings data for {ticker}: {e}")
            return []
    else:
        print(f"Error fetching earnings for {ticker}: {response.status_code}")
        return []

# Helper function to download dividend data from the API
def fetch_dividend_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/div/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(url)
    print(response, " ", url)

    if response.status_code == 200 and response.text.strip() != "":
        try:
            dividends = response.json()
            dividend_dates = [pd.to_datetime(item['date']) for item in dividends if 'date' in item]
            # Print diagnostics for dividend dates
            dividend_dates_str = ', '.join([date.strftime('%Y-%m-%d') for date in dividend_dates])
            print(f"Dividend Dates for {ticker}: {dividend_dates_str}")
            return dividend_dates
        except Exception as e:
            print(f"Error processing dividend data for {ticker}: {e}")
            return []
    else:
        print(f"Error fetching dividends for {ticker}: {response.status_code}")
        return []



def download_data(api_key, tickers, start_date, end_date):
    # Placeholder for downloaded data
    downloaded_data = {}
        
    # Fetch prices, earnings, and dividends for each stock
    for ticker in tickers:
        print(f"\nFetching data for {ticker}...")

        # Fetch the prices, earnings, and dividends
        prices_df = fetch_price_data(ticker, start_date, end_date, api_key)
        earnings_dates = fetch_earnings_data(ticker, start_date, end_date, api_key)
        dividend_dates = fetch_dividend_data(ticker, start_date, end_date, api_key)
        
        # Convert dates to strings for CSV logging
        earnings_dates_str = ', '.join([str(date) for date in earnings_dates])
        dividend_dates_str = ', '.join([date.strftime('%Y-%m-%d') for date in dividend_dates])

        # Store the fetched data for later use
        downloaded_data[ticker] = {
            'prices': prices_df,
            'earnings_dates': earnings_dates,
            'dividends': dividend_dates
        }

    market_caps = fetch_market_caps(tickers, start_date, end_date, api_key)

    print("\nData retrieval completed!")

    return downloaded_data, market_caps