from io import BytesIO
import base64
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


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

def chart_top_stocks(top_stocks_by_date):
    # "Explode" the DataFrame, splitting the lists in each row into separate rows
    df = top_stocks_by_date.explode('Stock')

    # Get unique stocks and dynamically set the figure height based on the number of stocks
    unique_stocks = df['Stock'].unique()
    num_stocks = len(unique_stocks)
    height = max(3, num_stocks * 0.25)  # Set a minimum height of 4, scaling with the number of stocks

    fig, ax = plt.subplots(figsize=(10, height))  # Width remains 14, height is dynamic

    # Assign each stock a unique offset on the y-axis
    stock_offsets = {stock: i for i, stock in enumerate(unique_stocks, 1)}

    for stock in unique_stocks:
        stock_data = df[df['Stock'] == stock]
        # Apply an offset to each stock to separate them vertically, only show markers
        ax.plot(stock_data.index, np.repeat(stock_offsets[stock], len(stock_data)), label=stock, marker='o', linestyle='')

    # Formatting the plot
    ax.set_title('Top Stocks Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Presence with Offset')
    ax.set_yticks(list(stock_offsets.values()))  # Set y-ticks to the assigned offsets
    ax.set_yticklabels(list(stock_offsets.keys()))  # Label y-ticks with stock names

    # Remove legend from the plot and adjust layout
    plt.legend(title='Stocks', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    # Convert plot to base64 string
    return base64.b64encode(buf.getvalue()).decode("utf-8")
