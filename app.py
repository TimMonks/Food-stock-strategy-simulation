# %%
import sys
import io
from flask import Flask, render_template, request, redirect, url_for
import food_stock_strategy_simulation as fss
import pandas as pd
from io import BytesIO
import base64
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
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

            downloaded_data,market_caps = fss.download_data(api_key, tickers, start_date, end_date)

            top_stocks_by_date= fss.create_top_stocks_by_date(market_caps, start_date, end_date, 5)
            
            # Redirect stdout to capture output
            old_stdout = sys.stdout
            captured_output = io.StringIO()  # Create a StringIO object
            sys.stdout = captured_output  # Redirect stdout to this StringIO object            

            investment_results = fss.process(downloaded_data, top_stocks_by_date, days_after_dividend, days_before_earnings, initial_investment)

            # Get the captured output and make it ready for rendering
            output = captured_output.getvalue()
            captured_output.close()
            sys.stdout = old_stdout  # Reset redirect

            # Assuming investment_results is populated, and start_date and end_date are defined
            plot = fss.create_combined_plots(investment_results, start_date, end_date)

            # Save the plot to a BytesIO object
            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            # Convert plot to base64 string
            plot_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            return render_template('index.html', plot=plot_base64, output=output)
        
        except Exception as e:
            print(f"Error processing POST request: {e}")
            result = "Error processing your request."

        return render_template('index.html', plot=result)
    else:
        # GET request to show the form
        return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=True)  # Start the server with debugging enabled
