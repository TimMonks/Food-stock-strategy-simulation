# %%
# Block 2: Data Retrieval

import requests
import io
import pandas as pd

import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend like 'Agg' (for PNGs)

pd.set_option('display.max_rows', 20)  


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
        # Print diagnostics for earnings dates
        print(prices)
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

def get_top_n_stocks(market_caps_data, date_filter,n):
    latest_caps = {}
    date_filter = pd.to_datetime(date_filter)

    for ticker, data in market_caps_data.items():
        if data.empty:
            print(f"No data available for {ticker}.")
            continue

        # Filter data to include only entries up to and including the date filter
        filtered_data = data.loc[data.index <= date_filter]

        if not filtered_data.empty:
            latest_value = filtered_data['value'].iloc[-1]
            latest_caps[ticker] = latest_value
        else:
            print(f"No data for {ticker} on or before {date_filter}")

    if latest_caps:
        top_n = sorted(latest_caps, key=latest_caps.get, reverse=True)[:n]
        return top_n
    else:
        print("No stocks have data up to the specified date.")
        return []


def create_top_stocks_by_date(market_caps, start_date, end_date, n):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start=start, end=end, freq='1D') # EODHD is only per 7 says max, but we need daily data later

    # Prepare a DataFrame to store the data
    columns = ['Date', 'Stock', 'Rank']
    data = []

    for date in date_range:
        top_stocks = get_top_n_stocks(market_caps, date, 5)
        for rank, stock in enumerate(top_stocks, start=1):
            data.append({'Date': date, 'Stock': stock, 'Rank': rank})

    # Convert list of dicts into a DataFrame
    df = pd.DataFrame(data, columns=columns)

    # Group by Date and collect stocks into a list for each date
    top_stocks_by_date = df.groupby('Date')['Stock'].apply(list).reset_index()
    top_stocks_by_date.set_index('Date', inplace=True)

    return top_stocks_by_date


def process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment_per_pool):
    # We have 5 separate pools of $1,000 each
    free_capital_pools = [initial_investment_per_pool] * 5  # List of 5 pools, each starting with $1,000
    active_investments = {i: {} for i in range(5)}  # Track active investments for each pool (0 to 4)
    pending_sales = {i: {} for i in range(5)}  # Track pending sales for each pool
    pool_availability = [True] * 5  # Track if a pool is available (True) or currently in use (False)
    
    # New structure for investment results
    investment_results = {}  # Will store results as investment_results[date][ticker_or_pool_name] = value

    # Loop over each day provided by the top stocks data
    for date, top_stocks_row in top_stocks_by_date.iterrows():
        current_top_stocks = top_stocks_row['Stock']  # Stocks considered 'top' on this day
        date_str = date.strftime('%Y-%m-%d')
        investment_results[date_str] = {}  # Initialize results for the date

        # Diagnostics at the start of each day
        for i in range(5):
            # Track free capital for each pool
            investment_results[date_str][f"Pool {i} Free Capital"] = free_capital_pools[i]
            # Track investments for each pool
            if active_investments[i]:
                for ticker, investment_value in active_investments[i].items():
                    investment_results[date_str][f"Pool {i} - {ticker}"] = investment_value

        # First, process pending sales for today
        for i in range(5):
            if pending_sales[i]:
                ticker = pending_sales[i]['ticker']
                if pending_sales[i]['sell_date'] == date:
                    # Execute the sale
                    prices = downloaded_data[ticker]['prices']
                    sell_price = prices.loc[pending_sales[i]['sell_date'], 'adjusted_close']
                    buy_price = pending_sales[i]['buy_price']
                    investment_gain = (sell_price / buy_price - 1) * active_investments[i][ticker]
                    total_return = active_investments[i][ticker] + investment_gain  # Total value after sale

                    print(f"{date_str} - Pool {i}: Sold {ticker} - Bought at ${buy_price:.2f}, Sold at ${sell_price:.2f}, Gain: ${investment_gain:.2f}, Total Return: ${total_return:.2f}")

                    # Move proceeds back to free capital for the pool
                    free_capital_pools[i] += total_return
                    active_investments[i].pop(ticker)  # Remove the investment from the active investments
                    
                    # Mark pool as available again
                    pending_sales[i] = {}  # Clear pending sale
                    pool_availability[i] = True  # Mark pool as available

        # Next, process possible buys for today
        for ticker, data in downloaded_data.items():
            if ticker not in current_top_stocks:
                continue  # Skip processing if ticker is not in the top stocks for the day

            prices = data['prices']
            dividends = data['dividends']
            earnings_dates = [pd.Timestamp(d) for d in data['earnings_dates']]

            # Process each dividend date to determine possible buy dates
            for ex_dividend_date in dividends:
                ex_dividend_date = pd.Timestamp(ex_dividend_date)  # Ensure dividend date is a Timestamp
                intended_buy_date = ex_dividend_date + pd.DateOffset(days=days_after_dividend)

                if intended_buy_date == date and intended_buy_date in prices.index:  # Check if it's the right date to buy
                    valid_earnings_dates = [ed for ed in earnings_dates if ed > intended_buy_date]

                    if not valid_earnings_dates:
                        continue  # No valid earnings date to plan a sell, skip this dividend

                    intended_sell_date = min(valid_earnings_dates) - pd.DateOffset(days=days_before_earnings)
                    
                    # Check if the sell date is correct and in the price index
                    if intended_sell_date in prices.index and intended_sell_date > intended_buy_date:
                        buy_price = prices.loc[intended_buy_date, 'adjusted_close']

                        # Find a free pool to invest from
                        for i in range(5):
                            if free_capital_pools[i] > 0 and pool_availability[i]:  # Check pool availability
                                amount_to_invest = free_capital_pools[i]
                                active_investments[i][ticker] = amount_to_invest  # Start the investment
                                free_capital_pools[i] = 0  # Deduct free capital for this pool
                                pool_availability[i] = False  # Mark pool as in use
                                print(f"{date_str} - Pool {i}: Investing ${amount_to_invest:.2f} in {ticker}")

                                # Schedule the sale on the intended_sell_date for this pool
                                pending_sales[i] = {
                                    'ticker': ticker,
                                    'buy_date': intended_buy_date,
                                    'sell_date': intended_sell_date,
                                    'buy_price': buy_price
                                }
                                break  # Stop after finding a pool
                        else:
                            print(f"{date_str} - No free capital available to invest in {ticker} from any pool")

    return investment_results


