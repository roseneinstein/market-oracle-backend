import os
from flask import Flask, jsonify, request # Added 'request' for query parameters
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
TWELVE_DATA_API_KEY = os.getenv('TWELVE_DATA_API_KEY')
MARKETSTACK_API_KEY = os.getenv('MARKETSTACK_API_KEY')

@app.route('/')
def home():
    return jsonify({"message": "Backend is running!"})

# Existing route for fetching a single stock price
@app.route('/api/stock/<symbol>')
def get_stock_price(symbol):
    symbol = symbol.upper()

    # --- Alpha Vantage Attempt (Primary) ---
    if ALPHA_VANTAGE_API_KEY:
        url_alpha_vantage = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"

        try:
            print(f"Attempting to fetch {symbol} price from Alpha Vantage...")
            response_av = requests.get(url_alpha_vantage, timeout=10)
            response_av.raise_for_status()
            data_av = response_av.json()

            if "Time Series (Daily)" in data_av:
                latest_date = list(data_av["Time Series (Daily)"].keys())[0]
                latest_price = data_av["Time Series (Daily)"][latest_date]["4. close"]
                print(f"Successfully fetched {symbol} price from Alpha Vantage: {latest_price}")
                return jsonify({
                    "symbol": symbol,
                    "price": float(latest_price),
                    "source": "Alpha Vantage"
                })
            elif "Error Message" in data_av:
                print(f"Alpha Vantage Error for {symbol}: {data_av['Error Message']}")
                if "invalid API call" in data_av["Error Message"].lower():
                     return jsonify({"error": f"Invalid stock symbol: {symbol}"}), 400
                pass # Continue to next API attempt
            else:
                print(f"Alpha Vantage did not return expected daily time series data for {symbol}.")
                pass # Continue to next API attempt

        except requests.exceptions.RequestException as e:
            print(f"Alpha Vantage network or API request error for {symbol}: {str(e)}")
            pass
        except Exception as e:
            print(f"Alpha Vantage unexpected error for {symbol}: {str(e)}")
            pass
    else:
        print("Alpha Vantage API key not configured.")


    # --- Finnhub Attempt (Failover) ---
    if FINNHUB_API_KEY:
        url_finnhub = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
        try:
            print(f"Attempting to fetch {symbol} price from Finnhub (failover)...")
            response_fh = requests.get(url_finnhub, timeout=10)
            response_fh.raise_for_status()
            data_fh = response_fh.json()

            if data_fh and 'c' in data_fh and data_fh['c'] is not None and data_fh['c'] != 0:
                print(f"Successfully fetched {symbol} price from Finnhub: {data_fh['c']}")
                return jsonify({
                    "symbol": symbol,
                    "price": data_fh['c'],
                    "source": "Finnhub"
                })
            else:
                print(f"Finnhub did not return expected data or price is 0 for {symbol}.")
                pass
        except requests.exceptions.RequestException as e:
            print(f"Finnhub network or API request error for {symbol}: {str(e)}")
            pass
        except Exception as e:
            print(f"Finnhub unexpected error for {symbol}: {str(e)}")
            pass
    else:
        print("Finnhub API key not configured.")

    return jsonify({"error": f"Failed to fetch {symbol} price from all available sources or API keys missing."}), 500

# New route for symbol search/autocomplete
@app.route('/api/search')
def search_symbols():
    query = request.args.get('query', '').strip() # Get the search query from URL parameters
    if not query:
        return jsonify({"results": []}) # Return empty if no query

    # --- Finnhub Search (Primary for search) ---
    if FINNHUB_API_KEY:
        url_finnhub_search = f"https://finnhub.io/api/v1/search?q={query}&token={FINNHUB_API_KEY}"
        try:
            print(f"Attempting to search for '{query}' using Finnhub...")
            response_fh_search = requests.get(url_finnhub_search, timeout=10)
            response_fh_search.raise_for_status()
            data_fh_search = response_fh_search.json()

            if data_fh_search and 'result' in data_fh_search:
                # Filter for common stock exchanges if needed, e.g., 'US' for NASDAQ/NYSE
                # For now, just return all results
                results = [
                    {"symbol": item['symbol'], "description": item['description']}
                    for item in data_fh_search['result']
                    if item.get('type') == 'Common Stock' or item.get('type') == 'ADR' or item.get('type') == 'Equity'
                ]
                print(f"Finnhub search found {len(results)} results for '{query}'.")
                return jsonify({"results": results, "source": "Finnhub"})
            else:
                print(f"Finnhub search did not return expected results for '{query}'.")
        except requests.exceptions.RequestException as e:
            print(f"Finnhub search network or API request error for '{query}': {str(e)}")
        except Exception as e:
            print(f"Finnhub search unexpected error for '{query}': {str(e)}")
    else:
        print("Finnhub API key not configured for search.")

    # --- Alpha Vantage Search (Failover for search) ---
    if ALPHA_VANTAGE_API_KEY:
        # Alpha Vantage symbol search
        url_av_search = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={ALPHA_VANTAGE_API_KEY}"
        try:
            print(f"Attempting to search for '{query}' using Alpha Vantage...")
            response_av_search = requests.get(url_av_search, timeout=10)
            response_av_search.raise_for_status()
            data_av_search = response_av_search.json()

            if "bestMatches" in data_av_search:
                results = [
                    {"symbol": item['1. symbol'], "description": item['2. name']}
                    for item in data_av_search['bestMatches']
                    # You might want to filter by region or type here too, e.g., if item['4. region'] == 'United States'
                ]
                print(f"Alpha Vantage search found {len(results)} results for '{query}'.")
                return jsonify({"results": results, "source": "Alpha Vantage"})
            else:
                print(f"Alpha Vantage search did not return expected results for '{query}'.")
        except requests.exceptions.RequestException as e:
            print(f"Alpha Vantage search network or API request error for '{query}': {str(e)}")
        except Exception as e:
            print(f"Alpha Vantage search unexpected error for '{query}': {str(e)}")
    else:
        print("Alpha Vantage API key not configured for search.")

    # If both search attempts fail
    return jsonify({"error": f"Failed to search for '{query}' from all available sources or API keys missing."}), 500


if __name__ == '__main__':
    app.run(debug=True)
