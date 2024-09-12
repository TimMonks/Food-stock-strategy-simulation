# %%
# Block 2: Data Retrieval

import requests
import io
import pandas as pd

import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend like 'Agg' (for PNGs)

pd.set_option('display.max_rows', 20)  

def calculate_strategy_metrics(investment_results, start_date, end_date, total_investment):
    total_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
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


    metrics = {}
    metrics['total_capital_tracked'] = invested_capital_days + uninvested_capital_days
    metrics['percent_time_in_market'] = (invested_capital_days / metrics['total_capital_tracked']) * 100 if metrics['total_capital_tracked'] > 0 else 0
    metrics['overall_return'] = ((final_value - total_investment) / total_investment) * 100 if total_investment > 0 else 0
    metrics['annualized_return'] = ((final_value / total_investment) ** (365 / total_days) - 1) * 100 if total_days > 0 else 0

    return metrics


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


def remove_tickers_without_dividends(downloaded_data):
    """
    Removes tickers from the downloaded_data dictionary that do not have any dividend data.
    
    Parameters:
    - downloaded_data (dict): The dictionary containing the downloaded stock data.
    
    Returns:
    - dict: The updated downloaded_data dictionary with tickers without dividends removed.
    """
    tickers_to_remove = []

    # Check each ticker for dividend data
    for ticker, data in downloaded_data.items():
        dividends = data.get('dividends', [])
        if not dividends:  # If the dividend list is empty or None
            print(f"Removing {ticker} because it has no dividend data.")
            tickers_to_remove.append(ticker)

    # Remove tickers without dividends from the downloaded_data dictionary
    for ticker in tickers_to_remove:
        del downloaded_data[ticker]

    return downloaded_data

def process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment, num_pools):
    # Initialize pools and their states based on the number of pools
    free_capital_pools = [initial_investment/num_pools] * num_pools
    active_investments = {i: {} for i in range(num_pools)}
    pending_sales = {i: {} for i in range(num_pools)}
    pool_availability = [True] * num_pools
    investment_results = {}
    free_capital_errors = []  # List to store tickers and dates of "no free capital" errors

    # Generate a full date range (including non-trading days)
    full_date_range = pd.date_range(start=top_stocks_by_date.index.min(), end=top_stocks_by_date.index.max(), freq='D')

    # Forward-fill price data for each stock across all dates
    for ticker, data in downloaded_data.items():
        data['prices'] = data['prices'].reindex(full_date_range).ffill()

    # Iterate over each date in the full range (including non-trading days)
    for date in full_date_range:
        date_str = date.strftime('%Y-%m-%d')
        investment_results[date_str] = {}

        # Print diagnostics for the start of each day (per pool)
        for i in range(num_pools):
            investment_results[date_str][f"Pool {i} Free Capital"] = free_capital_pools[i]

            if active_investments[i]:
                for ticker, investment_value in active_investments[i].items():
                    # Use the last valid price (forward-filled) for non-trading days
                    current_price = downloaded_data[ticker]['prices'].loc[date, 'adjusted_close']
                    current_investment_value = (investment_value / pending_sales[i]['buy_price']) * current_price
                    investment_results[date_str][f"Pool {i} - {ticker}"] = current_investment_value

        # Process sales for the day (if any pending sales are due)
        for i in range(num_pools):
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

        # Check if it's a valid trading day and process possible buys
        if date in top_stocks_by_date.index:
            current_top_stocks = top_stocks_by_date.loc[date, 'Stock']

            for ticker, data in downloaded_data.items():
                if ticker not in current_top_stocks:
                    continue  # Skip stocks that are not in the top list for the current date

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
                            for i in range(num_pools):
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
                                free_capital_errors.append((ticker, date_str))  # Log the no free capital error

    return investment_results, free_capital_errors  # Return the results and the list of no free capital errors


def calculate_returns(downloaded_data, start_date, end_date, top_stocks_by_date, num_stocks):
    """
    Calculate returns based on investing in the top 'n' stocks from the first valid date.
    Args:
        downloaded_data (dict): Dictionary containing the stock data.
        start_date (str): The start date of the period.
        end_date (str): The end date of the period.
        top_stocks_by_date (pd.DataFrame): DataFrame containing top stocks by date.
        n (int): Number of top stocks to consider for return calculation.
    Returns:
        tuple: (returns_data, avg_percent_return, avg_annual_return, first_valid_date, last_valid_date)
    """
    start_date_ts = pd.to_datetime(start_date)
    end_date_ts = pd.to_datetime(end_date)

    first_valid_date = None
    last_valid_date = None

    # Helper function to check if all stocks have valid price data for a given date
    def has_valid_data_on_date(ticker, date):
        data = downloaded_data.get(ticker)
        if data is None or data['prices'].empty:
            return False
        prices = data['prices']
        return pd.Timestamp(date) in pd.to_datetime(prices.index)

    # Loop through the dates to find the first valid date where all 'n' stocks have data
    for date in top_stocks_by_date.index:
        top_stocks = top_stocks_by_date.loc[date, 'Stock'][:num_stocks]  # Select the top 'n' stocks
        
        # Ensure there are exactly 'n' tickers on this date
        if len(top_stocks) != num_stocks:
            continue

        all_stocks_have_data = all(has_valid_data_on_date(ticker, date) for ticker in top_stocks)

        # Set the first valid date if all selected stocks have data
        if all_stocks_have_data:
            first_valid_date = date
            break

    # If no valid date is found, return with no data
    if not first_valid_date:
        print("No valid date where all top 'n' stocks have data.")
        return [], None, None, None, None

    # Now calculate the last valid date where all selected stocks have data
    for date in reversed(top_stocks_by_date.index):
        top_stocks = top_stocks_by_date.loc[date, 'Stock'][:num_stocks]

        # Ensure there are exactly 'n' tickers on this date
        if len(top_stocks) != num_stocks:
            continue

        all_stocks_have_data = all(has_valid_data_on_date(ticker, date) for ticker in top_stocks)

        if all_stocks_have_data:
            last_valid_date = date
            break

    returns_data = []
    total_percent_return = 0
    total_annual_return = 0
    valid_tickers_count = 0
    total_days = (last_valid_date - first_valid_date).days  # Recalculate total days based on actual valid dates

    for ticker in top_stocks_by_date.loc[first_valid_date, 'Stock'][:num_stocks]:
        data = downloaded_data.get(ticker)
        prices = data['prices'] if data else pd.DataFrame()

        if not prices.empty and first_valid_date in prices.index and last_valid_date in prices.index:
            start_price = prices.loc[first_valid_date, 'adjusted_close']
            end_price = prices.loc[last_valid_date, 'adjusted_close']

            percent_return = ((end_price - start_price) / start_price) * 100

            # Calculate effective annual return (EAR)
            if total_days > 0:
                annual_return = ((end_price / start_price) ** (365 / total_days) - 1) * 100
            else:
                annual_return = None

            # Track total returns for average calculation
            total_percent_return += percent_return
            if annual_return is not None:
                total_annual_return += annual_return
            valid_tickers_count += 1

            returns_data.append({
                'ticker': ticker,
                'start_price': start_price,
                'end_price': end_price,
                'percent_return': percent_return,
                'annual_return': annual_return
            })

    # Calculate the average returns assuming equal investment in all top 'n' stocks
    if valid_tickers_count > 0:
        avg_percent_return = total_percent_return / valid_tickers_count
        avg_annual_return = total_annual_return / valid_tickers_count if total_days > 0 else None
    else:
        avg_percent_return = None
        avg_annual_return = None

    return returns_data, avg_percent_return, avg_annual_return, first_valid_date, last_valid_date
