from flask import Flask, render_template, request, Response, stream_with_context
import process as fss
import pandas as pd
import base64
import matplotlib.pyplot as plt
import sys
import io

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    # Default values for the form fields
    api_key = "6669d7a6eb70f4.27564131"
    tickers = "AAPL.US,MSFT.US"
    days_after_dividend = 0
    days_before_earnings = 0
    start_date = "2019-09-09"
    end_date = "2024-09-09"
    initial_investment = 1000

    return render_template('index.html',
                           api_key=api_key,
                           tickers=tickers,
                           days_after_dividend=days_after_dividend,
                           days_before_earnings=days_before_earnings,
                           start_date=start_date,
                           end_date=end_date,
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

    return Response(stream_process(api_key, tickers, days_after_dividend, days_before_earnings, start_date, end_date, initial_investment),
                    content_type='text/html')


@stream_with_context
def stream_process(api_key, tickers, days_after_dividend, days_before_earnings, start_date, end_date, initial_investment):
    yield "Received input data...<br>\n"
    yield f"Tickers: {tickers}<br>\n"

    # Download data
    yield "Downloading data...<br>\n"
    import download_info as di
    tickers_list = tickers.split(',')
    downloaded_data = di.download_data(api_key, tickers_list, start_date, end_date)
    yield "Data downloaded.<br>\n"

    # First chart (stock date ranges)
    import chart_available_dates as cad
    plot_available_dates_base64 = cad.plot_stock_date_ranges(downloaded_data)
    yield f" "  # Flush the stream
    yield f'<img src="data:image/png;base64,{plot_available_dates_base64}"><br>\n'
    
    # Process market cap data
    yield "Processing market cap data...<br>\n"
    market_caps = fss.process_market_caps(downloaded_data)
    top_stocks_by_date = fss.create_top_stocks_by_date(market_caps, start_date, end_date, 5)
    yield "Market cap processing complete.<br>\n"

    # Second chart (top stocks over time)
    import chart_top_stocks as cts
    plot_top_stocks_base64 = cts.chart_top_stocks(top_stocks_by_date)
    yield f" "  # Flush the stream
    yield f'<img src="data:image/png;base64,{plot_top_stocks_base64}"><br>\n'

    # Redirect stdout to capture output
    old_stdout = sys.stdout
    captured_output = io.StringIO()  # Create a StringIO object
    sys.stdout = captured_output  # Redirect stdout to this StringIO object            

    # Process investment strategy
    yield "Processing investment strategy...<br>\n"
    investment_results = fss.process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment)
    yield "Investment strategy processed.<br>\n"

    # Get the captured output and make it ready for rendering
    output = captured_output.getvalue()
    captured_output.close()
    sys.stdout = old_stdout  # Reset redirect

    # Third chart (combined investment results)
    import chart_combined as cc
    try:
        plot_combined_base64 = cc.chart_combined(investment_results, start_date, end_date)
        yield f" "  # Flush the stream
        yield f'<img src="data:image/png;base64,{plot_combined_base64}"><br>\n'
    except Exception as e:
        yield f"Error generating third chart: {str(e)}<br>\n"

    yield f"<pre>{output}</pre>"

    yield "Simulation complete!<br>\n"


if __name__ == '__main__':
    app.run(debug=True)
