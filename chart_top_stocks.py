from io import BytesIO
import base64
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

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
