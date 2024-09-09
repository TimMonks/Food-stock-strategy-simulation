# %%
# Block 2: Data Retrieval

import requests
import io
import pandas as pd

import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend like 'Agg' (for PNGs)

pd.set_option('display.max_rows', 20)  # Show all rows

# Helper function to download price data from the API
def fetch_price_data(ticker, start_date, end_date, api_key):
    prices_url = f"https://eodhd.com/api/eod/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(prices_url)
    print(response, " ", prices_url)
    
    if response.status_code == 200:
        prices = pd.read_json(io.StringIO(response.text))
        prices['date'] = pd.to_datetime(prices['date'])
        prices.set_index('date', inplace=True)
        # Print diagnostics for earnings dates
        print(prices)
        return prices[['adjusted_close']]  # Only return the 'adjusted_close' price column
    else:
        print(f"Error fetching prices for {ticker}: {response.status_code}")
        return pd.DataFrame()

# Helper function to download earnings data from the API
def fetch_earnings_data(ticker, start_date, end_date, api_key):
    earnings_url = f"https://eodhd.com/api/calendar/earnings?api_token={api_key}&from={start_date}&to={end_date}&symbols={ticker}"
    response = requests.get(earnings_url)
    print(response, " ", earnings_url)
    
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
    dividends_url = f"https://eodhd.com/api/div/{ticker}?from={start_date}&to={end_date}&api_token={api_key}&fmt=json"
    response = requests.get(dividends_url)
    print(response, " ", dividends_url)

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

    print("\nData retrieval completed!")

    return downloaded_data


def process(downloaded_data, days_after_dividend, days_before_earnings, initial_investment):


    # %%
    import pandas as pd

    # Helper function to find the nearest valid date for price lookup
    def get_nearest_date(df, target_date):
        if target_date in df.index:
            return target_date
        nearest_idx = df.index.get_indexer([target_date], method='nearest')
        nearest_date = df.index[nearest_idx[0]]
        return nearest_date

    # Placeholder for cumulative returns data and nominal investment values
    investment_data = {}
    total_days_in_market = 0  # To calculate % time in market
    total_investment_days = 0  # To accumulate total days the investment could have been active

    # Loop over each stock and simulate the strategy
    for ticker, data in downloaded_data.items():
        print(f"\nProcessing {ticker} for strategy...")  # Diagnostic output
        
        # Extract the relevant data
        prices = data['prices']
        dividends = data['dividends']
        earnings_dates = data['earnings_dates']
        
        # Ensure that we have earnings dates and dividends data to process
        if len(earnings_dates) == 0:
            print(f"No earnings dates available for {ticker}. Skipping...")
            continue

        if len(dividends) == 0:
            print(f"No dividend data available for {ticker}. Skipping...")
            continue

        # Simulate the buy-sell strategy
        cumulative_investment = initial_investment  # Start with $1,000 initial investment
        cumulative_values = []  # Track cumulative value after each trade
        trade_dates = []  # Track the trade dates
        days_in_market = 0  # Track days in the market for this stock
        
        for ex_dividend_date in dividends:
            try:
                ex_dividend_date = pd.Timestamp(ex_dividend_date).tz_localize(None)
                buy_date = get_nearest_date(prices, ex_dividend_date + pd.DateOffset(days=days_after_dividend))
                buy_price = prices.loc[buy_date]['adjusted_close']

                next_earnings_dates = [pd.Timestamp(date) for date in earnings_dates if pd.Timestamp(date) > buy_date]
                if not next_earnings_dates:
                    print(f"No future earnings date available for {ticker} after {buy_date}")
                    continue

                next_earnings_date = min(next_earnings_dates)
                sell_date = get_nearest_date(prices, next_earnings_date - pd.DateOffset(days=days_before_earnings))
                sell_price = prices.loc[sell_date]['adjusted_close']
                
                days_held = (sell_date - buy_date).days
                days_in_market += days_held
                total_days_in_market += days_held

                trade_return = (sell_price - buy_price) / buy_price * 100
                cumulative_value = cumulative_investment * (1 + trade_return / 100)
                cumulative_investment = cumulative_value

                print(f"Trade on {ticker}: Buy on {buy_date} at {buy_price:.2f}, Sell on {sell_date} at {sell_price:.2f}, "
                    f"Return: {trade_return:.2f}%, Cumulative Value: {cumulative_value:.2f} $, Days Held: {days_held}")
                
                cumulative_values.append(cumulative_value)
                trade_dates.append(sell_date)
            
            except KeyError as e:
                print(f"KeyError for {ticker}: {e}")
                continue

        if len(cumulative_values) > 0:
            investment_data[ticker] = pd.Series(cumulative_values, index=trade_dates).groupby(level=0).sum()
            total_investment_days += (prices.index.max() - prices.index.min()).days

    print(f"\nDays in the market: {total_days_in_market:.0f}\nTotal days: {total_investment_days:.0f}")

    # Calculate overall percentage of time in the market
    if total_investment_days > 0:
        percent_time_in_market = (total_days_in_market / total_investment_days) * 100
        print(f"\nOverall % Time in Market: {percent_time_in_market:.1f}%")

    print("\nProcessing completed!")

    return investment_data, percent_time_in_market

