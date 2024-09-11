from io import BytesIO
import base64
import pandas as pd
import matplotlib.pyplot as plt


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

import matplotlib.gridspec as gridspec

def chart_combined(investment_results, no_free_capital_errors, start_date, end_date):
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

    # Create a gridspec layout for subplots
    total_subplots = len(cleaned_df.columns) + 1
    if len(no_free_capital_errors) > 0:
        total_subplots += 1  # Extra subplot for the error chart

    fig = plt.figure(figsize=(12, (total_subplots * 3) + 10))
    gs = gridspec.GridSpec(total_subplots, 1, height_ratios=[1] * len(cleaned_df.columns) + [2, 1])

    axs = []

    # Plot each ticker and free capital in a separate subplot
    for i, column in enumerate(cleaned_df.columns):
        ax = fig.add_subplot(gs[i, 0])
        cleaned_df[column].plot(kind='area', stacked=False, ax=ax, color=colors[i])

        # Formatting the plot
        ax.set_title(f'Cumulative Value Over Time ({column})', fontsize=10)
        ax.set_ylabel('Capital Value ($)', fontsize=8)
        ax.grid(True)
        axs.append(ax)

    # Plot the stacked chart
    ax_stacked = fig.add_subplot(gs[-2, 0], sharex=axs[0])
    cleaned_df.plot(kind='area', stacked=True, ax=ax_stacked, color=colors)
    ax_stacked.set_title('Cumulative Capital Over Time (Stacked)', fontsize=10)
    ax_stacked.set_ylabel('Total Value ($)', fontsize=8)
    ax_stacked.grid(True)
    axs.append(ax_stacked)

    # Explicitly remove the legend from the stacked plot
    ax_stacked.get_legend().remove()

    # Rotate date labels for better visibility on the stacked chart
    plt.setp(ax_stacked.xaxis.get_majorticklabels(), rotation=45)

    # Plot the "No Free Capital Errors" chart only if there are errors
    if len(no_free_capital_errors) > 0:
        ax_errors = fig.add_subplot(gs[-1, 0], sharex=axs[0])

        df_errors = pd.DataFrame(no_free_capital_errors, columns=['Ticker', 'Date'])
        df_errors['Date'] = pd.to_datetime(df_errors['Date'])

        # Group by both Ticker and Date to count the number of errors per ticker on each date
        error_counts_by_ticker_date = df_errors.groupby(['Date', 'Ticker']).size().unstack(fill_value=0)

        # Ensure we reindex to match the full date range used by the other plots
        error_counts_by_ticker_date = error_counts_by_ticker_date.reindex(cleaned_df.index, fill_value=0)

        # Plot the error counts over time in the last subplot for each ticker
        tickers = error_counts_by_ticker_date.columns
        for idx, ticker in enumerate(tickers):
            ax_errors.fill_between(error_counts_by_ticker_date.index,
                                0, error_counts_by_ticker_date[ticker],
                                label=ticker, step='mid', color=colormap(idx / len(tickers)))

        ax_errors.set_title("Free Capital Errors Over Time (by Ticker)", fontsize=10)
        ax_errors.set_ylabel("Error Count", fontsize=8)
        ax_errors.grid(True)
        ax_errors.set_ylim(bottom=0)  # Ensure y-axis starts at 0
        ax_errors.set_xlabel('Date', fontsize=10)
        ax_errors.legend(loc="upper left")  # Optional: add a legend if desired

        # Rotate date labels for better visibility
        plt.setp(ax_errors.xaxis.get_majorticklabels(), rotation=45)

    # Add metrics information at the top of the plot
    metrics_text = (
        f"% Time in Market: {percent_time_in_market:.2f}%\n"
        f"Overall Return: {overall_return:.2f}%\n"
        f"Annualized Return: {annualized_return:.2f}%"
    )
    fig.text(0.5, 0.96, metrics_text, ha='center', fontsize=12)

    plt.tight_layout(rect=[0, 0.1, 1, 0.95])

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)

    # Convert plot to base64 string
    return base64.b64encode(buf.getvalue()).decode("utf-8")
