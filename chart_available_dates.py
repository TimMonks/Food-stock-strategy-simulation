from io import BytesIO
import base64
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# Function to plot date ranges for each stock, showing dividends, earnings, and prices with markers
def plot_stock_date_ranges(downloaded_data):

    # Scale the height of the plot based on the number of tickers
    num_tickers = len(downloaded_data)
    height = max(3, num_tickers * 0.6)  # Set a minimum height of 3, scale with tickers

    fig, ax = plt.subplots(figsize=(10, height))  # Width remains 10, height is scaled

    # Set a color scheme for the different data types
    colors = {'prices': 'tab:blue', 'dividends': 'tab:green', 'earnings': 'tab:orange'}
    markers = {'dividends': 'o', 'earnings': 's'}  # Circle for dividends, square for earnings

    # Adjust vertical spacing between rows (each stock)
    y_pos = num_tickers
    
    for ticker, data in downloaded_data.items():
        # Extract and convert price, dividend, and earnings date ranges
        price_range = (pd.Timestamp(data['prices'].index.min()).to_pydatetime(), 
                       pd.Timestamp(data['prices'].index.max()).to_pydatetime())
        
        # Convert dividend dates to Timestamps if they aren't already
        dividend_dates = [pd.Timestamp(d) for d in data['dividends']]
        dividend_range = (min(dividend_dates).to_pydatetime(), max(dividend_dates).to_pydatetime()) if dividend_dates else (None, None)
        
        # Convert earnings dates to Timestamps if they aren't already
        earnings_dates = [pd.Timestamp(e) for e in data['earnings_dates']]
        earnings_range = (min(earnings_dates).to_pydatetime(), max(earnings_dates).to_pydatetime()) if earnings_dates else (None, None)
        
        # Plot price range
        ax.plot(price_range, [y_pos, y_pos], color=colors['prices'], label='Prices' if y_pos == num_tickers else "")

        # Plot dividend range (if exists) and markers for dividends
        if dividend_range[0] is not None and dividend_range[1] is not None:
            ax.plot(dividend_range, [y_pos - 0.2, y_pos - 0.2], color=colors['dividends'], label='Dividends' if y_pos == num_tickers else "")
            # Add markers for dividend dates
            ax.scatter(dividend_dates, [y_pos - 0.2] * len(dividend_dates), color=colors['dividends'], marker=markers['dividends'], label='' if y_pos < num_tickers else 'Dividend markers')

        # Plot earnings range (if exists) and markers for earnings
        if earnings_range[0] is not None and earnings_range[1] is not None:
            ax.plot(earnings_range, [y_pos - 0.4, y_pos - 0.4], color=colors['earnings'], label='Earnings' if y_pos == num_tickers else "")
            # Add markers for earnings dates
            ax.scatter(earnings_dates, [y_pos - 0.4] * len(earnings_dates), color=colors['earnings'], marker=markers['earnings'], label='' if y_pos < num_tickers else 'Earnings markers')

        # Label each stock on the y-axis
        ax.text(price_range[0], y_pos, ticker, va='center', ha='right', fontsize=10)
        
        # Move to the next y position
        y_pos -= 1

    # Set title and labels
    ax.set_title('Date Ranges for Prices, Dividends, and Earnings for Each Stock')
    ax.set_xlabel('Date')
    ax.set_yticks([])  # Remove y-ticks
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.legend(loc='upper right')

    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    # Convert plot to base64 string
    return base64.b64encode(buf.getvalue()).decode("utf-8")