def create_df(investment_data):
    if not investment_data:
        raise ValueError("No investment data available to convert.")

    investment_df = pd.DataFrame(investment_data)

    # Ensure data is numeric
    investment_df = investment_df.apply(pd.to_numeric, errors='coerce')
    if investment_df.empty or investment_df.isnull().all().all():
        raise ValueError("No valid numeric data available for plotting.")

    # Calculate the day before the start date dynamically
    if 'date' not in investment_df.columns:
        investment_df['date'] = pd.to_datetime(investment_df.index)
    investment_df.set_index('date', inplace=True)

    initial_investment_date = investment_df.index.min() - pd.Timedelta(days=1)
    initial_investment_row = pd.Series({ticker: 1000 for ticker in investment_df.columns}, name=initial_investment_date)
    investment_df = pd.concat([pd.DataFrame([initial_investment_row]), investment_df]).ffill()

    return investment_df

import base64
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd

def create_plot(investment_df, percent_time_in_market, days_after_dividend, days_before_earnings):

    # Calculate the total initial investment and final investment value
    initial_value = investment_df.iloc[0].sum()  # Sum of investments at the start
    final_value = investment_df.iloc[-1].sum()  # Sum of investments at the end

    # Calculate overall growth percentage
    growth_percentage = ((final_value - initial_value) / initial_value) * 100

    # Calculate the gain with no other buy/sell operations
    simple_buy_sell_gain = (investment_df.iloc[-1] - investment_df.iloc[0]) / investment_df.iloc[0] * 100
    simple_total_gain = simple_buy_sell_gain.sum()  # Sum the gains for a total overview

    fig, ax = plt.subplots(figsize=(10, 6))
    investment_df.plot(kind='area', stacked=True, ax=ax, title='Cumulative Nominal Investment Growth Over Time')
    plt.ylabel('Cumulative Investment Value ($)')
    plt.xlabel('Date')

    # Add a text box with the final value and growth percentage in the bottom-left corner
    textstr = f'Buy {days_after_dividend} days after ex dividend\nSell {days_before_earnings} days before earnings\nInitial Value: ${initial_value:,.2f}\nFinal Value: ${final_value:,.2f}\nOverall Growth: {growth_percentage:.2f}%\nTime in Market: {percent_time_in_market:.2f}%'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.05, 0.05, textstr, transform=ax.transAxes, fontsize=12,
            verticalalignment='bottom', bbox=props)

    # Add a second text box with the gain from simple buy and sell operation
    textstr2 = f'Simple Buy & Sell Gain: {simple_total_gain:.2f}%'
    ax.text(0.95, 0.05, textstr2, transform=ax.transAxes, fontsize=12,
            verticalalignment='bottom', horizontalalignment='right', bbox=props)
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close(fig)
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')

    return graph


