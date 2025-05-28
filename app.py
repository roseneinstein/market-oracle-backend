import os
from flask import Flask, jsonify
from flask_cors import CORS
import requests # New import for making web requests

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# Get API keys from environment variables
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')
MARKETSTACK_API_KEY = os.getenv('MARKETSTACK_API_KEY')

@app.route('/')
def home():
    return jsonify({"message": "Backend is running!"})

@app.route('/api/stock/aapl')
def get_aapl_price():
    if not ALPHA_VANTAGE_API_KEY:
        return jsonify({"error": "Alpha Vantage API key not configured on server"}), 500

    # --- Alpha Vantage Attempt (Primary) ---
    url_alpha_vantage = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey={ALPHA_VANTAGE_API_KEY}"

    try:
        print("Attempting to fetch AAPL price from Alpha Vantage...")
        response_av = requests.get(url_alpha_vantage, timeout=10) # Added timeout
        response_av.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data_av = response_av.json()

        if "Time Series (Daily)" in data_av:
            latest_date = list(data_av["Time Series (Daily)"].keys())[0]
            latest_price = data_av["Time Series (Daily)"][latest_date]["4. close"]
            print(f"Successfully fetched AAPL price from Alpha Vantage: {latest_price}")
            return jsonify({
                "symbol": "AAPL",
                "price": float(latest_price),
                "source": "Alpha Vantage"
            })
        elif "Error Message" in data_av:
            print(f"Alpha Vantage Error: {data_av['Error Message']}")
            # If Alpha Vantage returns an error message, try next API
            pass # Continue to next API attempt
        else:
            print("Alpha Vantage did not return expected daily time series data.")
            pass # Continue to next API attempt

    except requests.exceptions.RequestException as e:
        print(f"Alpha Vantage network or API request error: {str(e)}")
        pass # Continue to next API attempt
    except Exception as e:
        print(f"Alpha Vantage unexpected error: {str(e)}")
        pass # Continue to next API attempt

    # --- Finnhub Attempt (Failover) ---
    if FINNHUB_API_KEY:
        url_finnhub = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={FINNHUB_API_KEY}"
        try:
            print("Attempting to fetch AAPL price from Finnhub (failover)...")
            response_fh = requests.get(url_finnhub, timeout=10)
            response_fh.raise_for_status()
            data_fh = response_fh.json()

            if data_fh and 'c' in data_fh and data_fh['c'] != 0: # 'c' is current price
                print(f"Successfully fetched AAPL price from Finnhub: {data_fh['c']}")
                return jsonify({
                    "symbol": "AAPL",
                    "price": data_fh['c'],
                    "source": "Finnhub"
                })
            else:
                print("Finnhub did not return expected data or price is 0.")
                pass # Continue to next API attempt if more existed
        except requests.exceptions.RequestException as e:
            print(f"Finnhub network or API request error: {str(e)}")
            pass
        except Exception as e:
            print(f"Finnhub unexpected error: {str(e)}")
            pass
    else:
        print("Finnhub API key not configured.")


    # If all attempts fail
    return jsonify({"error": "Failed to fetch AAPL price from all available sources or API keys missing."}), 500


if __name__ == '__main__':
    app.run(debug=True)