def calculate_strategy_metrics(investment_results, start_date, end_date, initial_investment_per_pool=1000):
    total_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
    total_investment = initial_investment_per_pool * 5  # Assume 5 pools of $1000 each at the start
    final_value = 0
    invested_capital_days = 0
    uninvested_capital_days = 0
    running_invested = 0  # Track the amount of invested capital for each day

    # Loop through the investment data to calculate time in market and final value
    for date, data in investment_results.items():
        # Calculate the total invested capital on this date
        invested_on_date = sum([value for key, value in data.items() if "Free Capital" not in key])
        free_capital_on_date = sum([value for key, value in data.items() if "Free Capital" in key])
        
        # Track the total invested and uninvested capital for the day
        running_invested += invested_on_date
        invested_capital_days += invested_on_date
        uninvested_capital_days += free_capital_on_date

        final_value = invested_on_date + free_capital_on_date

    # Total capital tracked over time
    total_capital_tracked = invested_capital_days + uninvested_capital_days
    percent_time_in_market = (invested_capital_days / total_capital_tracked) * 100 if total_capital_tracked > 0 else 0
    overall_return = ((final_value - total_investment) / total_investment) * 100 if total_investment > 0 else 0
    annualized_return = ((final_value / total_investment) ** (365 / total_days) - 1) * 100 if total_days > 0 else 0

    return percent_time_in_market, overall_return, annualized_return

import pandas as pd
import matplotlib.pyplot as plt

def create_combined_plots(investment_results, start_date, end_date):
    # Convert the investment_results dictionary to a DataFrame
    df = pd.DataFrame(investment_results).T  # Transpose to get dates as rows
    
    # Initialize a DataFrame to store cleaned data
    cleaned_df = pd.DataFrame()
    
    # Sum the free capital across all pools into one column "Free Capital"
    cleaned_df["Free Capital"] = df.filter(like="Free Capital").sum(axis=1)

    # Rename columns to only show ticker names (e.g., 'KHC.US') and sum across pools
    for column in df.columns:
        if "Free Capital" in column:
            continue  # Already handled free capital, so skip these columns
        
        # Extract the ticker name (e.g., "KHC.US") from the column name
        ticker = column.split(" - ")[-1] if " - " in column else column
        if ticker not in cleaned_df:
            cleaned_df[ticker] = df[column].fillna(0)
        else:
            # Sum investments across pools for the same ticker
            cleaned_df[ticker] += df[column].fillna(0)

    # Use forward fill to propagate values for missing data (non-trading periods)
    cleaned_df.ffill(inplace=True)

    # Calculate strategy metrics
    percent_time_in_market, overall_return, annualized_return = calculate_strategy_metrics(
        investment_results, start_date, end_date
    )

    # Set up colors using the updated Matplotlib colormap API
    colormap = plt.colormaps['tab20']  # Get the colormap
    num_colors = len(cleaned_df.columns)
    colors = [colormap(i / num_colors) for i in range(num_colors)]

    # Create subplots for each ticker and free capital, plus one for the stacked chart
    num_columns = len(cleaned_df.columns)
    fig, axs = plt.subplots(num_columns + 1, 1, figsize=(12, (num_columns * 2) + 6), sharex=True)  # Doubled the height of the last plot

    # Plot each ticker and free capital in a separate subplot
    for i, column in enumerate(cleaned_df.columns):
        ax = axs[i]  # Get the specific subplot axis
        
        # Plot the single column (ticker or Free Capital)
        cleaned_df[column].plot(kind='area', stacked=False, ax=ax, color=colors[i])

        # Formatting the plot
        ax.set_title(f'Cumulative Value Over Time ({column})', fontsize=10)
        ax.set_ylabel('Capital Value ($)', fontsize=8)
        ax.grid(True)

    # Plot the stacked chart in the last subplot
    cleaned_df.plot(kind='area', stacked=True, ax=axs[-1], color=colors)

    # Formatting the stacked plot
    axs[-1].set_title('Cumulative Capital Over Time (Stacked)', fontsize=10)
    axs[-1].set_xlabel('Date', fontsize=10)
    axs[-1].set_ylabel('Total Value ($)', fontsize=8)
    axs[-1].grid(True)

    # Explicitly remove the legend
    axs[-1].get_legend().remove()

    # Rotate date labels for better visibility on the last subplot
    plt.setp(axs[-1].xaxis.get_majorticklabels(), rotation=45) 

    # Add metrics information at the top of the plot
    metrics_text = (
        f"% Time in Market: {percent_time_in_market:.2f}%\n"
        f"Overall Return: {overall_return:.2f}%\n"
        f"Annualized Return: {annualized_return:.2f}%"
    )
    fig.text(0.5, 0.96, metrics_text, ha='center', fontsize=12)  # Moved to the top

    plt.tight_layout(rect=[0, 0.1, 1, 0.95])  # Adjust layout to make room for the text and rotated labels
    return plt

