# %%
import sys
import io
from flask import Flask, render_template, request
import food_stock_strategy_simulation as fss
import pandas as pd
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    plot_available_dates_base64=None
    plot_top_stocks_base64=None
    plot_combined_base64=None
    output = None

    # Default values for the form fields
    api_key = "6669d7a6eb70f4.27564131"
    #tickers = "MSFT.US,AAPL.US,AMZN.US,CB.US,INTC.US,AMD.US" # note that TSLA doesn't have dividends
    #tickers = "NESN.SW,UL.US,MDLZ.US,CMG.US,KHC.US,GIS.US,HSY.US,SYY.US,KHC.US"
    tickers = "AAPL.US,MSFT.US,LLY.US,JPM.US,AVGO.US,UNH.US,V.US,PG.US,JNJ.US,NVDA.US,AMZN.US,GOOG.US,GOOGL.US,META.US"
    tickers = "AAPL.US"
    days_after_dividend = 0
    days_before_earnings = 0
    start_date = "2019-09-09"
    end_date = "2024-09-09"
    initial_investment = 1000

    if request.method == 'POST':
     #   try:
            print("Received POST request with the following data:")
            api_key = request.form.get('api_key')
            tickers = request.form.get('tickers').split(',')
            days_after_dividend = int(request.form.get('days_after_dividend'))
            days_before_earnings = int(request.form.get('days_before_earnings'))
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            initial_investment = float(request.form.get('initial_investment'))

            print(f"API Key: {api_key}")
            print(f"Tickers: {tickers}")
            print(f"Days After Dividend: {days_after_dividend}")
            print(f"Days Before Earnings: {days_before_earnings}")
            print(f"Start Date: {start_date}")
            print(f"End Date: {end_date}")
            print(f"Initial Investment: {initial_investment}")

            # Download data
            import download_info as di
            downloaded_data = di.download_data(api_key, tickers, start_date, end_date)

            # Create top stocks by date
            import food_stock_strategy_simulation as fss
            market_caps = fss.process_market_caps(downloaded_data)
            top_stocks_by_date = fss.create_top_stocks_by_date(market_caps, start_date, end_date, 5)

            # Redirect stdout to capture output
            old_stdout = sys.stdout
            captured_output = io.StringIO()  # Create a StringIO object
            sys.stdout = captured_output  # Redirect stdout to this StringIO object            

            # Process investment strategy
            investment_results = fss.process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment)

            # Get the captured output and make it ready for rendering
            output = captured_output.getvalue()
            captured_output.close()
            sys.stdout = old_stdout  # Reset redirect

            # Generate the plots
            import chart_available_dates as cad
            plot_available_dates_base64 = cad.plot_stock_date_ranges(downloaded_data)
            import chart_top_stocks as cts
            plot_top_stocks_base64 = cts.chart_top_stocks(top_stocks_by_date)
            import chart_combined as cc
            plot_combined_base64 = cc.chart_combined(investment_results, start_date, end_date)

            # Convert tickers list back to a comma-separated string
            tickers = ",".join(tickers)

     #   except Exception as e:
     #       print(f"Error processing POST request: {e}")
     #       output = f"Error processing your request: {e}"


    # Render the form with current values (retains input after submission)
    return render_template('index.html',
                           plot_available_dates_base64=plot_available_dates_base64,
                           plot_top_stocks_base64=plot_top_stocks_base64,
                           plot_combined_base64=plot_combined_base64,
                           output=output,
                           api_key=api_key,
                           tickers=tickers,
                           days_after_dividend=days_after_dividend,
                           days_before_earnings=days_before_earnings,
                           start_date=start_date,
                           end_date=end_date,
                           initial_investment=initial_investment)


if __name__ == '__main__':
    app.run(debug=True)  # Start the server with debugging enabled
