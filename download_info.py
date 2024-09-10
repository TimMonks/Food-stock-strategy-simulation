import pandas as pd
import requests
import io


# Helper function to download price data from the API
def fetch_price_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/eod/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(url)
    print(response, " ", url)
    
    if response.status_code == 200:
        prices = pd.read_json(io.StringIO(response.text))
        prices['date'] = pd.to_datetime(prices['date'])
        prices.set_index('date', inplace=True)
        return prices[['adjusted_close']], response.status_code  # Return data and status code
    else:
        print(f"Error fetching prices for {ticker}: {response.status_code}")
        return pd.DataFrame(), response.status_code  # Return empty DataFrame and status code

# Helper function to download earnings data from the API
def fetch_earnings_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/calendar/earnings?api_token={api_key}&from={start_date}&to={end_date}&symbols={ticker}"
    response = requests.get(url)
    print(response, " ", url)
    
    if response.status_code == 200 and response.text.strip() != "":
        try:
            earnings = pd.read_csv(io.StringIO(response.text))
            earnings_dates = earnings['Report_Date'].dropna().unique()
            earnings_dates_str = ', '.join(earnings_dates)
            print(f"Earnings Dates for {ticker}: {earnings_dates_str}")
            return earnings_dates, response.status_code  # Return data and status code
        except Exception as e:
            print(f"Error processing earnings data for {ticker}: {e}")
            return [], response.status_code  # Return empty list and status code
    else:
        print(f"Error fetching earnings for {ticker}: {response.status_code}")
        return [], response.status_code  # Return empty list and status code

# Helper function to download dividend data from the API
def fetch_dividend_data(ticker, start_date, end_date, api_key):
    url = f"https://eodhd.com/api/div/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(url)
    print(response, " ", url)

    if response.status_code == 200 and response.text.strip() != "":
        try:
            dividends = response.json()
            dividend_dates = [pd.to_datetime(item['date']) for item in dividends if 'date' in item]
            dividend_dates_str = ', '.join([date.strftime('%Y-%m-%d') for date in dividend_dates])
            print(f"Dividend Dates for {ticker}: {dividend_dates_str}")
            return dividend_dates, response.status_code  # Return data and status code
        except Exception as e:
            print(f"Error processing dividend data for {ticker}: {e}")
            return [], response.status_code  # Return empty list and status code
    else:
        print(f"Error fetching dividends for {ticker}: {response.status_code}")
        return [], response.status_code  # Return empty list and status code

# Fetch market cap data and return with status code
def fetch_market_cap_data(ticker, start_date, end_date, api_key):
    ticker_to_request = ticker
    if ticker_to_request == 'NESN.SW':
        ticker_to_request = 'NSRGY.US'

    url = f"https://eodhd.com/api/historical-market-cap/{ticker_to_request}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(url)
    print(response, " ", url)  # Debug print
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data:
                market_caps = pd.DataFrame.from_records(list(data.values()))
                market_caps['date'] = pd.to_datetime(market_caps['date'])
                market_caps.set_index('date', inplace=True)
                return market_caps[['value']], response.status_code  # Return data and status code
            else:
                print(f"No market cap data found for {ticker}")
                return pd.DataFrame(), response.status_code  # Return empty DataFrame and status code
        except Exception as e:
            print(f"Error processing market cap data for {ticker}: {e}")
            return pd.DataFrame(), response.status_code  # Return empty DataFrame and status code
    else:
        print(f"Error fetching market cap data for {ticker}: {response.status_code}")
        return pd.DataFrame(), response.status_code  # Return empty DataFrame and status code



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