from io import BytesIO
import base64
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


import matplotlib.dates as mdates

def chart_free_capital_errors(free_capital_errors, start_date, end_date):
    """
    Creates a chart visualizing the 'no free capital' errors by ticker and date.
    
    Args:
        free_capital_errors (list of tuples): A list of tuples containing (Ticker, Date) for each "no free capital" error.
        start_date (str): The start date of the simulation.
        end_date (str): The end date of the simulation.

    Returns:
        str: Base64 encoded string of the generated chart image.
    """
    # Check if there are any errors to plot
    if len(free_capital_errors) == 0:
        return None

    # Create a DataFrame from the list of errors
    df_errors = pd.DataFrame(free_capital_errors, columns=['Ticker', 'Date'])
    df_errors['Date'] = pd.to_datetime(df_errors['Date'])

    # Group by both Ticker and Date to count the number of errors per ticker on each date
    error_counts_by_ticker_date = df_errors.groupby(['Date', 'Ticker']).size().unstack(fill_value=0)

    # Ensure we reindex to match the full date range from start to end
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    error_counts_by_ticker_date = error_counts_by_ticker_date.reindex(full_date_range, fill_value=0)

    # Set up the colormap
    colormap = plt.colormaps['tab20']
    tickers = error_counts_by_ticker_date.columns

    # Create the figure and plot
    fig, ax_errors = plt.subplots(figsize=(12, 3))

    # Plot the error counts for each ticker
    for idx, ticker in enumerate(tickers):
        ax_errors.scatter(error_counts_by_ticker_date.index,
                          [idx] * len(error_counts_by_ticker_date.index),
                          s=error_counts_by_ticker_date[ticker] * 100,  # Bubble size proportional to error count
                          label=ticker, color=colormap(idx / len(tickers)))

    # Set title and labels for the plot
    ax_errors.set_title("Free Capital Errors Over Time (by Ticker)", fontsize=10)
    ax_errors.set_xlabel('Date', fontsize=10)
    ax_errors.set_ylabel('Ticker', fontsize=10)
    ax_errors.grid(True)
    ax_errors.set_yticks(range(len(tickers)))
    ax_errors.set_yticklabels(tickers)

    # Set the date format explicitly to avoid issues
    ax_errors.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax_errors.xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # Change to MonthLocator or WeekLocator as needed

    # Rotate date labels for better visibility
    plt.setp(ax_errors.xaxis.get_majorticklabels(), rotation=45)

    # Adjust the layout
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    # Convert plot to base64 string
    return base64.b64encode(buf.getvalue()).decode("utf-8")



def chart_combined(investment_results, metrics):
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
        f"% Time in Market: {metrics['percent_time_in_market']:.2f}%\n"
        f"Overall Return: {metrics['overall_return']:.2f}%\n"
        f"Annualized Return: {metrics['annualized_return']:.2f}%"
    )
    fig.text(0.5, 0.96, metrics_text, ha='center', fontsize=12)  # Moved to the top

    plt.tight_layout(rect=[0, 0.1, 1, 0.95])  # Adjust layout to make room for the text and rotated labels
    
    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    # Convert plot to base64 string
    return base64.b64encode(buf.getvalue()).decode("utf-8")