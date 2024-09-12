from flask import Flask, render_template, request, Response, stream_with_context
import process as fss
import pandas as pd
import base64
import matplotlib.pyplot as plt
import sys
import io

import download_info as di
import top_stocks as ts
import process as p
import chart_combined as cc
import chart_available_dates as cad

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    # Default values for the form fields
    api_key = "6669d7a6eb70f4.27564131"
    tickers = "AAPL.US,MSFT.US,NVDA.US,AMZN.US,META.US,GOOGL.US,GOOG.US,LLY.US,JPM.US,BRK-B.US,V.US,PG.US,UNH.US,AVGO.US,JNJ.US"
    days_after_dividend = 0
    days_before_earnings = 0
    start_date = "2019-09-09"
    end_date = "2024-09-09"
    initial_investment = 1000
    num_pools = 10
    num_stocks = 10

    return render_template('index.html',
                           api_key=api_key,
                           tickers=tickers,
                           days_after_dividend=days_after_dividend,
                           days_before_earnings=days_before_earnings,
                           start_date=start_date,
                           end_date=end_date,
                           num_pools=num_pools,
                           num_stocks=num_stocks,
                           initial_investment=initial_investment)


@app.route('/process', methods=['POST'])
def process():
    api_key = request.form.get('api_key')
    tickers = request.form.get('tickers')
    days_after_dividend = int(request.form.get('days_after_dividend'))
    days_before_earnings = int(request.form.get('days_before_earnings'))
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    initial_investment = float(request.form.get('initial_investment'))
    num_pools = int(request.form.get('num_pools'))
    num_stocks = int(request.form.get('num_stocks'))

    return Response(stream_process(api_key, tickers, days_after_dividend, days_before_earnings, start_date, end_date, initial_investment, num_pools, num_stocks),
                    content_type='text/html')


@stream_with_context
def stream_process(api_key, tickers, days_after_dividend, days_before_earnings, start_date, end_date, initial_investment, num_pools, num_stocks):
    yield "Received input data...<br>\n"
    yield f"Tickers: {tickers}<br>\n"

    # Download data
    yield "Downloading data...<br>\n"
    tickers_list = tickers.split(',')
    downloaded_data = di.download_data(api_key, tickers_list, start_date, end_date)
    yield "Data downloaded.<br>\n"

    # Remove tickers without dividends
    yield "Removing tickers without dividends.<br>\n"
    downloaded_data = p.remove_tickers_without_dividends(downloaded_data)
    plot_available_dates_base64 = cad.plot_stock_date_ranges(downloaded_data)
    yield f" "  # Flush the stream
    yield f'<img src="data:image/png;base64,{plot_available_dates_base64}"><br>\n'

    # Process market cap data
    yield "Processing market cap data...<br>\n"
    market_caps = p.process_market_caps(downloaded_data)
    top_stocks_by_date = ts.create_top_stocks_by_date(market_caps, start_date, end_date, num_stocks)
    yield "Market cap processing complete.<br>\n"

    # Second chart (top stocks over time)
    plot_top_stocks_base64 = ts.chart_top_stocks(top_stocks_by_date)
    yield f" "  # Flush the stream
    yield f'<img src="data:image/png;base64,{plot_top_stocks_base64}"><br>\n'

    # Calculate returns for each ticker
    yield "Calculating returns for each ticker...<br>\n"
    returns_data, avg_percent_return, avg_annual_return, first_valid_date, last_valid_date = p.calculate_returns(downloaded_data, start_date, end_date, top_stocks_by_date, num_stocks)

    yield f"First valid date: {first_valid_date} last valid date: {last_valid_date}<br>\n"

    # Prepare the table structure for individual stock returns
    yield "<table border='1' style='border-collapse: collapse; text-align: center;'>"
    yield "<tr><th>Ticker</th><th>Start Price</th><th>End Price</th><th>% Return</th><th>Effective Annual Return</th></tr>"

    for item in returns_data:
        ticker = item['ticker']
        start_price = item['start_price']
        end_price = item['end_price']
        percent_return = item['percent_return']
        annual_return = item['annual_return']
        
        yield "<tr>"
        yield f"<td>{ticker}</td>"
        yield f"<td>{start_price:.2f}</td>" if start_price is not None else "<td>N/A</td>"
        yield f"<td>{end_price:.2f}</td>" if end_price is not None else "<td>N/A</td>"
        yield f"<td>{percent_return:.2f}%</td>" if percent_return is not None else "<td>N/A</td>"
        yield f"<td>{annual_return:.2f}%</td>" if annual_return is not None else "<td>N/A</td>"
        yield "</tr>"

    # Add row for average returns
    yield "<tr style='font-weight: bold; background-color: #f0f0f0;'>"
    yield "<td colspan='3'>Average</td>"
    yield f"<td>{avg_percent_return:.2f}%</td>" if avg_percent_return is not None else "<td>N/A</td>"
    yield f"<td>{avg_annual_return:.2f}%</td>" if avg_annual_return is not None else "<td>N/A</td>"
    yield "</tr>"
    yield "</table>"


    # Redirect stdout to capture output
    old_stdout = sys.stdout
    captured_output = io.StringIO()  # Create a StringIO object
    sys.stdout = captured_output  # Redirect stdout to this StringIO object            

    # Process investment strategy
    yield "Processing investment strategy...<br>\n"
    investment_results, free_capital_errors = p.process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment, num_pools)
    yield "Investment strategy processed.<br>\n"

    # Get the captured output and make it ready for rendering
    output = captured_output.getvalue()
    captured_output.close()
    sys.stdout = old_stdout  # Reset redirect

    # Calculate the strategy's overall return and annualized return
    metrics = p.calculate_strategy_metrics(investment_results, start_date, end_date, initial_investment)

    plot_free_capital_errors_base64 = cc.chart_free_capital_errors(free_capital_errors, start_date, end_date)
    if plot_free_capital_errors_base64:
        yield f" "  # Flush the stream
        yield f'<img src="data:image/png;base64,{plot_free_capital_errors_base64}" alt="No Free Capital Errors Chart"><br>\n'
    else:
        yield "No free capital errors to display.<br>"


    # Compare strategy return vs. average returns
    yield "<h2>Comparison: Strategy vs. Average Stock Returns</h2>"
    if metrics['overall_return'] > avg_percent_return:
        yield f"<p style='color:green;'>The strategy outperformed the average stock return! 🎉</p>"
    else:
        yield f"<p style='color:red;'>The strategy underperformed the average stock return. 😞</p>"

    # Display the comparison table
    yield "<table border='1' style='border-collapse: collapse;'>"
    yield "<tr><th>Metric</th><th>Average Stock Return</th><th>Strategy Return</th></tr>"
    yield f"<tr><td>% Return</td><td>{avg_percent_return:.2f}%</td><td>{metrics['overall_return']:.2f}%</td></tr>"
    yield f"<tr><td>Effective Annual Return</td><td>{avg_annual_return:.2f}%</td><td>{metrics['annualized_return']:.2f}%</td></tr>"
    yield "</table>"


    # Third chart (combined investment results)
    try:
        plot_combined_base64 = cc.chart_combined(investment_results, metrics)
        yield f" "  # Flush the stream
        yield f'<img src="data:image/png;base64,{plot_combined_base64}"><br>\n'
    except Exception as e:
        yield f"Error generating third chart: {str(e)}<br>\n"

    yield f"<pre>{output}</pre>"

    yield "Simulation complete!<br>\n"


if __name__ == '__main__':
    app.run(debug=True)
