# %%
import sys
import io
from flask import Flask, render_template, request, redirect, url_for
import food_stock_strategy_simulation as fss
import pandas as pd

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

            downloaded_data = fss.download_data(api_key, tickers, start_date, end_date)

            # Redirect stdout to capture output
            captured_output = io.StringIO()  # Create a StringIO object
            sys.stdout = captured_output  # Redirect stdout to this StringIO object            

            investment_data, percent_time_in_market = fss.process(downloaded_data, days_after_dividend, days_before_earnings, initial_investment)

            # Get the captured output and make it ready for rendering
            output = captured_output.getvalue()
            captured_output.close()

            investment_df = fss.create_df(investment_data)
            plot = fss.create_plot(investment_df, percent_time_in_market, days_after_dividend, days_before_earnings)
            
            # Convert your DataFrame to HTML
            investment_data_html = investment_df.to_html(classes='data', header="true")
            
            return render_template('index.html', plot=plot, investment_data_html=investment_data_html, output=output)
        
        except Exception as e:
            print(f"Error processing POST request: {e}")
            result = "Error processing your request."

        return render_template('index.html', plot=result)
    else:
        # GET request to show the form
        return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=True)  # Start the server with debugging enabled
