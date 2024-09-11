# %%
# Block 2: Data Retrieval

import requests
import io
import pandas as pd

import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend like 'Agg' (for PNGs)

pd.set_option('display.max_rows', 20)  

def process_market_caps(downloaded_data):
    market_caps_data = {}

    # Loop through each ticker in downloaded_data
    for ticker, data in downloaded_data.items():
        market_cap_status = data.get('market_cap_status')  # Get the market cap status code

        # Check if the response was successful (status code 200)
        if market_cap_status == 200:
            market_caps = data.get('market_cap')  # Access the market cap DataFrame for the ticker
            
            if not market_caps.empty:
                # Ensure the DataFrame contains only the market cap with the correct format
                market_caps = market_caps[['value']].copy()  # Use 'value' column
                market_caps.columns = ['value']  # Ensure column is named 'value'
                
                # Make sure the index is date and the data is in the correct format
                market_caps.index = pd.to_datetime(market_caps.index)
                market_caps.sort_index(inplace=True)

                # Store the properly formatted DataFrame in the dictionary
                market_caps_data[ticker] = market_caps
            else:
                # Diagnostic message if no data
                print(f"No market cap data to process for {ticker}. Empty DataFrame returned.")
                market_caps_data[ticker] = pd.DataFrame()  # Empty DataFrame if no data
        else:
            # Diagnostic message if the status code indicates an error
            print(f"Failed to fetch market cap data for {ticker}. Status code: {market_cap_status}")
            market_caps_data[ticker] = pd.DataFrame()  # Empty DataFrame if fetch failed

    return market_caps_data




def process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment_per_pool):
    free_capital_pools = [initial_investment_per_pool] * 5
    active_investments = {i: {} for i in range(5)}
    pending_sales = {i: {} for i in range(5)}
    pool_availability = [True] * 5
    investment_results = {}
    no_free_capital_errors = []  # List to store tickers and dates of "no free capital" errors

    for date, top_stocks_row in top_stocks_by_date.iterrows():
        current_top_stocks = top_stocks_row['Stock']
        date_str = date.strftime('%Y-%m-%d')
        investment_results[date_str] = {}

        # Print diagnostics for the start of each day
        for i in range(5):
            investment_results[date_str][f"Pool {i} Free Capital"] = free_capital_pools[i]
            if active_investments[i]:
                for ticker, investment_value in active_investments[i].items():
                    investment_results[date_str][f"Pool {i} - {ticker}"] = investment_value

        # Process sales for the day
        for i in range(5):
            if pending_sales[i] and pending_sales[i]['sell_date'] == date:
                prices = downloaded_data[pending_sales[i]['ticker']]['prices']
                sell_price = prices.loc[date, 'adjusted_close']
                buy_price = pending_sales[i]['buy_price']
                investment_gain = (sell_price / buy_price - 1) * active_investments[i][pending_sales[i]['ticker']]
                total_return = active_investments[i][pending_sales[i]['ticker']] + investment_gain
                print(f"{date_str}: Sold: {pending_sales[i]['ticker']}, Pool: {i}, Gain: ${investment_gain:.2f}, Total Return: ${total_return:.2f}")
                free_capital_pools[i] += total_return
                active_investments[i].pop(pending_sales[i]['ticker'])
                pending_sales[i] = {}
                pool_availability[i] = True

        # Process possible buys for the day
        for ticker, data in downloaded_data.items():
            if ticker not in current_top_stocks:
                continue

            prices = data['prices']
            dividends = data['dividends']
            earnings_dates = [pd.Timestamp(d) for d in data['earnings_dates']]

            for ex_dividend_date in dividends:
                ex_dividend_date = pd.Timestamp(ex_dividend_date)
                intended_buy_date = ex_dividend_date + pd.DateOffset(days=days_after_dividend)
                if intended_buy_date == date:
                    valid_earnings_dates = [ed for ed in earnings_dates if ed > intended_buy_date]
                    if not valid_earnings_dates:
                        continue
                    intended_sell_date = min(valid_earnings_dates) - pd.DateOffset(days=days_before_earnings)
                    if intended_sell_date in prices.index:
                        buy_price = prices.loc[intended_buy_date, 'adjusted_close']
                        bought = False  # Track if any pool successfully buys
                        for i in range(5):
                            if free_capital_pools[i] > 0 and pool_availability[i]:
                                amount_to_invest = free_capital_pools[i]
                                active_investments[i][ticker] = amount_to_invest
                                free_capital_pools[i] = 0
                                pool_availability[i] = False
                                print(f"{date_str}: Bought: {ticker}, Pool: {i}, Investment: ${amount_to_invest:.2f}")
                                pending_sales[i] = {'ticker': ticker, 'buy_date': intended_buy_date, 'sell_date': intended_sell_date, 'buy_price': buy_price}
                                bought = True
                                break
                        if not bought:
                            print(f"*** No free capital for {ticker} on {date_str}")
                            no_free_capital_errors.append((ticker, date_str))  # Log the no free capital error

    return investment_results, no_free_capital_errors  # Return the results and the list of no free capital errors




