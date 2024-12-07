import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import random
import string
import os

# Initialize Firebase Admin SDK using Streamlit secrets
if not firebase_admin._apps:
    firebase_cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(firebase_cred)
db_firestore = firestore.client()

# Function to retrieve client data by email
def get_client_by_email(email):
    clients_ref = db_firestore.collection('clients')
    client_query = clients_ref.where('email', '==', email).limit(1).stream()
    for client in client_query:
        client_data = client.to_dict()
        client_data['permissions'] = client_data.get('permissions', [])
        client_data['username'] = client_data.get('username', '')
        client_data['password'] = client_data.get('password', '')
        client_data['expiry_date'] = client_data.get('expiry_date', '2099-12-31')
        client_data['login_status'] = client_data.get('login_status', 0)
        return client_data
    return None

# Function to retrieve client data by username
def get_client_by_username(username):
    client_ref = db_firestore.collection('clients').document(username)
    client = client_ref.get()
    if client.exists:
        client_data = client.to_dict()
        client_data['permissions'] = client_data.get('permissions', [])
        client_data['username'] = client_data.get('username', '')
        client_data['password'] = client_data.get('password', '')
        client_data['expiry_date'] = client_data.get('expiry_date', '2099-12-31')
        client_data['login_status'] = client_data.get('login_status', 0)
        return client_data
    return None

# Function to generate a random password
def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(characters) for i in range(length))

# Function to update the password (without affecting login status)
def update_password(username, password):
    db_firestore.collection('clients').document(username).update({'password': password})

# Function to update login status (active/inactive)
def update_login_status(username, status):
    db_firestore.collection('clients').document(username).update({'login_status': status})

# Sign Up: Verify Email and Retrieve or Generate Credentials
def sign_up():
    st.title("Sign Up")
    email = st.text_input("Enter your registered email:")
    if st.button("Generate Login Credentials"):
        client_data = get_client_by_email(email)
        
        if client_data:
            username = client_data['username']
            password = client_data['password']
            
            if not password:
                password = generate_random_password()
                update_password(username, password)
            
            st.success("Login credentials retrieved successfully!")
            st.write(f"**Username**: {username}")
            st.write(f"**Password**: {password}")

            st.session_state['generated_username'] = username
            st.session_state['generated_password'] = password
            st.session_state['credentials_generated'] = True
            st.session_state['signed_up'] = True
            show_login()
        else:
            st.error("This email is not registered. Please contact the admin.")

def show_login():
    st.title("User Login")
    username = st.text_input("Username", value=st.session_state.get('generated_username', ''))
    password = st.text_input("Password", type="password", value=st.session_state.get('generated_password', ''))

    if st.button("Login"):
        client_data = get_client_by_username(username)
        
        if client_data:
            if client_data['login_status'] == 1:
                st.warning("You are already logged in on another device or session.")
                if st.button("Clear Previous Session and Login Again"):
                    update_login_status(username, 0)
                    st.info("Previous session cleared. Please click 'Login' again to continue.")
                    st.experimental_rerun()
                return
            
            if client_data['password'] == password:
                expiry_date = datetime.strptime(client_data['expiry_date'], '%Y-%m-%d')
                if datetime.now() > expiry_date:
                    st.error(f"Your access expired on {expiry_date.strftime('%Y-%m-%d')}. Please contact admin.")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = client_data['username']
                    st.session_state['permissions'] = client_data['permissions']
                    st.session_state['expiry_date'] = client_data['expiry_date']
                    update_login_status(username, 1)
                    st.success(f"Welcome, {username}!")
                    st.session_state['active_dashboard'] = "main"  # Default dashboard
            else:
                st.error("Invalid password.")
        else:
            st.error("Username not found.")


def main_dashboard():
    username = st.session_state.get('username', 'User')
    permissions = st.session_state.get('permissions', [])
    expiry_date = st.session_state.get('expiry_date', datetime.now().strftime("%Y-%m-%d"))

    st.write(f"Welcome, {username}!")
    st.write(f"Your access expires on: {expiry_date}")

    st.write("### Available Dashboards")
    dashboards = {
        'Dashboard 1': 'dashboard_1',
    }

    # Display dashboard options
    for dashboard, key in dashboards.items():
        if dashboard.lower().replace(' ', '') in permissions:
            if st.button(f"Open {dashboard}"):
                st.session_state['active_dashboard'] = key
        else:
            st.write(f"❌ {dashboard} - No Access")


def load_dashboard(filepath):
    # Check if the file exists
    if not os.path.exists(filepath):
        st.error(f"Error: The dashboard file '{filepath}' does not exist.")
        return

    try:
        # Display the loading message
        st.write(f"Loading {filepath}...")

        # Read and execute the file
        with open(filepath, 'r') as file:
            code = file.read()
        exec(code, globals())  # Execute the dashboard script

    except Exception as e:
        # Catch and display any errors during execution
        st.error(f"An error occurred while loading the dashboard: {e}")

def handle_navigation():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if 'active_dashboard' not in st.session_state:
        st.session_state['active_dashboard'] = "main"

    if st.session_state['logged_in']:
        if st.session_state['active_dashboard'] == "main":
            main_dashboard()
        elif st.session_state['active_dashboard'] == "dashboard_1":
            show_dashboard_1()  # Call Dashboard 1 function
        else:
            st.error("Invalid dashboard selection.")
    else:
        choice = st.sidebar.radio("Choose an option", ["Sign Up", "Login"])

        if choice == "Sign Up":
            sign_up()
        else:
            show_login()


if __name__ == "__main__":
    handle_navigation()



# Function for Dashboard 1 (add your 3000+ lines of code here)
def show_dashboard_1():
    st.title("Dashboard 1: Buy Signal (EMA, RSI, Correction)")
    st.write("Welcome to Dashboard 1!")
    
    # ADD YOUR 3000+ LINES OF DASHBOARD 1 CODE BELOW
import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import random
import string
import os

# Initialize Firebase Admin SDK using Streamlit secrets
if not firebase_admin._apps:
    firebase_cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(firebase_cred)
db_firestore = firestore.client()

# Function to retrieve client data by email
def get_client_by_email(email):
    clients_ref = db_firestore.collection('clients')
    client_query = clients_ref.where('email', '==', email).limit(1).stream()
    for client in client_query:
        client_data = client.to_dict()
        client_data['permissions'] = client_data.get('permissions', [])
        client_data['username'] = client_data.get('username', '')
        client_data['password'] = client_data.get('password', '')
        client_data['expiry_date'] = client_data.get('expiry_date', '2099-12-31')
        client_data['login_status'] = client_data.get('login_status', 0)
        return client_data
    return None

# Function to retrieve client data by username
def get_client_by_username(username):
    client_ref = db_firestore.collection('clients').document(username)
    client = client_ref.get()
    if client.exists:
        client_data = client.to_dict()
        client_data['permissions'] = client_data.get('permissions', [])
        client_data['username'] = client_data.get('username', '')
        client_data['password'] = client_data.get('password', '')
        client_data['expiry_date'] = client_data.get('expiry_date', '2099-12-31')
        client_data['login_status'] = client_data.get('login_status', 0)
        return client_data
    return None

# Function to generate a random password
def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(characters) for i in range(length))

# Function to update the password (without affecting login status)
def update_password(username, password):
    db_firestore.collection('clients').document(username).update({'password': password})

# Function to update login status (active/inactive)
def update_login_status(username, status):
    db_firestore.collection('clients').document(username).update({'login_status': status})

# Sign Up: Verify Email and Retrieve or Generate Credentials
def sign_up():
    st.title("Sign Up")
    email = st.text_input("Enter your registered email:")
    if st.button("Generate Login Credentials"):
        client_data = get_client_by_email(email)
        
        if client_data:
            username = client_data['username']
            password = client_data['password']
            
            if not password:
                password = generate_random_password()
                update_password(username, password)
            
            st.success("Login credentials retrieved successfully!")
            st.write(f"**Username**: {username}")
            st.write(f"**Password**: {password}")

            st.session_state['generated_username'] = username
            st.session_state['generated_password'] = password
            st.session_state['credentials_generated'] = True
            st.session_state['signed_up'] = True
            show_login()
        else:
            st.error("This email is not registered. Please contact the admin.")

def show_login():
    st.title("User Login")
    username = st.text_input("Username", value=st.session_state.get('generated_username', ''))
    password = st.text_input("Password", type="password", value=st.session_state.get('generated_password', ''))

    if st.button("Login"):
        client_data = get_client_by_username(username)
        
        if client_data:
            if client_data['login_status'] == 1:
                st.warning("You are already logged in on another device or session.")
                if st.button("Clear Previous Session and Login Again"):
                    update_login_status(username, 0)
                    st.info("Previous session cleared. Please click 'Login' again to continue.")
                    st.experimental_rerun()
                return
            
            if client_data['password'] == password:
                expiry_date = datetime.strptime(client_data['expiry_date'], '%Y-%m-%d')
                if datetime.now() > expiry_date:
                    st.error(f"Your access expired on {expiry_date.strftime('%Y-%m-%d')}. Please contact admin.")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = client_data['username']
                    st.session_state['permissions'] = client_data['permissions']
                    st.session_state['expiry_date'] = client_data['expiry_date']
                    update_login_status(username, 1)
                    st.success(f"Welcome, {username}!")
                    st.session_state['active_dashboard'] = "main"  # Default dashboard
            else:
                st.error("Invalid password.")
        else:
            st.error("Username not found.")


def main_dashboard():
    username = st.session_state.get('username', 'User')
    permissions = st.session_state.get('permissions', [])
    expiry_date = st.session_state.get('expiry_date', datetime.now().strftime("%Y-%m-%d"))

    st.write(f"Welcome, {username}!")
    st.write(f"Your access expires on: {expiry_date}")

    st.write("### Available Dashboards")
    dashboards = {
        'Dashboard 1': 'dashboard_1',
    }

    # Display dashboard options
    for dashboard, key in dashboards.items():
        if dashboard.lower().replace(' ', '') in permissions:
            if st.button(f"Open {dashboard}"):
                st.session_state['active_dashboard'] = key
        else:
            st.write(f"❌ {dashboard} - No Access")


def load_dashboard(filepath):
    # Check if the file exists
    if not os.path.exists(filepath):
        st.error(f"Error: The dashboard file '{filepath}' does not exist.")
        return

    try:
        # Display the loading message
        st.write(f"Loading {filepath}...")

        # Read and execute the file
        with open(filepath, 'r') as file:
            code = file.read()
        exec(code, globals())  # Execute the dashboard script

    except Exception as e:
        # Catch and display any errors during execution
        st.error(f"An error occurred while loading the dashboard: {e}")

def handle_navigation():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if 'active_dashboard' not in st.session_state:
        st.session_state['active_dashboard'] = "main"

    if st.session_state['logged_in']:
        if st.session_state['active_dashboard'] == "main":
            main_dashboard()
        elif st.session_state['active_dashboard'] == "dashboard_1":
            show_dashboard_1()  # Call Dashboard 1 function
        else:
            st.error("Invalid dashboard selection.")
    else:
        choice = st.sidebar.radio("Choose an option", ["Sign Up", "Login"])

        if choice == "Sign Up":
            sign_up()
        else:
            show_login()


if __name__ == "__main__":
    handle_navigation()



# Function for Dashboard 1 (add your 3000+ lines of code here)
def show_dashboard_1():
    st.title("Dashboard 1: Buy Signal (EMA, RSI, Correction)")
    st.write("Welcome to Dashboard 1!")
    
    # ADD YOUR 3000+ LINES OF DASHBOARD 1 CODE BELOW
    import yfinance as yf
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px
from datetime import datetime
from datetime import datetime, timedelta
import streamlit.components.v1 as components


# Set up the Streamlit app
st.title("Nifty 50 Stock Analysis Dashboard")

# Create navigation tabs
tab1, = st.tabs(["📈 EMA 200 Analysis"])

# First Tab: Drawdown Analysis
with tab1:
    st.header("Swing High-Based Drawdown Analysis")


    # # --- Dashboard Settings ---
    # st.set_page_config(page_title='Nifty 50 Stock Dashboard', layout='wide')

    # Sidebar for navigation
    st.sidebar.title("Dashboard Navigation")




    section = st.sidebar.radio("Go to", ["Overview", "Charts", "Buy Signals based on EMA/RSI condition", "Buy Signals based on average historical correction data"])




    # Dropdown for Nifty 50 stocks
    nifty_50_stocks = {
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", "HDFCBANK": "HDFCBANK.NS",
        "HINDUNILVR": "HINDUNILVR.NS", "ICICIBANK": "ICICIBANK.NS", "KOTAKBANK": "KOTAKBANK.NS",
        "LT": "LT.NS", "BHARTIARTL": "BHARTIARTL.NS", "ITC": "ITC.NS", "AXISBANK": "AXISBANK.NS",
        "SBIN": "SBIN.NS", "WIPRO": "WIPRO.NS", "BAJFINANCE": "BAJFINANCE.NS", "MARUTI": "MARUTI.NS",
        "HCLTECH": "HCLTECH.NS", "ADANIPORTS": "ADANIPORTS.NS", "POWERGRID": "POWERGRID.NS",
        "ULTRACEMCO": "ULTRACEMCO.NS", "NTPC": "NTPC.NS", "SUNPHARMA": "SUNPHARMA.NS",
        "TITAN": "TITAN.NS", "ASIANPAINT": "ASIANPAINT.NS", "ONGC": "ONGC.NS", "BAJAJFINSV": "BAJAJFINSV.NS",
        "TECHM": "TECHM.NS", "GRASIM": "GRASIM.NS", "TATASTEEL": "TATASTEEL.NS", "HDFC": "HDFC.NS",
        "JSWSTEEL": "JSWSTEEL.NS", "COALINDIA": "COALINDIA.NS", "BPCL": "BPCL.NS", "SHREECEM": "SHREECEM.NS",
        "DRREDDY": "DRREDDY.NS", "INDUSINDBK": "INDUSINDBK.NS", "HDFCLIFE": "HDFCLIFE.NS", "DIVISLAB": "DIVISLAB.NS",
        "UPL": "UPL.NS", "M&M": "M&M.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "BRITANNIA": "BRITANNIA.NS",
        "CIPLA": "CIPLA.NS", "NESTLEIND": "NESTLEIND.NS", "SBILIFE": "SBILIFE.NS", "EICHERMOT": "EICHERMOT.NS",
        "TATAMOTORS": "TATAMOTORS.NS", "HINDALCO": "HINDALCO.NS", "MTARTECH":"MTARTECH.NS", "Adani gas":"ATGL.NS","vodaphone":"IDEA.NS","Bataindia":"BATAINDIA.NS"
    }




    # Select stock from the dropdown
    selected_stock = st.sidebar.selectbox("Select a Nifty 50 stock for EMA analysis", list(nifty_50_stocks.keys()))




    # Fetch the ticker symbol for the selected stock
    ticker = nifty_50_stocks[selected_stock]




    # Function to calculate the Relative Strength Index (RSI)
    def calculate_rsi(data, window=14):
        delta = data['Close'].diff(1)
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi




    # Fetch historical data for the selected stock from a longer period to ensure EMA accuracy
    start_date = '2010-01-01'  # Fetch data from 2010 to have enough data for a 200-week EMA
    end_date = pd.to_datetime('today').strftime('%Y-%m-%d')




    # Download the data from Yahoo Finance
    data = yf.download(ticker, start=start_date, end=end_date)




    # Convert Date index to datetime to avoid serialization issues
    data.index = pd.to_datetime(data.index)




    # Calculate the 200-day EMA
    data['EMA200'] = data['Close'].ewm(span=200, adjust=False).mean()




    # Calculate the 200-week EMA (Weekly Data)
    data_weekly = data['Close'].resample('W').last()  # Resample to weekly data
    data_weekly['EMA200_Weekly'] = data_weekly.ewm(span=200, adjust=False).mean()




    # Ensure weekly EMA data aligns with daily data for comparison and analysis
    data['EMA200_Weekly'] = data_weekly['EMA200_Weekly'].reindex(data.index, method='ffill')




    # Calculate the RSI (14-day)
    data['RSI'] = calculate_rsi(data)




    # Calculate the percentage difference between the Close price and the EMA (Daily and Weekly)
    data['Percent_Below_EMA'] = (data['EMA200'] - data['Close']) / data['EMA200'] * 100
    data['Percent_Below_EMA_Weekly'] = (data['EMA200_Weekly'] - data['Close']) / data['EMA200_Weekly'] * 100




    # Initialize lists and counters for buy and strong buy signals and below EMA tracking
    buy_signals = []
    strong_buy_signals = []




    # Initialize counters and lists for daily and weekly EMA analysis
    category_0_count, category_1_count, category_2_count, category_3_count = 0, 0, 0, 0
    bottom_points, max_falls = [], []
    weekly_fall_data = []
    fall_data = []




    # Counter to track how many times the stock price crossed below the 200-day and 200-week EMA
    below_ema_count = 0
    cross_below_weekly_ema_count = 0  # For counting the 200-week EMA crosses




    # Tracking variables for below EMA periods
    below_weekly_ema, below_ema = False, False
    lowest_weekly_price, lowest_price = None, None
    lowest_weekly_idx, lowest_idx = None, None
    first_cross_below_weekly_ema, first_weekly_cross_price = None, None
    first_cross_below_date, first_cross_below_price = None, None
    max_percent_fall, first_signal_given, first_strong_signal_given = 0, False, False




    # Flags to track the RSI below 20 condition to avoid repeated signals
    rsi_below_20_flag, rsi_below_20_strong_flag = False, False




    # Limit the analysis to data starting from 2019
    analysis_start_date = '2010-01-01'
    data_analysis = data.loc[analysis_start_date:]




    # Loop through the data to find periods where the stock was below the 200-day and 200-week EMAs
    for i in range(1, len(data_analysis)):
        # Process daily EMA
        if data_analysis['Percent_Below_EMA'].iloc[i] > 0:  # Price is below daily EMA
            if not below_ema:
                below_ema = True
                below_ema_count += 1  # Increment count when price crosses below daily EMA
                first_cross_below_date = data_analysis.index[i]
                first_cross_below_price = data_analysis['Close'].iloc[i]
                lowest_price = data_analysis['Close'].iloc[i]
                lowest_idx = data_analysis.index[i]
                max_percent_fall = data_analysis['Percent_Below_EMA'].iloc[i]
                first_signal_given = False  # Reset signal flag
                rsi_below_20_flag = False  # Reset RSI < 20 flag when crossing below EMA
            else:
                if data_analysis['Close'].iloc[i] < lowest_price:
                    lowest_price = data_analysis['Close'].iloc[i]
                    lowest_idx = data_analysis.index[i]
                max_percent_fall = max(max_percent_fall, data_analysis['Percent_Below_EMA'].iloc[i])




            # Buy signal logic: First signal (RSI < 30 and below 200-day EMA), then RSI < 20 for further signals
            if data_analysis['RSI'].iloc[i] < 30 and not first_signal_given:
                buy_signals.append((data_analysis.index[i], data_analysis['Close'].iloc[i]))
                first_signal_given = True
            elif data_analysis['RSI'].iloc[i] < 20 and first_signal_given and not rsi_below_20_flag:
                buy_signals.append((data_analysis.index[i], data_analysis['Close'].iloc[i]))
                rsi_below_20_flag = True




        elif below_ema:
            # If price crosses above daily EMA, reset tracking for new signals
            cross_above_date = data_analysis.index[i]
            cross_above_price = data_analysis['Close'].iloc[i]
            duration_to_bottom = (lowest_idx - first_cross_below_date).days
            duration_to_cross_above = (cross_above_date - lowest_idx).days




            percent_fall = (data_analysis['EMA200'].loc[lowest_idx] - lowest_price) / data_analysis['EMA200'].loc[lowest_idx] * 100
            if percent_fall < 2:
                category_0_count += 1
            elif 2 <= percent_fall < 5:
                category_1_count += 1
            elif 5 <= percent_fall < 10:
                category_2_count += 1
            elif percent_fall >= 10:
                category_3_count += 1




            bottom_points.append((lowest_idx, lowest_price, percent_fall))
            max_falls.append((lowest_idx, max_percent_fall))




            fall_data.append({
                'Date First Cross Below EMA': first_cross_below_date,
                'First Cross Price': first_cross_below_price,
                'Bottom Date': lowest_idx,
                'Bottom Price': lowest_price,
                'Max Percentage Fall': max_percent_fall,
                'Date Cross Above EMA': cross_above_date,
                'Cross Above Price': cross_above_price,
                'Duration to Bottom (days)': duration_to_bottom,
                'Duration from Bottom to Cross Above (days)': duration_to_cross_above
            })




            below_ema = False
            first_signal_given = False  # Reset signal flag when price crosses above EMA
            rsi_below_20_flag = False  # Reset RSI < 20 flag when price crosses above EMA




        # Process weekly EMA for strong buy signal
        if data_analysis['Percent_Below_EMA_Weekly'].iloc[i] > 0:  # Price is below weekly EMA
            if not below_weekly_ema:
                below_weekly_ema = True
                cross_below_weekly_ema_count += 1  # Increment count when price crosses below weekly EMA
                first_cross_below_weekly_ema = data_analysis.index[i]
                first_weekly_cross_price = data_analysis['Close'].iloc[i]
                lowest_weekly_price = data_analysis['Close'].iloc[i]
                lowest_weekly_idx = data_analysis.index[i]
                first_strong_signal_given = False  # Reset strong signal flag
                rsi_below_20_strong_flag = False  # Reset RSI < 20 flag for strong signals




            # Strong buy signal logic (RSI < 30, below both 200-day and 200-week EMA)
            if data_analysis['RSI'].iloc[i] < 30 and data_analysis['Close'].iloc[i] < data_analysis['EMA200_Weekly'].iloc[i] and not first_strong_signal_given:
                strong_buy_signals.append((data_analysis.index[i], data_analysis['Close'].iloc[i]))
                first_strong_signal_given = True
            elif data_analysis['RSI'].iloc[i] < 20 and data_analysis['Close'].iloc[i] < data_analysis['EMA200_Weekly'].iloc[i] and first_strong_signal_given and not rsi_below_20_strong_flag:
                strong_buy_signals.append((data_analysis.index[i], data_analysis['Close'].iloc[i]))
                rsi_below_20_strong_flag = True




        elif below_weekly_ema:
            # If price crosses back above the weekly EMA, reset tracking
            weekly_fall_data.append({
                'First Cross Below Weekly EMA Date': first_cross_below_weekly_ema,
                'First Cross Price': first_weekly_cross_price,
                'Lowest Price Date': lowest_weekly_idx,
                'Lowest Price': lowest_weekly_price,
                'Cross Above Weekly EMA Date': data_analysis.index[i],
                'Cross Above Price': data_analysis['Close'].iloc[i]
            })
            below_weekly_ema = False
            first_strong_signal_given = False  # Reset strong signal flag when price crosses above weekly EMA
            rsi_below_20_strong_flag = False  # Reset RSI < 20 flag when price crosses above weekly EMA




    # Create DataFrames for buy and strong buy signals
    buy_signals_df = pd.DataFrame(buy_signals, columns=['Date', 'Price']).set_index('Date')
    strong_buy_signals_df = pd.DataFrame(strong_buy_signals, columns=['Date', 'Price']).set_index('Date')




    # Create DataFrame for weekly EMA falls
    weekly_fall_df = pd.DataFrame(weekly_fall_data)




    # Format the dates for display
    fall_data_df = pd.DataFrame(fall_data)
    fall_data_df['Date First Cross Below EMA'] = pd.to_datetime(fall_data_df['Date First Cross Below EMA']).dt.strftime('%B %d, %Y')
    fall_data_df['Bottom Date'] = pd.to_datetime(fall_data_df['Bottom Date']).dt.strftime('%B %d, %Y')
    fall_data_df['Date Cross Above EMA'] = pd.to_datetime(fall_data_df['Date Cross Above EMA']).dt.strftime('%B %d, %Y')




    # --- Additional Section for Average-Based Buy Signals ---
    # Calculate the average and standard deviation of the percentage fall and duration
    avg_percent_fall = fall_data_df['Max Percentage Fall'].mean()
    std_percent_fall = fall_data_df['Max Percentage Fall'].std()
    avg_duration_bottom = fall_data_df['Duration to Bottom (days)'].mean()
    std_duration_bottom = fall_data_df['Duration to Bottom (days)'].std()




    # Define thresholds for generating buy signals based on averages and 2 standard deviations
    fall_threshold_upper = avg_percent_fall + 2 * std_percent_fall
    fall_threshold_lower = avg_percent_fall - 2 * std_percent_fall
    duration_threshold_upper = avg_duration_bottom + 2 * std_duration_bottom
    duration_threshold_lower = avg_duration_bottom - 2 * std_duration_bottom




    # New Buy Signal based on average fall and duration
    new_buy_signals = []
    for i in range(1, len(fall_data_df)):
        percent_fall = fall_data_df['Max Percentage Fall'].iloc[i]
        duration_to_bottom = fall_data_df['Duration to Bottom (days)'].iloc[i]
    
        if (fall_threshold_lower <= percent_fall <= fall_threshold_upper) and \
        (duration_threshold_lower <= duration_to_bottom <= duration_threshold_upper):
            new_buy_signals.append((fall_data_df['Bottom Date'].iloc[i], fall_data_df['Bottom Price'].iloc[i]))




    # Create DataFrame for new buy signals
    new_buy_signals_df = pd.DataFrame(new_buy_signals, columns=['Date', 'Price']).set_index('Date')




    # Convert 'Date' index of new_buy_signals_df to datetime format
    new_buy_signals_df.index = pd.to_datetime(new_buy_signals_df.index)




    # --- Sidebar Section Navigation ---
    if section == "Overview":
        st.title(f"{selected_stock} Stock Overview")
        st.write(f"""
        This dashboard provides an analysis of {selected_stock} stock based on the following criteria:
        - Stock price performance relative to the 200-day and 200-week Exponential Moving Averages (EMA)
        - Buy signals based on RSI (Relative Strength Index) and EMA
        - Categorization of price movements below the EMAs
        - Buy signals based on average percentage fall and duration below EMA
        - Statistical summaries and download options for signal data.
        """)




    elif section == "Charts":
        st.title(f"{selected_stock} Stock Price and EMA Analysis")
    
        # Create a chart using Matplotlib
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(data['Close'], label=f'{selected_stock} Close Price', color='blue', linewidth=1.5)
        ax.plot(data['EMA200'], label='200-day EMA', linestyle='--', color='orange')
        ax.plot(data['EMA200_Weekly'], label='200-week EMA', linestyle='--', color='purple')




        # Highlight the periods when price is below the 200-day EMA with shading
        ax.fill_between(data.index, data['Close'], data['EMA200'], where=(data['Close'] < data['EMA200']),
                        color='lightgray', label='Below 200-day EMA', alpha=0.5)




        # Plot the red dots at the bottom points where price is below EMA and crosses back above
        bottom_dates, bottom_prices, _ = zip(*bottom_points) if bottom_points else ([], [], [])
        ax.scatter(bottom_dates, bottom_prices, label='Bottom Points (Before Cross Above EMA)', color='red', marker='o', s=60)




        # Highlight the buy signals and strong buy signals
        ax.scatter(buy_signals_df.index, buy_signals_df['Price'], label='Buy Signal (RSI < 30 & Price Below EMA 200)', color='green', marker='^', s=60)
        ax.scatter(strong_buy_signals_df.index, strong_buy_signals_df['Price'], label='Strong Buy Signal (RSI < 30 & Below Both EMAs)', color='purple', marker='x', s=80)




        # Customize the plot with grid and better formatting
        ax.set_title(f'{selected_stock} Stock Price vs 200-day & 200-week EMA (Buy and Strong Buy Signals)', fontsize=16)
        ax.legend()
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.set_ylabel('Price', fontsize=12)
        ax.set_xlabel('Date', fontsize=12)




        # Display the chart in Streamlit
        st.pyplot(fig)


    elif section == "Buy Signals based on EMA/RSI condition":
        st.title(f"Buy Signals for {selected_stock} (RSI < 30 and Below EMA)")

        # Input parameters
        full_data_start_date = '1990-01-01'  # Start as early as possible to calculate indicators properly
        signal_start_date = '2000-01-01'     # Start signals from 2000 onward
        end_date = datetime.today().strftime('%Y-%m-%d')

        # Fetch full data to calculate accurate RSI and EMAs
        full_data = yf.download(ticker, start=full_data_start_date, end=end_date)

        # Ensure data is loaded
        if full_data.empty:
            st.error(f"No data fetched for {selected_stock}.")
            st.stop()

        # --- Calculate EMAs ---
        def calculate_ema(series, length):
            ema = series.copy()
            multiplier = 2 / (length + 1)
            ema.iloc[0] = series.iloc[0]  # Initialize with the first close price
            for i in range(1, len(series)):
                ema.iloc[i] = (series.iloc[i] - ema.iloc[i - 1]) * multiplier + ema.iloc[i - 1]
            return ema

        # Calculate Daily and Weekly EMAs using full historical data
        full_data['EMA200'] = calculate_ema(full_data['Close'], 200)
        weekly_data = full_data['Close'].resample('W').last()
        weekly_ema200 = calculate_ema(weekly_data, 200)
        full_data['EMA200_Weekly'] = weekly_ema200.reindex(full_data.index, method='ffill')


        # --- Calculate RSI using full historical data ---
        def calculate_rsi(series, period):
            delta = series.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
            avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi


        # Calculate Weekly RSI using full historical data
        weekly_rsi = calculate_rsi(weekly_data, 14)
        full_data['RSI_Weekly'] = weekly_rsi.reindex(full_data.index, method='ffill')


        # Now filter the data to start signals from 2000 onwards
        data = full_data.loc[signal_start_date:]


        # --- Add price comparison columns ---
        data['Price_Below_Daily_EMA'] = data['Close'] < data['EMA200']
        data['Price_Below_Weekly_EMA'] = data['Close'] < data['EMA200_Weekly']


        # --- Buy Signal Logic with Fall from EMAs ---
        data['Buy_Signal'] = False  # Create a column to store buy signals
        data['Fall_%_From_EMA_to_Buying_Signal(D)'] = np.nan  # Renamed column
        data['Fall_%_From_EMA_to_Buying_Signal(W)'] = np.nan  # Renamed column


        buy_signal_active = False
        min_price = None  # Track the lowest price during the buy signal period


        for i in range(1, len(data)):
            # Check if the price is below both EMAs and RSI is below 30
            if (data['Price_Below_Daily_EMA'].iloc[i] and 
                data['Price_Below_Weekly_EMA'].iloc[i] and 
                data['RSI_Weekly'].iloc[i] < 30 and not buy_signal_active):
                
                # Trigger buy signal
                data.loc[data.index[i], 'Buy_Signal'] = True
                buy_signal_price = data['Close'].iloc[i]
                min_price = buy_signal_price  # Initialize min price to the current price
                
                # Calculate the fall percentage from both EMAs at the time of the buy signal
                fall_from_daily_ema = ((data['EMA200'].iloc[i] - buy_signal_price) / data['EMA200'].iloc[i]) * 100
                fall_from_weekly_ema = ((data['EMA200_Weekly'].iloc[i] - buy_signal_price) / data['EMA200_Weekly'].iloc[i]) * 100
                
                # Store the fall from EMAs at the buy signal
                data.loc[data.index[i], 'Fall_%_From_EMA_to_Buying_Signal(D)'] = fall_from_daily_ema
                data.loc[data.index[i], 'Fall_%_From_EMA_to_Buying_Signal(W)'] = fall_from_weekly_ema


                buy_signal_active = True
            
            # Reset the buy signal when the price crosses above the closest EMA
            closest_ema = min(data['EMA200'].iloc[i], data['EMA200_Weekly'].iloc[i])
            if data['Close'].iloc[i] >= closest_ema:
                buy_signal_active = False


        # Initialize variables to track max fall below EMA 200
        data['Max_Fall_Below_EMA(200/D)'] = np.nan
        data['Price_at_Max_Drop_Below_EMA200_Daily'] = np.nan

        # Variables to track the active fall period
        below_ema_active = False
        max_fall_below_ema = 0
        entry_price = None
        lowest_price = None

        for i in range(1, len(data)):
            current_price = data['Close'].iloc[i]
            ema_200 = data['EMA200'].iloc[i]

            # Start tracking if price crosses below EMA 200
            if current_price < ema_200 and not below_ema_active:
                below_ema_active = True
                entry_price = current_price
                lowest_price = current_price
                max_fall_below_ema = 0  # Reset for a new period

            if below_ema_active:
                if current_price < ema_200:
                    lowest_price = min(lowest_price, current_price)
                    fall_percentage = ((entry_price - lowest_price) / entry_price) * 100
                    max_fall_below_ema = max(max_fall_below_ema, fall_percentage)

                    # Assign calculated values safely
                    data.loc[data.index[i], 'Max_Fall_Below_EMA(200/D)'] = max_fall_below_ema
                    data.loc[data.index[i], 'Price_at_Max_Drop_Below_EMA200_Daily'] = lowest_price

            # Reset when price crosses above EMA 200
            if current_price >= ema_200:
                below_ema_active = False
                entry_price = None
                lowest_price = None
                max_fall_below_ema = 0


            # Track the lowest price and fall percentage if the price remains below EMA 200
            if below_ema_active and current_price < ema_200:
                # Update the lowest price during the period below EMA 200
                lowest_price = min(lowest_price, current_price)


                # Calculate fall percentage from the entry price
                fall_percentage = ((entry_price - lowest_price) / entry_price) * 100


                # Update the maximum fall and the lowest price if the current fall is greater
                if fall_percentage > max_fall_below_ema:
                    max_fall_below_ema = fall_percentage


                # Store the max fall and the lowest price at the point of maximum drop
                data.loc[data.index[i], 'Max_Fall_Below_EMA(200/D)'] = max_fall_below_ema
                data.loc[data.index[i], 'Price_at_Max_Drop_Below_EMA200_Daily'] = lowest_price


            # Reset tracking when the price crosses back above EMA 200
            if current_price >= ema_200:
                below_ema_active = False  # Stop tracking when price crosses above EMA 200
                max_fall_below_ema = 0  # Reset for the next period below EMA
                entry_price = None
                lowest_price = None


            # --- Add Max % Fall Below EMA 200 Weekly ---
        data['Max_Fall_Below_EMA(200/W)'] = np.nan  # Create a column to store the max fall % below EMA 200 weekly
        data['Price_at_Max_Drop_Below_EMA200_Weekly'] = np.nan  # Track the lowest price at the max drop below EMA 200 weekly


        # Variables to track max fall and active periods below EMA 200 weekly
        below_ema_weekly_active = False  # Track if the price is currently below the weekly EMA 200
        max_fall_below_ema_weekly = 0  # Track the maximum fall below the weekly EMA 200
        entry_price_weekly = None  # The price when the stock first crosses below the weekly EMA 200
        lowest_price_weekly = None  # Track the lowest price while below weekly EMA 200


        for i in range(1, len(data)):
            current_price = data['Close'].iloc[i]
            ema_200_weekly = data['EMA200_Weekly'].iloc[i]


            # Start tracking when price crosses below the weekly EMA 200
            if current_price < ema_200_weekly and not below_ema_weekly_active:
                below_ema_weekly_active = True  # Set active tracking below EMA 200 weekly
                entry_price_weekly = current_price  # Set the entry price when crossing below EMA 200 weekly
                lowest_price_weekly = current_price  # Initialize the lowest price with the current price
                max_fall_below_ema_weekly = 0  # Reset the max fall for the new period


            # Track the lowest price and fall percentage if the price remains below EMA 200 weekly
            if below_ema_weekly_active and current_price < ema_200_weekly:
                # Update the lowest price during the period below the weekly EMA 200
                lowest_price_weekly = min(lowest_price_weekly, current_price)


                # Calculate the fall percentage from the entry price
                fall_percentage_weekly = ((entry_price_weekly - lowest_price_weekly) / entry_price_weekly) * 100


                # Update the maximum fall if the current fall is greater
                if fall_percentage_weekly > max_fall_below_ema_weekly:
                    max_fall_below_ema_weekly = fall_percentage_weekly


                # Store the max fall and the price at the lowest point
                data.loc[data.index[i], 'Max_Fall_Below_EMA(200/W)'] = max_fall_below_ema_weekly
                data.loc[data.index[i], 'Price_at_Max_Drop_Below_EMA200_Weekly'] = lowest_price_weekly


            # Reset tracking when the price crosses back above EMA 200 weekly
            if current_price >= ema_200_weekly:
                below_ema_weekly_active = False  # Stop tracking when price crosses above EMA 200 weekly
                max_fall_below_ema_weekly = 0  # Reset for the next period below EMA 200 weekly
                entry_price_weekly = None
                lowest_price_weekly = None


        # --- Calculate Differences --- 
        # Difference between max fall below EMA daily and fall % from EMA to buying signal
        data['Difference_Max_Fall-Buying_Signal_Fall(D)'] = data['Max_Fall_Below_EMA(200/D)'] - data['Fall_%_From_EMA_to_Buying_Signal(D)']


        # Difference between max fall below EMA weekly and fall % from weekly EMA to buying signal
        data['Difference_Max_Fall-Buying_Signal_Fall(W)'] = data['Max_Fall_Below_EMA(200/W)'] - data['Fall_%_From_EMA_to_Buying_Signal(W)']


            # Fetch CMP for the selected stock
        cmp = yf.download(ticker, period='1d')['Close'].iloc[-1]


        # Fetch the latest EMA 200 Daily and EMA 200 Weekly
        ema_200_daily = data['EMA200'].iloc[-1]
        ema_200_weekly = data['EMA200_Weekly'].iloc[-1]
        rsi_weekly_latest = data['RSI_Weekly'].iloc[-1]


        # Calculate the percentage difference from EMA 200 Daily and Weekly
        percent_diff_from_ema_daily = ((cmp - ema_200_daily) / ema_200_daily) * 100
        percent_diff_from_ema_weekly = ((cmp - ema_200_weekly) / ema_200_weekly) * 100


        # --- Display logic for missing or achieved ---
        # For EMA 200 Daily: If CMP is below the EMA, show "achieved", by what percentage, and the actual EMA value
        if percent_diff_from_ema_daily < 0:
            ema_daily_status = f"<span style='color:green; font-weight:bold;'>Achieved</span> by {abs(percent_diff_from_ema_daily):.2f}% below (EMA 200 Daily: <span style='font-weight:bold;'>{ema_200_daily:.2f}</span>)"
        else:
            ema_daily_status = f"<span style='color:red; font-weight:bold;'>{abs(percent_diff_from_ema_daily):.2f}% above</span> (EMA 200 Daily: <span style='font-weight:bold;'>{ema_200_daily:.2f}</span>)"


        # For EMA 200 Weekly: If CMP is below the EMA, show "achieved", by what percentage, and the actual EMA value
        if percent_diff_from_ema_weekly < 0:
            ema_weekly_status = f"<span style='color:green; font-weight:bold;'>Achieved</span> by {abs(percent_diff_from_ema_weekly):.2f}% below (EMA 200 Weekly: <span style='font-weight:bold;'>{ema_200_weekly:.2f}</span>)"
        else:
            ema_weekly_status = f"<span style='color:red; font-weight:bold;'>{abs(percent_diff_from_ema_weekly):.2f}% above</span> (EMA 200 Weekly: <span style='font-weight:bold;'>{ema_200_weekly:.2f}</span>)"


        # For RSI: If RSI is below 30, show "achieved" with the actual RSI value
        if rsi_weekly_latest < 30:
            rsi_status = f"<span style='color:green; font-weight:bold;'>Achieved</span> by {abs(30 - rsi_weekly_latest):.2f} points below (RSI: <span style='font-weight:bold;'>{rsi_weekly_latest:.2f}</span>)"
        else:
            rsi_status = f"<span style='color:red; font-weight:bold;'>Missing</span> by {rsi_weekly_latest - 30:.2f} points (RSI: <span style='font-weight:bold;'>{rsi_weekly_latest:.2f}</span>)"


        # --- Check which conditions are met ---
        condition_ema_daily_met = cmp < ema_200_daily
        condition_ema_weekly_met = cmp < ema_200_weekly
        condition_rsi_met = rsi_weekly_latest < 30


        # --- Display CMP, EMA values, and status with advanced styling ---
        st.markdown(f"""
        <div style="font-family: 'Arial', sans-serif; color: #333; font-size: 18px; padding: 20px; border: 1px solid #e3e3e3; border-radius: 8px; background-color: #f8f9fa;">
            <h3 style="margin-bottom: 10px; color: #007BFF;">Current Market Data for {selected_stock}</h3>
            <ul style="list-style-type: none; padding-left: 0;">
                <li><b>CMP (Current Market Price):</b> {cmp:.2f}</li>
                <li><b>EMA 200 Daily Price:</b> {ema_200_daily:.2f}</li>
                <li><b>EMA 200 Weekly Price:</b> {ema_200_weekly:.2f}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


        # Display the status for EMA 200 Daily, Weekly, and RSI with custom text formatting
        st.markdown(f"""
        <div style="font-family: 'Arial', sans-serif; font-size: 16px; padding: 15px; background-color: #e9f7ef; border-left: 4px solid #28a745; margin-top: 20px;">
            <h4 style="color: #28a745;">Condition Status</h4>
            <ul style="list-style-type: none; padding-left: 0; font-size: 15px;">
                <li style="margin-bottom: 10px;">📊 <b>Status for EMA 200 Daily:</b> {ema_daily_status}</li>
                <li style="margin-bottom: 10px;">📊 <b>Status for EMA 200 Weekly:</b> {ema_weekly_status}</li>
                <li style="margin-bottom: 10px;">📊 <b>RSI Status (relative to 30):</b> {rsi_status}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


        # --- Display tick boxes for condition checks ---
        st.subheader("Buy Condition Checks")


        # Function to display a checkbox with a green tick when the condition is met
        def display_custom_checkbox_with_tick(condition, label):
            if condition:
                # Green tick inside the box if the condition is met
                st.markdown(f"""
                    <div style="display: flex; align-items: center; font-family: Arial, sans-serif; font-size: 16px; color: #444; padding: 5px;">
                        <div style="width: 20px; height: 20px; border: 2px solid black; margin-right: 10px; display: flex; justify-content: center; align-items: center; background-color: lightgreen;">
                            <span style="color: green;">&#10003;</span>
                        </div>
                        <span style="font-weight: bold;">{label}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Empty checkbox if the condition is not met
                st.markdown(f"""
                    <div style="display: flex; align-items: center; font-family: Arial, sans-serif; font-size: 16px; color: #444; padding: 5px;">
                        <div style="width: 20px; height: 20px; border: 2px solid black; margin-right: 10px; display: flex; justify-content: center; align-items: center;">
                        </div>
                        <span style="font-weight: bold;">{label}</span>
                    </div>
                    """, unsafe_allow_html=True)


        # CMP < EMA 200 Daily
        display_custom_checkbox_with_tick(condition_ema_daily_met, "CMP below EMA 200 Daily")


        # CMP < EMA 200 Weekly
        display_custom_checkbox_with_tick(condition_ema_weekly_met, "CMP below EMA 200 Weekly")


        # RSI < 30
        display_custom_checkbox_with_tick(condition_rsi_met, "RSI below 30")


        fig = go.Figure()


        # Plot Close Price
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close Price', line=dict(color='blue')))


        # Plot Daily and Weekly EMAs
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA200'], name='Daily EMA 200', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA200_Weekly'], name='Weekly EMA 200', line=dict(color='green')))


        # Plot Buy Signals
        buy_signals = data[data['Buy_Signal']]
        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Buy Signal',
                                marker=dict(color='gold', size=10, symbol='triangle-up')))


        # Plot Max Fall Below EMA 200 Daily as a separate trace (optional)
        fig.add_trace(go.Scatter(x=data.index, y=data['Max_Fall_Below_EMA(200/D)'], name='Max Fall Below EMA 200 Daily (%)', 
                                line=dict(color='purple', dash='dash')))


        # Plot Max Fall Below EMA 200 Weekly as a separate trace (optional)
        fig.add_trace(go.Scatter(x=data.index, y=data['Max_Fall_Below_EMA(200/W)'], name='Max Fall Below EMA 200 Weekly (%)', 
                                line=dict(color='orange', dash='dash')))


        # Update layout
        fig.update_layout(title=f"Buy Signals, Max Fall, and Fall % from Both EMAs for {selected_stock}", 
                        xaxis_title='Date', yaxis_title='Price',
                        font=dict(size=12), hovermode='x')


        st.plotly_chart(fig, use_container_width=True)


        # --- Show Buy Signal Data with Max Fall Below EMAs ---
        st.subheader("Buy Signals and Maximum Fall from EMAs")
        st.dataframe(buy_signals[['Close', 'EMA200', 'EMA200_Weekly', 'RSI_Weekly', 
                                'Fall_%_From_EMA_to_Buying_Signal(D)', 'Fall_%_From_EMA_to_Buying_Signal(W)', 
                                'Max_Fall_Below_EMA(200/D)', 'Max_Fall_Below_EMA(200/W)', 
                                'Price_at_Max_Drop_Below_EMA200_Daily',
                                'Difference_Max_Fall-Buying_Signal_Fall(D)',
                                'Difference_Max_Fall-Buying_Signal_Fall(W)']])


        # Option to download buy signals data
        st.download_button(label="Download Buy Signals Data", data=buy_signals.to_csv(), file_name=f"{selected_stock}_buy_signals.csv", mime="text/csv")


        # --- Calculate Averages and Standard Deviations ---

                # Average Fall % from EMA 200 Daily to Buying Signal
        avg_fall_ema_to_buying_daily = buy_signals['Fall_%_From_EMA_to_Buying_Signal(D)'].mean()

        # Average Fall % from EMA 200 Weekly to Buying Signal
        avg_fall_ema_to_buying_weekly = buy_signals['Fall_%_From_EMA_to_Buying_Signal(W)'].mean()
        # Average % Difference between EMA 200 Daily and its corresponding Buy Signal
        average_diff_daily = buy_signals['Difference_Max_Fall-Buying_Signal_Fall(D)'].mean()
    


        # Average % Difference between EMA 200 Weekly and its corresponding Buy Signal
        average_diff_weekly = buy_signals['Difference_Max_Fall-Buying_Signal_Fall(W)'].mean()
        


        # Max fall from EMA 200 Daily
        max_fall_daily = buy_signals['Max_Fall_Below_EMA(200/D)'].max()
        


        # --- Calculate Average and Standard Deviation for EMA to Max Drop ---
        # Average % Difference between EMA 200 Daily and Max Drop
        avg_diff_daily_ema_max_drop = buy_signals['Max_Fall_Below_EMA(200/D)'].mean()
        


        # Average % Difference between EMA 200 Weekly and Max Drop
        avg_diff_weekly_ema_max_drop = buy_signals['Max_Fall_Below_EMA(200/W)'].mean()
        
        # --- Calculate Max Differences for Summary Statistics ---
        # Max difference between EMA 200 Daily buy signal fall and Max Fall Below EMA 200 Daily
        max_diff_daily = buy_signals['Difference_Max_Fall-Buying_Signal_Fall(D)'].max()

        # Max difference between EMA 200 Weekly buy signal fall and Max Fall Below EMA 200 Weekly
        max_diff_weekly = buy_signals['Difference_Max_Fall-Buying_Signal_Fall(W)'].max()

        # --- Display Averages and Standard Deviations in a Separate Table ---
        st.subheader("Summary Statistics")

        summary_stats = {
            'Statistic': [
                'Average % Diff Daily EMA to Buy Signal', 
                'Average % Diff Weekly EMA to Buy Signal', 
                'Max % Fall Below EMA 200 Daily',
                'Max Difference Between Buying Signal Fall and Max Fall Below EMA 200 Daily',
                'Max Difference Between Buying Signal Fall and Max Fall Below EMA 200 Weekly',
                'Average Fall % from EMA 200 Daily to Buying Signal',  # Added
                'Average Fall % from EMA 200 Weekly to Buying Signal'  # Added
            ],
            'Value': [
                average_diff_daily, 
                average_diff_weekly,  
                max_fall_daily, 
                max_diff_daily,
                max_diff_weekly,
                avg_fall_ema_to_buying_daily,  # Added
                avg_fall_ema_to_buying_weekly  # Added
            ]
        }


        # Convert the summary stats dictionary into a DataFrame
        summary_df = pd.DataFrame(summary_stats).round(2)


        # Display the summary table
        #st.table(summary_df)


        # Option to download the summary stats data
        # st.download_button(label="Download Summary Statistics", data=summary_df.to_csv(), file_name=f"{selected_stock}_summary_statistics.csv", mime="text/csv")
        fig_summary = go.Figure()


        # Add vertical bar traces for each statistic
        fig_summary.add_trace(go.Bar(
            y=summary_df['Statistic'],  # Y-axis will have the statistics for vertical orientation
            x=summary_df['Value'],  # X-axis will have the values
            name='Summary Statistics',
            orientation='h',  # This sets the orientation to vertical bars (horizontal in axis terms)
            marker_color='royalblue'  # Professional color choice
        ))


        # Update the layout of the bar chart for a professional look
        fig_summary.update_layout(
            title="<b>Summary Statistics of Buy Signals and EMA Falls</b>",
            xaxis_title='<b>Value</b>',
            yaxis_title='<b>Statistic</b>',
            font=dict(size=12, family="Arial, sans-serif"),  # Professional font
            hovermode='y',
            plot_bgcolor='rgba(255,255,255,0.9)',  # Light background for professional look
            paper_bgcolor='rgba(255,255,255,0)',  # Transparent paper background
            showlegend=False,
            xaxis=dict(
                showgrid=True, gridwidth=0.5, gridcolor='lightgray'  # Light grid lines for clarity
            ),
            yaxis=dict(
                showgrid=False  # No gridlines on the Y-axis for a cleaner look
            )
        )


        # Display the bar chart
        st.plotly_chart(fig_summary, use_container_width=True)


        # Add new columns to track the time and period for successful, partially successful, and failed signals
        data['Time_to_Gain'] = np.nan  # Track time taken for gain (if successful)
        data['Period_to_Gain'] = np.nan  # Track period of gain (start date to end date of gain)
        data['Failed_Signal'] = False  # Initially mark all signals as not failed
        data['Successful_Signal'] = False  # Initially mark all signals as not successful
        data['Partially_Successful_Signal'] = False  # Track partially successful signals

        # Define success conditions
        success_threshold_7 = 0.07  # 7% gain threshold for successful signals
        partial_success_threshold_10 = 0.10  # 10% gain threshold for partially successful signals
        partial_success_threshold_15 = 0.15  # 15% gain threshold for partially successful signals

        # Loop through buy signals to check for successful signals
        for i in range(len(data)):
            if data['Buy_Signal'].iloc[i]:
                # Check the future data after the buy signal
                signal_date = data.index[i]
                signal_price = data['Close'].iloc[i]
                
                # Calculate percentage gain over time
                future_data = data.loc[signal_date:]
                future_gain = (future_data['Close'] - signal_price) / signal_price
                
                # Check if the 7% gain was achieved at any point for successful signals
                if (future_gain >= success_threshold_7).any():
                    success_index = future_gain[future_gain >= success_threshold_7].index[0]
                    
                    # Record the time it took to reach 7% gain
                    time_to_gain = (success_index - signal_date).days
                    data.loc[signal_date, 'Time_to_Gain'] = time_to_gain
                    data.loc[signal_date, 'Period_to_Gain'] = f"{signal_date.strftime('%Y-%m-%d')} to {success_index.strftime('%Y-%m-%d')}"

        # Calculate the average time it takes to achieve a 7% gain for successful signals
        average_days_to_gain = int(data['Time_to_Gain'].mean())

        # Ensure there are valid values before calculating the standard deviation
        if 'Time_to_Gain' in data.columns and data['Time_to_Gain'].notna().any():
            std_days_to_gain_value = data['Time_to_Gain'].dropna().std()
            std_days_to_gain = int(std_days_to_gain_value) if not pd.isna(std_days_to_gain_value) else 0
        else:
            std_days_to_gain = 0  # Default to 0 if no valid data exists


        # Define the upper range of the standard deviation
        upper_range_days_to_gain = average_days_to_gain + std_days_to_gain

        # Loop again to mark signals as partially successful based on new logic
        for i in range(len(data)):
            if data['Buy_Signal'].iloc[i]:
                # Get the time to gain for this signal
                time_to_gain = data.loc[data.index[i], 'Time_to_Gain']
                
                if time_to_gain > average_days_to_gain and time_to_gain <= upper_range_days_to_gain:
                    # Check if the partial success conditions apply based on standard deviation ranges
                    if std_days_to_gain <= 100 and (future_gain >= partial_success_threshold_10).any():
                        partial_success_index = future_gain[future_gain >= partial_success_threshold_10].index[0]
                        data.loc[data.index[i], 'Partially_Successful_Signal'] = True
                        data.loc[data.index[i], 'Time_to_Gain'] = (partial_success_index - signal_date).days
                        data.loc[data.index[i], 'Period_to_Gain'] = f"{signal_date.strftime('%Y-%m-%d')} to {partial_success_index.strftime('%Y-%m-%d')}"
                    
                    elif 100 < std_days_to_gain <= 150 and (future_gain >= partial_success_threshold_15).any():
                        partial_success_index = future_gain[future_gain >= partial_success_threshold_15].index[0]
                        data.loc[data.index[i], 'Partially_Successful_Signal'] = True
                        data.loc[data.index[i], 'Time_to_Gain'] = (partial_success_index - signal_date).days
                        data.loc[data.index[i], 'Period_to_Gain'] = f"{signal_date.strftime('%Y-%m-%d')} to {partial_success_index.strftime('%Y-%m-%d')}"

        # Mark signals as:
        # - 'Successful_Signal' if gained 7% within average days
        # - 'Failed_Signal' if took longer than the upper range to gain 7%
        data['Successful_Signal'] = data['Time_to_Gain'] <= average_days_to_gain
        data['Failed_Signal'] = data['Time_to_Gain'] > upper_range_days_to_gain

        # Ensure no NaN values in 'Failed_Signal', 'Successful_Signal', and 'Partially_Successful_Signal'
        data['Failed_Signal'] = data['Failed_Signal'].fillna(False)
        data['Successful_Signal'] = data['Successful_Signal'].fillna(False)
        data['Partially_Successful_Signal'] = data['Partially_Successful_Signal'].fillna(False)

        # Calculate the total buy signals, successful signals, partially successful signals, and failed signals
        total_signals = data['Buy_Signal'].sum()
        successful_signals = data[(data['Buy_Signal']) & (data['Successful_Signal'])].shape[0]
        partially_successful_signals = data[(data['Buy_Signal']) & (data['Partially_Successful_Signal'])].shape[0]
        failed_signals = data['Failed_Signal'].sum()

        # Display the success, partial success, and failure rates
        success_rate = (successful_signals / total_signals) * 100 if total_signals > 0 else 0
        partial_success_rate = (partially_successful_signals / total_signals) * 100 if total_signals > 0 else 0
        failure_rate = (failed_signals / total_signals) * 100 if total_signals > 0 else 0

        # Create a compact card layout for better presentation
        st.subheader("Performance Summary of Buy Signals")

        # Add some custom styling using markdown for a professional look
        st.markdown(f"""
        <style>
            .card {{
                display: flex;
                justify-content: space-between;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 10px;
                margin: 10px 0;
            }}
            .card .left {{
                text-align: left;
            }}
            .card .right {{
                text-align: right;
            }}
            .card-title {{
                font-size: 16px;
                font-weight: bold;
                color: #1a73e8;
            }}
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #0d47a1;
            }}
        </style>
        """, unsafe_allow_html=True)

        # Compact cards for each metric
        st.markdown(f"""
        <div class="card">
            <div class="left">
                <div class="card-title">Total Buy Signals</div>
            </div>
            <div class="right">
                <div class="stat-number">{total_signals}</div>
            </div>
        </div>

        <div class="card">
            <div class="left">
                <div class="card-title">Success Rate of Buy Signals</div>
                <div class="card-title">(Within {average_days_to_gain} days)</div>
            </div>
            <div class="right">
                <div class="stat-number">{success_rate:.2f}%</div>
            </div>
        </div>

        <div class="card">
            <div class="left">
                <div class="card-title">Partially Successful Buy Signals</div>
                <div class="card-title">(Within {upper_range_days_to_gain} days)</div>
            </div>
            <div class="right">
                <div class="stat-number">{partially_successful_signals}</div>
            </div>
        </div>

        <div class="card">
            <div class="left">
                <div class="card-title">Failed Buy Signals</div>
                <div class="card-title">(Beyond {upper_range_days_to_gain} days)</div>
            </div>
            <div class="right">
                <div class="stat-number">{failed_signals}</div>
            </div>
        </div>

        <div class="card">
            <div class="left">
                <div class="card-title">Additional Stats</div>
                <div class="card-title">Average Days to Gain 7%: {average_days_to_gain}</div>
                <div class="card-title">Standard Deviation Upper Range: {upper_range_days_to_gain} days</div>
                <div class="card-title">Max Duration to Gain 7%: {int(data['Time_to_Gain'].max())} days</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show the data for failed signals
        st.subheader("Details of Failed Signals")
        failed_signal_data = data[data['Failed_Signal']][['Close', 'EMA200', 'EMA200_Weekly', 'RSI_Weekly', 'Time_to_Gain', 'Period_to_Gain']]
        st.dataframe(failed_signal_data)

        # Show the data for partially successful signals
        st.subheader("Details of Partially Successful Buy Signals")
        partially_successful_signal_data = data[(data['Buy_Signal']) & (data['Partially_Successful_Signal'])][['Close', 'EMA200', 'EMA200_Weekly', 'RSI_Weekly', 'Time_to_Gain', 'Period_to_Gain']]
        st.dataframe(partially_successful_signal_data)

        # Show the


        # Show the data for successful signals where buy signals were formed and succeeded
        st.subheader("Details of Successful Buy Signals")
        successful_signal_data = data[(data['Buy_Signal']) & (data['Successful_Signal'])][['Close', 'EMA200', 'EMA200_Weekly', 'RSI_Weekly', 'Time_to_Gain', 'Period_to_Gain']]
        st.dataframe(successful_signal_data)


        # Define the full data range for calculations (from 2010 to today)
        start_date = '2010-01-01'
        end_date = datetime.today().strftime('%Y-%m-%d')

        # Define the last 100 days range
        last_100_days_start = (datetime.today() - timedelta(days=100)).strftime('%Y-%m-%d')

        # List of Nifty 50 stocks (sample list)
        nifty_50_stocks = [
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "HINDUNILVR.NS", "ICICIBANK.NS", 
            "KOTAKBANK.NS", "LT.NS", "BHARTIARTL.NS", "ITC.NS", "AXISBANK.NS", "SBIN.NS", "WIPRO.NS", 
            "BAJFINANCE.NS", "MARUTI.NS", "HCLTECH.NS", "ADANIPORTS.NS", "POWERGRID.NS", "ULTRACEMCO.NS", 
            "NTPC.NS", "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "ONGC.NS", "BAJAJFINSV.NS", 
            "TECHM.NS", "GRASIM.NS", "TATASTEEL.NS", "HDFC.NS", "JSWSTEEL.NS", "COALINDIA.NS", 
            "BPCL.NS", "SHREECEM.NS", "DRREDDY.NS", "INDUSINDBK.NS", "HDFCLIFE.NS", "DIVISLAB.NS", 
            "UPL.NS", "M&M.NS", "HEROMOTOCO.NS", "BRITANNIA.NS", "CIPLA.NS", "NESTLEIND.NS", 
            "SBILIFE.NS", "EICHERMOT.NS", "TATAMOTORS.NS", "HINDALCO.NS", "MTARTECH.NS", "ATGL.NS", "IDEA.NS", "BATAINDIA.NS","BAJAJ-AUTO.NS", "TATACONSUM.NS"
        ]

                # Create a dataframe to store the latest buy signal
        latest_signal = pd.DataFrame(columns=['Stock', 'Buy Signal Date', 'Buy Signal Price', 'CMP', '% Change from Buy Signal', 'EMA 200 Daily', 'EMA 200 Weekly'])

        # Loop through each stock in the Nifty 50 list
        for stock in nifty_50_stocks:
            ticker = stock

            # Fetch data for the stock from 2010 onward
            full_data = yf.download(ticker, start=start_date, end=end_date)

            # Ensure data is loaded
            if full_data.empty:
                continue

            # Calculate Daily EMA 200
            full_data['EMA200'] = calculate_ema(full_data['Close'], 200)

            # Calculate Weekly EMA 200 and RSI
            weekly_data = full_data['Close'].resample('W').last()
            weekly_ema200 = calculate_ema(weekly_data, 200)
            full_data['EMA200_Weekly'] = weekly_ema200.reindex(full_data.index, method='ffill')
            full_data['RSI_Weekly'] = calculate_rsi(weekly_data, 14).reindex(full_data.index, method='ffill')

            # Initialize variable to store the most recent signal
            most_recent = None

            # Loop through the data to find the latest signal
            for i in range(1, len(full_data)):
                cmp = full_data['Close'].iloc[i]
                ema_200_daily = full_data['EMA200'].iloc[i]
                ema_200_weekly = full_data['EMA200_Weekly'].iloc[i]
                rsi_weekly_latest = full_data['RSI_Weekly'].iloc[i]

                # Check buy condition (CMP < EMA 200 Daily, CMP < EMA 200 Weekly, RSI < 40)
                if cmp < ema_200_daily and cmp < ema_200_weekly and rsi_weekly_latest < 30:
                    buy_signal_date = full_data.index[i]
                    # Only consider signals within the last 100 days
                    if buy_signal_date >= pd.Timestamp(last_100_days_start):
                        # Store the most recent signal
                        most_recent = {
                            'Stock': ticker,
                            'Buy Signal Date': buy_signal_date,
                            'Buy Signal Price': cmp,
                            'EMA 200 Daily': ema_200_daily,
                            'EMA 200 Weekly': ema_200_weekly
                        }

            # If a signal was found, add the most recent one to the table
            if most_recent:
                # Fetch the latest CMP
                current_cmp = full_data['Close'].iloc[-1]
                percentage_change = ((current_cmp - most_recent['Buy Signal Price']) / most_recent['Buy Signal Price']) * 100

                # Add the signal to the dataframe
                signal_data = pd.DataFrame({
                    'Stock': [most_recent['Stock']],
                    'Buy Signal Date': [most_recent['Buy Signal Date'].strftime('%Y-%m-%d')],
                    'Buy Signal Price': [most_recent['Buy Signal Price']],
                    'CMP': [current_cmp],
                    '% Change from Buy Signal': [percentage_change],
                    'EMA 200 Daily': [most_recent['EMA 200 Daily']],
                    'EMA 200 Weekly': [most_recent['EMA 200 Weekly']]
                })
                latest_signal = pd.concat([latest_signal, signal_data], ignore_index=True)

        # Sort by the most recent signal date
        latest_signal['Buy Signal Date'] = pd.to_datetime(latest_signal['Buy Signal Date'])
        latest_signal = latest_signal.sort_values(by='Buy Signal Date', ascending=False)

        # Display the latest signal with user-friendly presentation
        st.subheader("📈 **Latest Buy Signals (Last 100 Days)**")

        if not latest_signal.empty:
            # Display a summary of the signals
            total_signals = len(latest_signal)
            st.markdown(f"""
            <div style="padding:10px; background-color:#007BFF; border-radius:5px; color:white; text-align:center; font-weight:bold;">
                Total Buy Signals Found: {total_signals}
            </div>
            """, unsafe_allow_html=True)

            # Style the table using pandas styling
            styled_table = latest_signal.style.applymap(
                lambda x: 'background-color: #28a745; color: white;' if x > 0 else 'background-color: #dc3545; color: white;', 
                subset=['% Change from Buy Signal']
            ).format({
                'Buy Signal Price': '₹{:.2f}',
                'CMP': '₹{:.2f}',
                '% Change from Buy Signal': '{:.2f}%',
                'EMA 200 Daily': '₹{:.2f}',
                'EMA 200 Weekly': '₹{:.2f}'
            })

            # Display the styled table
            st.dataframe(latest_signal)

            # Option to download the data
            st.download_button(
                label="📥 Download Latest Buy Signal Data",
                data=latest_signal.to_csv(index=False),
                file_name="latest_buy_signal.csv",
                mime="text/csv"
            )
        else:
            st.markdown("<p style='font-size:16px; color:red;'>No buy signals were triggered in the last 100 days.</p>", unsafe_allow_html=True)
            
    elif section == "Buy Signals based on average historical correction data":
        st.title("📊 Average historical correction data")
 


        # Custom CSS to improve the layout and look
        st.markdown("""
            <style>
                /* General styling for the dashboard */
                body {
                    background-color: #f5f7fa;
                }




                /* Styling the header */
                .stTitle {
                    color: #004085;
                    font-weight: bold;
                    font-size: 28px;
                }
            
                .stSubheader {
                    color: #004085;
                    font-size: 24px;
                    margin-bottom: 20px;
                }




                /* Styling for cards */
                .card {
                    background-color: #ffffff;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 10px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    height: 100%;
                }
                .card-title {
                    font-size: 18px;
                    font-weight: bold;
                    color: #495057;
                    margin-bottom: 10px;
                }
                .card-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #007BFF;
                    margin-bottom: 10px;
                }
                .card-subtext {
                    font-size: 14px;
                    color: #6c757d;
                }




                /* Styling for category ratios dropdown */
                .dropdown-box {
                    background-color: #007bff;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
                    font-size: 16px;
                }




                /* Styling for overall summary section */
                .overall-summary {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    gap: 20px;
                }
                .summary-card {
                    flex: 1;
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
                    min-width: 250px;
                }




                /* Styling for advanced features */
                .advanced-feature {
                    background-color: #e9ecef;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
                }
            </style>
        """, unsafe_allow_html=True)




        # Creating tabs for each subsection
        tab1,tab2 = st.tabs(["📈 EMA 200 Analysis", "🔔 Signals"])




        with tab1:
            #st.subheader("📈 EMA 200 Analysis")
            st.subheader(f"📈 EMA 200 Analysis {selected_stock}")



            # Fetch stock data from the sidebar-selected stock using yfinance
            data = yf.download(ticker, start="2010-01-01")


            # Ensure data is available
            if data.empty:
                st.warning("⚠️ No data available for the selected stock.")
            else:
                # Calculate the 200-day EMA
                data['EMA200'] = data['Close'].ewm(span=200, adjust=False).mean()

                # Variables to track fall periods and store data
                fall_periods = []
                below_ema = False
                start_idx = None
                lowest_price = None
                bottom_date = None

                # Iterate through the data to find periods where price falls below EMA 200
                for i in range(1, len(data)):
                    if data['Close'].iloc[i] < data['EMA200'].iloc[i]:
                        if not below_ema:
                            below_ema = True
                            start_idx = i
                            lowest_price = data['Low'].iloc[i]
                            bottom_date = data.index[i]
                        else:
                            if data['Low'].iloc[i] < lowest_price:
                                lowest_price = data['Low'].iloc[i]
                                bottom_date = data.index[i]
                    else:
                        if below_ema:
                            duration_to_bottom = (bottom_date - data.index[start_idx]).days
                            duration_to_cross_above = (data.index[i] - bottom_date).days
                            total_duration = (data.index[i] - data.index[start_idx]).days
                            fall_percentage = ((data['Close'].iloc[start_idx] - lowest_price) / data['Close'].iloc[start_idx]) * 100
                            fall_percentage = round(fall_percentage, 2)

                            # Add % sign to fall percentage
                            fall_percentage_str = f"{fall_percentage}%"

                            # Categorizing based on fall percentage
                            if 0 < fall_percentage <= 2:
                                category = "0 to 2%"
                            elif 2 < fall_percentage <= 5:
                                category = "2 to 5%"
                            elif 5 < fall_percentage <= 10:
                                category = "5 to 10%"
                            elif 10 < fall_percentage <= 20:
                                category = "10 to 20%"
                            else:
                                category = "20% and above"

                            status = "Completed"

                            fall_periods.append({
                                'Date Crossed Below EMA 200': data.index[start_idx].strftime('%B %d, %Y'),
                                'Price Crossed Below': round(data['Close'].iloc[start_idx], 2),
                                'Bottom Date': bottom_date.strftime('%B %d, %Y'),
                                'Bottom Price': round(lowest_price, 2),
                                'Date Crossed Above EMA 200': data.index[i].strftime('%B %d, %Y'),
                                'Price Crossed Above': round(data['Close'].iloc[i], 2),
                                'Duration to Bottom (Days)': int(duration_to_bottom),  # Convert to integer
                                'Duration to Cross Above EMA 200 (Days)': int(duration_to_cross_above),  # Convert to integer
                                'Total Duration (Days)': int(total_duration),  # Convert to integer
                                'Fall %': fall_percentage_str,
                                'Category': category,
                                'Status': status
                            })
                        below_ema = False

                # Get the most recent data
                latest_data = data.iloc[-1]
                latest_cmp = latest_data['Close']
                latest_ema200 = latest_data['EMA200']

                # Check if the price is below the EMA 200 and calculate the current fall percentage
                if latest_cmp < latest_ema200:
                    current_status = "Still Below"
                    percentage_below_ema = ((latest_ema200 - latest_cmp) / latest_ema200) * 100
                    percentage_below_ema = round(percentage_below_ema, 2)
                    percentage_below_ema_str = f"{percentage_below_ema}%"

                    fall_periods.append({
                        'Date Crossed Below EMA 200': latest_data.name.strftime('%B %d, %Y'),
                        'Price Crossed Below': round(latest_cmp, 2),
                        'Bottom Date': "To be updated",
                        'Bottom Price': "To be updated",
                        'Date Crossed Above EMA 200': "To be updated",
                        'Price Crossed Above': "To be updated",
                        'Duration to Bottom (Days)': "To be updated",
                        'Duration to Cross Above EMA 200 (Days)': "To be updated",
                        'Total Duration (Days)': "To be updated",
                        'Fall %': percentage_below_ema_str,
                        'Category': "To be categorized",
                        'Status': current_status,
                    })

                fall_periods_df = pd.DataFrame(fall_periods)

                # Display current market price and EMA
                st.write(f"**📉 Current Market Price (CMP):** {round(latest_cmp, 2)}")
                st.write(f"**🔄 Latest EMA 200:** {round(latest_ema200, 2)}")

                if latest_cmp < latest_ema200:
                    st.warning(f"The current price is still below the EMA 200 by {percentage_below_ema_str}.")
                else:
                    st.success("The current price has crossed above the EMA 200.")

                # Display the fall periods DataFrame
                st.write("### 📊 EMA 200 Analysis Data Table")
                st.dataframe(fall_periods_df)

                # Separate completed and running counts
                completed_events = fall_periods_df[fall_periods_df['Status'] == "Completed"]
                running_events = fall_periods_df[fall_periods_df['Status'] == "Still Below"]

                # Display counts with appropriate conditions
                if not completed_events.empty:
                    st.write(f"**📝 Total Completed Events Count:** {completed_events.shape[0]}")

                if not running_events.empty:
                    running_count = len(running_events)
                    st.write(f"**⏳ Running Count (Still Below EMA 200):** {running_count}")
                else:
                    st.write(f"**⏳ Running Count (Still Below EMA 200):** 0")

                # Update and display the total completed events if conditions are met
                if not completed_events.empty and running_events.empty:
                    updated_completed_count = completed_events.shape[0]
                    st.write(f"**🔄 Updated Total Completed Events Count:** {updated_completed_count}")


                if not completed_events.empty:
                    completed_events['Category'] = pd.cut(
                        completed_events['Fall %'].str.replace('%', '').astype(float),
                        bins=[0, 2, 5, 10, 20, float('inf')],
                        labels=["0 to 2%", "2 to 5%", "5 to 10%", "10 to 20%", "20% and above"],
                        right=True
                    )




                    # Adding a column for the ratio of events in each category
                    total_completed_events = completed_events.shape[0]
                    category_summary_list = []
                    for category in ["0 to 2%", "2 to 5%", "5 to 10%", "10 to 20%", "20% and above"]:
                        category_df = completed_events[completed_events['Category'] == category]




                        if not category_df.empty:
                            category_counts = category_df.shape[0]
                            category_median = category_df['Fall %'].str.replace('%', '').astype(float).median()
                            category_average = category_df['Fall %'].str.replace('%', '').astype(float).mean()
                            category_max_fall = category_df['Fall %'].str.replace('%', '').astype(float).max()
                            category_ratio = (category_counts / total_completed_events) * 100
                            category_ratio_str = f"{round(category_ratio, 2)}%"




                            # Find the row corresponding to the max fall % to display the period
                            max_fall_period_row = category_df.loc[category_df['Fall %'].str.replace('%', '').astype(float).idxmax()]
                            max_fall_period = f"{max_fall_period_row['Date Crossed Below EMA 200']} - {max_fall_period_row['Bottom Date']}"




                            category_avg_duration_bottom = int(category_df['Duration to Bottom (Days)'].mean())
                            category_avg_duration_cross = int(category_df['Duration to Cross Above EMA 200 (Days)'].mean())
                            category_total_duration_avg = int(category_df['Total Duration (Days)'].mean())
                            category_max_total_duration = int(category_df['Total Duration (Days)'].max())




                            category_summary_list.append({
                                'Category': category,
                                'Count': category_counts,
                                'Median Fall %': f"{round(category_median, 2)}%",
                                'Average Fall %': f"{round(category_average, 2)}%",
                                'Max Fall %': f"{round(category_max_fall, 2)}%",
                                'Max Fall % Period': max_fall_period,
                                'Avg Duration to Bottom (Days)': category_avg_duration_bottom,  # No decimal places
                                'Avg Duration to Cross Above EMA (Days)': category_avg_duration_cross,  # No decimal places
                                'Avg Total Duration (Days)': category_total_duration_avg,  # No decimal places
                                'Max Total Duration (Days)': category_max_total_duration,  # No decimal places
                                'Ratio of % Fall': category_ratio_str
                            })




                    category_summary = pd.DataFrame(category_summary_list)




                    # Convert "Average Fall %" to numeric for calculations
                    category_summary['Average Fall %'] = category_summary['Average Fall %'].str.replace('%', '').astype(float)
                    category_summary['Average Fall %'] = category_summary['Average Fall %'].apply(lambda x: f"{x:.2f}%")




                    # Enhanced Data Table with colors
                    st.write("### 🗂️ Fall % Category Summary (with Ratio of % Fall)")
                    st.dataframe(category_summary.style.background_gradient(cmap="Blues"))




                    # Adding graphical representation for the ratio and average fall %
                    st.write("### 📊 Interactive Graph of Fall % Categories")




                    # Enhanced bar chart to show average fall % and ratio
                    fig = px.bar(
                        category_summary,
                        x='Category',
                        y='Average Fall %',
                        hover_data=['Count', 'Median Fall %', 'Max Fall %', 'Ratio of % Fall', 'Avg Duration to Bottom (Days)',
                                    'Avg Duration to Cross Above EMA (Days)', 'Avg Total Duration (Days)', 'Max Total Duration (Days)'],
                        color='Average Fall %',
                        text='Count',
                        labels={'Average Fall %': 'Average Fall %', 'Count': 'Event Count'},
                        title="📊 Average Fall % and Event Count by Category (with Ratio)",
                        color_continuous_scale=px.colors.sequential.Viridis  # Choose an attractive color scale
                    )




                    # Update the text and layout for an advanced look
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    fig.update_layout(
                        uniformtext_minsize=8,
                        uniformtext_mode='hide',
                        xaxis_title='Category',
                        yaxis_title='Average Fall %',
                        coloraxis_colorbar=dict(
                            title="Average Fall %",
                            tickvals=[0, 5, 10, 15, 20],
                            ticktext=['0%', '5%', '10%', '15%', '20%']
                        ),
                        title={
                            'text': "📊 Average Fall % and Event Count by Category (with Ratio)",
                            'y': 0.9,
                            'x': 0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'
                        },
                        plot_bgcolor='rgba(0, 0, 0, 0)',  # Transparent background for cleaner visuals
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                        font=dict(size=12),
                    )




                    # Display the updated chart
                    st.plotly_chart(fig)




                                # Enhanced Overall Summary with Dropdown for Category Ratios (Improved Look)




                    # Enhanced Overall Summary with Dropdown for Category Ratios (Improved Look)




                    # Prepare summary content
                    fall_percentages = completed_events['Fall %'].str.replace('%', '').astype(float)
                    durations_to_bottom = completed_events['Duration to Bottom (Days)'].astype(float)
                    durations_to_cross = completed_events['Duration to Cross Above EMA 200 (Days)'].astype(float)
                    total_durations = completed_events['Total Duration (Days)'].astype(float)




                    avg_fall_percentage = round(fall_percentages.mean(), 2)
                    max_fall_percentage = round(fall_percentages.max(), 2)
                    std_dev_fall_percentage = round(fall_percentages.std(), 2)




                    avg_duration_to_bottom = int(durations_to_bottom.mean())
                    max_duration_to_bottom = int(durations_to_bottom.max())




                    avg_duration_to_cross = int(durations_to_cross.mean())
                    max_total_duration = int(total_durations.max())




                    # Ratio summary for the dropdown
                    ratio_summary = ', '.join([f"{row['Category']}: {row['Ratio of % Fall']}" for _, row in category_summary.iterrows()])




                    # Advanced CSS for professional colors, animations, and a more polished look
                    st.markdown("""
                        <style>
                            /* General layout styling */
                            .overall-summary {
                                display: flex;
                                flex-wrap: wrap;
                                justify-content: space-between;
                                gap: 20px;
                            }




                            /* Card design with gradient and hover effect */
                            .summary-card {
                                background: linear-gradient(135deg, #f9fafc, #f0f1f5);
                                border-radius: 12px;
                                padding: 20px;
                                margin: 10px;
                                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.08);
                                transition: transform 0.3s, box-shadow 0.3s;
                                cursor: pointer;
                                min-width: 250px;
                                flex: 1;
                            }




                            /* Hover effect for the cards */
                            .summary-card:hover {
                                transform: translateY(-6px);
                                box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.15);
                            }




                            /* Professional card title styling */
                            .card-title {
                                font-size: 16px;
                                font-weight: bold;
                                color: #343a40;
                                margin-bottom: 8px;
                            }




                            /* Styling for card values with professional color */
                            .card-value {
                                font-size: 30px;
                                font-weight: bold;
                                color: #2f3640;
                                margin-bottom: 5px;
                                animation: fadeIn 1s ease-in-out;
                            }




                            /* Card subtext styling */
                            .card-subtext {
                                font-size: 14px;
                                color: #6c757d;
                            }




                            /* Animated counters for values */
                            @keyframes fadeIn {
                                0% { opacity: 0; }
                                100% { opacity: 1; }
                            }




                            /* Enhanced styling for dropdown box */
                            .dropdown-box {
                                background: #6c757d;
                                color: white;
                                padding: 10px;
                                border-radius: 8px;
                                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
                                font-size: 16px;
                                text-align: center;
                                transition: background 0.3s;
                            }




                            /* Subtle hover effect for the dropdown */
                            .dropdown-box:hover {
                                background: #495057;
                            }




                            /* Styling for the ratio display with emphasis */
                            .ratio-display {
                                font-size: 28px;
                                font-weight: bold;
                                color: #495057;
                                background: #f0f2f5;
                                padding: 15px;
                                border-radius: 10px;
                                text-align: center;
                                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.08);
                                transition: transform 0.3s;
                            }




                            .ratio-display:hover {
                                transform: translateY(-4px);
                            }




                            /* Icon style to make ratio display more engaging */
                            .ratio-icon {
                                font-size: 24px;
                                color: #6c757d;
                                margin-right: 8px;
                            }




                        </style>
                    """, unsafe_allow_html=True)




                    # Display the summary statistics in cards
                    st.markdown("""
                    <div class="overall-summary">
                        <div class="summary-card">
                            <div class="card-title">Average Fall %</div>
                            <div class="card-value">"""+str(avg_fall_percentage)+"""%</div>
                            <div class="card-subtext">Across all events</div>
                        </div>
                        <div class="summary-card">
                            <div class="card-title">Maximum Fall %</div>
                            <div class="card-value">"""+str(max_fall_percentage)+"""%</div>
                            <div class="card-subtext">Highest recorded</div>
                        </div>
                        <div class="summary-card">
                            <div class="card-title">Std. Deviation of Fall %</div>
                            <div class="card-value">"""+str(std_dev_fall_percentage)+"""%</div>
                            <div class="card-subtext">Measure of variability</div>
                        </div>
                        <div class="summary-card">
                            <div class="card-title">Avg. Duration to Bottom</div>
                            <div class="card-value">"""+str(avg_duration_to_bottom)+""" days</div>
                            <div class="card-subtext">Average time to reach bottom</div>
                        </div>
                        <div class="summary-card">
                            <div class="card-title">Max Duration to Bottom</div>
                            <div class="card-value">"""+str(max_duration_to_bottom)+""" days</div>
                            <div class="card-subtext">Longest time to reach bottom</div>
                        </div>
                        <div class="summary-card">
                            <div class="card-title">Max Total Duration</div>
                            <div class="card-value">"""+str(max_total_duration)+""" days</div>
                            <div class="card-subtext">Longest event duration</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


                    # Dropdown for category ratios with a modern look
                    category_selected = st.selectbox("Select Category", category_summary['Category'])
                    ratio_selected = category_summary.loc[category_summary['Category'] == category_selected, 'Ratio of % Fall'].values[0]

                    # Display the selected ratio in a more engaging format
                    st.markdown(f"""
                    <div class="ratio-display">
                        <span class="ratio-icon">📊</span>
                        {category_selected}: {ratio_selected}
                    </div>
                    """, unsafe_allow_html=True)

                    # Filter the category summary based on the selected category
                    selected_category_data = category_summary[category_summary['Category'] == category_selected]

                    # Extract relevant metrics for the selected category
                    if not selected_category_data.empty:
                        avg_fall_percentage_selected = selected_category_data['Average Fall %'].iloc[0]
                        max_fall_percentage_selected = selected_category_data['Max Fall %'].iloc[0]
                        avg_total_duration_selected = selected_category_data['Avg Total Duration (Days)'].iloc[0]
                        max_total_duration_selected = selected_category_data['Max Total Duration (Days)'].iloc[0]

                        # Display the metrics in a visually appealing format
                        st.markdown(f"""
                        <div class="overall-summary">
                            <div class="summary-card">
                                <div class="card-title">Average Fall % ({category_selected})</div>
                                <div class="card-value">{avg_fall_percentage_selected}</div>
                                <div class="card-subtext">Category Average Fall %</div>
                            </div>
                            <div class="summary-card">
                                <div class="card-title">Max Fall % ({category_selected})</div>
                                <div class="card-value">{max_fall_percentage_selected}</div>
                                <div class="card-subtext">Category Max Fall %</div>
                            </div>
                            <div class="summary-card">
                                <div class="card-title">Average Total Duration ({category_selected})</div>
                                <div class="card-value">{avg_total_duration_selected} days</div>
                                <div class="card-subtext">Average Total Duration for Category</div>
                            </div>
                            <div class="summary-card">
                                <div class="card-title">Max Total Duration ({category_selected})</div>
                                <div class="card-value">{max_total_duration_selected} days</div>
                                <div class="card-subtext">Maximum Total Duration for Category</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("No data available for the selected category.")


        with tab2:
            st.subheader("🔔 Signals")
            st.info("These are the Nifty 50 stocks where the CMP is currently below the EMA 200, along with the total count of falls, the average % fall, the historical count of falls in the current fall category, and the success rate based on staying below EMA 200 for less than 90 days.")


            # List of Nifty 50 stock tickers
            nifty50_tickers = [
                "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "HINDUNILVR.NS", "ICICIBANK.NS", 
                "KOTAKBANK.NS", "LT.NS", "BHARTIARTL.NS", "ITC.NS", "AXISBANK.NS", "SBIN.NS", "WIPRO.NS", 
                "BAJFINANCE.NS", "MARUTI.NS", "HCLTECH.NS", "ADANIPORTS.NS", "POWERGRID.NS", "ULTRACEMCO.NS", 
                "NTPC.NS", "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "ONGC.NS", "BAJAJFINSV.NS", 
                "TECHM.NS", "GRASIM.NS", "TATASTEEL.NS", "HDFC.NS", "JSWSTEEL.NS", "COALINDIA.NS", 
                "BPCL.NS", "SHREECEM.NS", "DRREDDY.NS", "INDUSINDBK.NS", "HDFCLIFE.NS", "DIVISLAB.NS", 
                "UPL.NS", "M&M.NS", "HEROMOTOCO.NS", "BRITANNIA.NS", "CIPLA.NS", "NESTLEIND.NS", 
                "SBILIFE.NS", "EICHERMOT.NS", "TATAMOTORS.NS", "HINDALCO.NS", "MTARTECH.NS", "ATGL.NS", "IDEA.NS", "BATAINDIA.NS"
            ]


            # Data structure to store the results
            stock_details = []


            # Loop through each Nifty 50 stock ticker
            for ticker in nifty50_tickers:
                # Normalize the ticker format
                normalized_ticker = ticker.replace('.NS', '').upper().strip()

                stock_data = yf.download(ticker, start="2010-01-01")
                if stock_data.empty:
                    continue  # Skip if no data is available

                # Calculate the 200-day EMA
                stock_data['EMA200'] = stock_data['Close'].ewm(span=200, adjust=False).mean()

                # Initialize counters and lists for various categories
                total_cross_below_ema_count = 0  # Initialize the counter for total crosses below EMA 200
                success_counts = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
                total_counts = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
                all_falls = {'0 to 2%': [], '2 to 5%': [], '5 to 10%': [], '10 to 20%': [], '20% and above': []}

                below_ema_event = False
                for i in range(1, len(stock_data)):
                    close = stock_data['Close'].iloc[i]
                    ema200 = stock_data['EMA200'].iloc[i]
                    prev_close = stock_data['Close'].iloc[i - 1]
                    prev_ema200 = stock_data['EMA200'].iloc[i - 1]

                    if close < ema200 and prev_close >= prev_ema200:
                        below_ema_event = True
                        event_start_date = stock_data.index[i]
                        event_max_fall = 0
                        total_cross_below_ema_count += 1  # Increment the count when a cross below EMA 200 occurs

                    if below_ema_event:
                        percentage_fall = ((ema200 - close) / ema200) * 100
                        event_max_fall = max(event_max_fall, percentage_fall)

                    if below_ema_event and close > ema200:
                        below_ema_event = False
                        event_duration = (stock_data.index[i] - event_start_date).days

                        if event_max_fall <= 2:
                            category = '0 to 2%'
                        elif 2 < event_max_fall <= 5:
                            category = '2 to 5%'
                        elif 5 < event_max_fall <= 10:
                            category = '5 to 10%'
                        elif 10 < event_max_fall <= 20:
                            category = '10 to 20%'
                        else:
                            category = '20% and above'

                        all_falls[category].append(event_max_fall)
                        total_counts[category] += 1

                        # Determine success based on duration
                        if event_duration <= 90:
                            success_counts[category] += 1

                # Calculate success rates for each category
                success_rates = {category: (success_counts[category] / total_counts[category] * 100) if total_counts[category] > 0 else 0 for category in total_counts}

                # Get the latest data points
                latest_close = stock_data['Close'].iloc[-1]
                latest_ema200 = stock_data['EMA200'].iloc[-1]

                if latest_close <= latest_ema200:
                    percentage_fall = ((latest_ema200 - latest_close) / latest_ema200) * 100
                    percentage_fall = round(percentage_fall, 2)

                    if percentage_fall <= 2:
                        fall_category = "0 to 2%"
                        historical_count = total_counts['0 to 2%']
                        avg_fall = round(sum(all_falls['0 to 2%']) / len(all_falls['0 to 2%']), 2) if all_falls['0 to 2%'] else "N/A"
                        success_rate = success_rates['0 to 2%']
                    elif 2 < percentage_fall <= 5:
                        fall_category = "2 to 5%"
                        historical_count = total_counts['2 to 5%']
                        avg_fall = round(sum(all_falls['2 to 5%']) / len(all_falls['2 to 5%']), 2) if all_falls['2 to 5%'] else "N/A"
                        success_rate = success_rates['2 to 5%']
                    elif 5 < percentage_fall <= 10:
                        fall_category = "5 to 10%"
                        historical_count = total_counts['5 to 10%']
                        avg_fall = round(sum(all_falls['5 to 10%']) / len(all_falls['5 to 10%']), 2) if all_falls['5 to 10%'] else "N/A"
                        success_rate = success_rates['5 to 10%']
                    elif 10 < percentage_fall <= 20:
                        fall_category = "10 to 20%"
                        historical_count = total_counts['10 to 20%']
                        avg_fall = round(sum(all_falls['10 to 20%']) / len(all_falls['10 to 20%']), 2) if all_falls['10 to 20%'] else "N/A"
                        success_rate = success_rates['10 to 20%']
                    else:
                        fall_category = "20% and above"
                        historical_count = total_counts['20% and above']
                        avg_fall = round(sum(all_falls['20% and above']) / len(all_falls['20% and above']), 2) if all_falls['20% and above'] else "N/A"
                        success_rate = success_rates['20% and above']

                    stock_details.append({
                        'Stock': normalized_ticker,  # Use normalized stock ticker
                        'CMP': round(latest_close, 2),
                        'EMA 200': round(latest_ema200, 2),
                        '% Fall from EMA 200': percentage_fall,
                        'Fall Category': fall_category,
                        'Historical Count in Category': historical_count,
                        'Avg Fall in Category (%)': avg_fall,
                        'Total Crosses Below EMA 200': total_cross_below_ema_count,
                        'Success Rate (%)': round(success_rate, 2)
                    })

            # Create a DataFrame from the stock details
            stock_details_df = pd.DataFrame(stock_details)


            if not stock_details_df.empty:
                def highlight_row(row):
                    # Highlight entire row if the % Fall from EMA 200 is greater than or equal to the Avg Fall in the category
                    if row['% Fall from EMA 200'] >= row['Avg Fall in Category (%)']:
                        return ['background-color: yellow'] * len(row)
                    else:
                        return [''] * len(row)


                st.write("📉 The following Nifty 50 stocks are currently below their EMA 200.")
                st.dataframe(stock_details_df.style.apply(highlight_row, axis=1).format({
                    "% Fall from EMA 200": "{:.2f}", 
                    "EMA 200": "{:.2f}", 
                    "Success Rate (%)": "{:.2f}"
                }))
            else:
                st.write("✅ All Nifty 50 stocks are currently above their EMA 200.")

            # --- Success Rate Table Section ---
            selected_stock = st.selectbox("Select a Nifty 50 stock for success rate stats:", nifty50_tickers)


            # Data structure to store success/failure counts, max duration, average % fall, max % fall, and ratios
            success_counts = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            failure_counts = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            max_duration = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            avg_duration_total = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            avg_duration_success = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            max_falls = {'0 to 2%': 0, '2 to 5%': 0, '5 to 10%': 0, '10 to 20%': 0, '20% and above': 0}
            all_falls = {'0 to 2%': [], '2 to 5%': [], '5 to 10%': [], '10 to 20%': [], '20% and above': []}
            all_durations = {'0 to 2%': [], '2 to 5%': [], '5 to 10%': [], '10 to 20%': [], '20% and above': []}


            # Logic to calculate falls for the selected stock
            stock_data = yf.download(selected_stock, start="2010-01-01")
            if not stock_data.empty:
                stock_data['EMA200'] = stock_data['Close'].ewm(span=200, adjust=False).mean()
                below_ema_event = False
                event_start_date = None


                for i in range(1, len(stock_data)):
                    close = stock_data['Close'].iloc[i]
                    ema200 = stock_data['EMA200'].iloc[i]
                    prev_close = stock_data['Close'].iloc[i - 1]
                    prev_ema200 = stock_data['EMA200'].iloc[i - 1]


                    if close < ema200 and prev_close >= prev_ema200:
                        below_ema_event = True
                        event_start_date = stock_data.index[i]
                        event_max_fall = 0


                    if below_ema_event:
                        percentage_fall = ((ema200 - close) / ema200) * 100
                        event_max_fall = max(event_max_fall, percentage_fall)


                    if below_ema_event and close > ema200:
                        below_ema_event = False
                        event_duration = (stock_data.index[i] - event_start_date).days


                        if event_max_fall <= 2:
                            fall_category = '0 to 2%'
                        elif 2 < event_max_fall <= 5:
                            fall_category = '2 to 5%'
                        elif 5 < event_max_fall <= 10:
                            fall_category = '5 to 10%'
                        elif 10 < event_max_fall <= 20:
                            fall_category = '10 to 20%'
                        else:
                            fall_category = '20% and above'


                        all_falls[fall_category].append(event_max_fall)
                        all_durations[fall_category].append(event_duration)
                        max_duration[fall_category] = max(max_duration[fall_category], event_duration)
                        max_falls[fall_category] = max(max_falls[fall_category], event_max_fall)


                        if event_duration <= 90:
                            success_counts[fall_category] += 1
                        else:
                            failure_counts[fall_category] += 1


            # Calculate total counts, success rates, and ratios
            total_counts = {category: success_counts[category] + failure_counts[category] for category in success_counts}
            success_rates = {category: (success_counts[category] / total_counts[category] * 100) if total_counts[category] > 0 else 0 for category in total_counts}
            ratios = {category: (total_counts[category] / sum(total_counts.values()) * 100) if sum(total_counts.values()) > 0 else 0 for category in total_counts}
            avg_falls = {category: round(sum(all_falls[category]) / len(all_falls[category]), 2) if all_falls[category] else "N/A" for category in all_falls}
            avg_duration_total = {category: int(round(sum(all_durations[category]) / len(all_durations[category]))) if all_durations[category] else "N/A" for category in all_durations}
            avg_duration_success = {
                category: int(round(sum(d for d in all_durations[category] if d <= 90) / len([d for d in all_durations[category] if d <= 90])))
                if len([d for d in all_durations[category] if d <= 90]) > 0 else "N/A" for category in all_durations
            }


            success_rate_df = pd.DataFrame({
                'Fall Category': list(total_counts.keys()),
                'Total Count': list(total_counts.values()),
                'Success Count': list(success_counts.values()),
                'Failure Count': list(failure_counts.values()),
                'Success Rate (%)': [round(success_rates[category], 2) for category in success_rates],
                'Max Duration (Days)': list(max_duration.values()),
                'Avg Duration (Total) (Days)': list(avg_duration_total.values()),
                'Avg Duration (Success) (Days)': list(avg_duration_success.values()),
                'Avg Fall (%)': list(avg_falls.values()),
                'Max Fall (%)': list(max_falls.values()),
                'Ratio (%)': [round(ratios[category], 2) for category in ratios]
            })


            st.write(f"📊 Success rates and statistics for {selected_stock}:")
            st.dataframe(success_rate_df.style.format({
                "Success Rate (%)": "{:.2f}", 
                "Ratio (%)": "{:.2f}", 
                "Avg Fall (%)": "{:.2f}", 
                "Max Fall (%)": "{:.2f}", 
                "Avg Duration (Total) (Days)": "{:d}", 
                "Avg Duration (Success) (Days)": "{:d}"
            }))


        # Second Tab: Qualified Stocks
        with tab2:
            st.header("Qualified Stocks Meeting Buying Conditions")


            nifty_50_stocks = {
                'ADANIPORTS': 'ADANIPORTS.NS',
                'ASIANPAINT': 'ASIANPAINT.NS',
                'AXISBANK': 'AXISBANK.NS',
                'BAJAJ-AUTO': 'BAJAJ-AUTO.NS',
                'BAJFINANCE': 'BAJFINANCE.NS',
                'BHARTIARTL': 'BHARTIARTL.NS',
                'BRITANNIA': 'BRITANNIA.NS',
                'CIPLA': 'CIPLA.NS',
                'COALINDIA': 'COALINDIA.NS',
                'DIVISLAB': 'DIVISLAB.NS',
                'DRREDDY': 'DRREDDY.NS',
                'EICHERMOT': 'EICHERMOT.NS',
                'GRASIM': 'GRASIM.NS',
                'HCLTECH': 'HCLTECH.NS',
                'HDFCBANK': 'HDFCBANK.NS',
                'HDFCLIFE': 'HDFCLIFE.NS',
                'HEROMOTOCO': 'HEROMOTOCO.NS',
                'HINDALCO': 'HINDALCO.NS',
                'HINDUNILVR': 'HINDUNILVR.NS',
                'ICICIBANK': 'ICICIBANK.NS',
                'INDUSINDBK': 'INDUSINDBK.NS',
                'INFY': 'INFY.NS',
                'ITC': 'ITC.NS',
                'JSWSTEEL': 'JSWSTEEL.NS',
                'KOTAKBANK': 'KOTAKBANK.NS',
                'LT': 'LT.NS',
                'M&M': 'M&M.NS',
                'MARUTI': 'MARUTI.NS',
                'NESTLEIND': 'NESTLEIND.NS',
                'NTPC': 'NTPC.NS',
                'ONGC': 'ONGC.NS',
                'POWERGRID': 'POWERGRID.NS',
                'RELIANCE': 'RELIANCE.NS',
                'SBIN': 'SBIN.NS',
                'SUNPHARMA': 'SUNPHARMA.NS',
                'TATACONSUM': 'TATACONSUM.NS',
                'TATAMOTORS': 'TATAMOTORS.NS',
                'TATASTEEL': 'TATASTEEL.NS',
                'TECHM': 'TECHM.NS',
                'TITAN': 'TITAN.NS',
                'ULTRACEMCO': 'ULTRACEMCO.NS',
                'UPL': 'UPL.NS',
                'WIPRO': 'WIPRO.NS',
                'MTARTECH': 'MTARTECH.NS'
            }


            # Cache stock data retrieval function
            @st.cache_data
            def get_stock_data_exclude_2020(ticker, start_date, end_date):
                stock_data = yf.download(ticker, start=start_date, end=end_date, actions=False)
                if stock_data.empty:
                    st.warning(f"No data available for {ticker} from {start_date} to {end_date}.")
                elif stock_data.index.max().year == 2024 and stock_data.index.max().month < 7:
                    st.warning("July 2024 data might not be available for this stock.")
                return stock_data




            # Function to format date with full month name and no time component for display
            def format_date(date):
                return date.strftime("%d %b %Y")




            # Nifty 50 index ticker symbol
            nifty_50_index_ticker = '^NSEI'




            # Cache function to fetch Nifty 50 data for the specified date range
            @st.cache_data
            def get_nifty_50_data(start_date, end_date):
                nifty_data = yf.download(nifty_50_index_ticker, start=start_date, end=end_date, actions=False)
                if nifty_data.empty:
                    st.warning(f"No Nifty 50 data available from {start_date} to {end_date}.")
                return nifty_data




            # Define the date range with unique keys for each widget
            start_date = st.sidebar.date_input('Start Date', pd.to_datetime('2015-01-01').date(), key="start_date_key")
            end_date = st.sidebar.date_input('End Date', datetime.today().date(), min_value=start_date, key="end_date_key")




            # Fetch Nifty 50 data for the selected date range
            nifty_50_data = get_nifty_50_data(start_date, end_date)




            def calculate_swing_high_drawdowns(stock_data, nifty_50_data):
                if len(stock_data) < 2:
                    # Return empty DataFrames if there is not enough data to calculate drawdowns
                    return pd.DataFrame(), pd.DataFrame()




                peaks_drawdowns = []
                current_peak = stock_data['High'].iloc[0]
                current_peak_index = stock_data.index[0]
                current_bottom = stock_data['Low'].iloc[0]
                current_bottom_index = stock_data.index[0]
                previous_bottom_date = current_bottom_index
                previous_bottom_price = current_bottom
                in_drawdown = False
                max_upside_move = 0
                current_move = {}




                for i in range(1, len(stock_data)):
                    price = stock_data['High'].iloc[i]
                    low_price = stock_data['Low'].iloc[i]




                    if price > current_peak:
                        if peaks_drawdowns:
                            previous_bottom_date = peaks_drawdowns[-1]['Bottom Date']
                            previous_bottom_price = peaks_drawdowns[-1]['Bottom Price']
                            max_upside_move = ((current_peak - previous_bottom_price) / previous_bottom_price) * 100
                        else:
                            max_upside_move = 0




                        duration_days = int((current_peak_index - previous_bottom_date).days)




                        if in_drawdown:
                            drawdown_percentage = (current_bottom - current_peak) / current_peak * 100
                            ratio = abs(drawdown_percentage) / max_upside_move if max_upside_move != 0 else None




                            if abs(drawdown_percentage) >= 15:
                                target_recovery = round(((current_peak - current_bottom) / current_bottom) * 100, 2) if current_bottom != 0 else None
                                recovery_days = int((stock_data.index[i] - current_bottom_index).days)




                                # Nifty 50 fall percentage using close prices on exact stock peak and bottom dates
                                nifty_price_at_peak = nifty_50_data['Adj Close'].asof(current_peak_index)
                                nifty_price_at_bottom = nifty_50_data['Adj Close'].asof(current_bottom_index)




                                # Calculate Nifty correction based on these specific dates, with checks for None values
                                if nifty_price_at_peak is not None and nifty_price_at_bottom is not None:
                                    nifty_fall_percentage = ((nifty_price_at_bottom - nifty_price_at_peak) / nifty_price_at_peak) * 100
                                else:
                                    nifty_fall_percentage = None




                                # Calculate time to gain 10% and 20% from the bottom
                                time_to_gain_10 = calculate_time_to_gain(stock_data, current_bottom_index, current_bottom, 0.10)




                                # Append data to peaks_drawdowns
                                peaks_drawdowns.append({
                                    'Peak Date': current_peak_index,
                                    'Bottom Date': current_bottom_index,
                                    'Peak Price': current_peak,
                                    'Bottom Price': current_bottom,
                                    'Previous Bottom Date': previous_bottom_date,
                                    'Previous Bottom Price': previous_bottom_price,
                                    'Correction Fall (%)': round(abs(drawdown_percentage), 2),
                                    'Fall/Up Move Ratio': round(ratio, 2) if ratio is not None else None,
                                    'Max Upside Move (%)': round(max_upside_move, 2),
                                    'Days to Reach Peak': duration_days,
                                    'Recovery Date': stock_data.index[i],
                                    'Days to Recover': recovery_days,
                                    'Target Recovery (%)': target_recovery,
                                    'Time to Gain 10%': time_to_gain_10,
                                    'Nifty Price at Peak Date': nifty_price_at_peak,
                                    'Nifty Price at Bottom Date': nifty_price_at_bottom,
                                    'Nifty Correction (%)': round(abs(nifty_fall_percentage), 2) if nifty_fall_percentage is not None else None
                                })




                        # Reset peak and bottom values
                        current_peak = price
                        current_peak_index = stock_data.index[i]
                        current_bottom = price
                        in_drawdown = False
                    else:
                        in_drawdown = True
                        if low_price < current_bottom:
                            current_bottom = low_price
                            current_bottom_index = stock_data.index[i]




                    ongoing_correction_fall = ((current_bottom - current_peak) / current_peak) * 100 if current_peak != 0 else None
                    fall_up_move_ratio = abs(ongoing_correction_fall) / max_upside_move if max_upside_move != 0 and ongoing_correction_fall else None
                
                    target_recovery = round(((current_peak - current_bottom) / current_bottom) * 100, 2) if current_bottom != 0 else None
                    cmp = stock_data['Adj Close'].iloc[-1]
                    actual_gain = round(((cmp - current_bottom) / current_bottom) * 100, 2) if current_bottom != 0 else None
                    percent_of_target_achieved = round((actual_gain / target_recovery) * 100, 2) if target_recovery and actual_gain else None




                    current_move = {
                        'Peak Date': current_peak_index,
                        'Bottom Date': current_bottom_index,
                        'Peak Price': current_peak,
                        'Bottom Price': current_bottom,
                        'Previous Bottom Date': previous_bottom_date,
                        'Previous Bottom Price': previous_bottom_price,
                        'Correction Fall (%)': round(abs(ongoing_correction_fall), 2) if ongoing_correction_fall is not None else None,
                        'Fall/Up Move Ratio': round(fall_up_move_ratio, 2) if fall_up_move_ratio is not None else None,
                        'Max Upside Move (%)': round(max_upside_move, 2),
                        'Days to Reach Peak': int((current_peak_index - previous_bottom_date).days) if previous_bottom_date else None,
                        'Target Recovery (%)': target_recovery,
                        'Actual Gain (%)': actual_gain,
                        'Percent of Target Achieved (%)': percent_of_target_achieved,
                        'Recovery Date': stock_data.index[-1],
                        'Days to Recover': int((stock_data.index[-1] - current_bottom_index).days) if current_bottom_index else None
                    }




                peaks_drawdowns_df = pd.DataFrame(peaks_drawdowns)
                current_move_df = pd.DataFrame([current_move])




                # Format dates for display
                for col in ['Peak Date', 'Bottom Date', 'Previous Bottom Date', 'Recovery Date']:
                    if col in peaks_drawdowns_df.columns:
                        peaks_drawdowns_df[col] = peaks_drawdowns_df[col].apply(format_date)
                    if col in current_move_df.columns:
                        current_move_df[col] = current_move_df[col].apply(format_date)




                return peaks_drawdowns_df, current_move_df




            def calculate_time_to_gain(stock_data, bottom_date, bottom_price, target_gain):
                target_price = bottom_price * (1 + target_gain)
                time_to_gain = None




                for i in range(stock_data.index.get_loc(bottom_date) + 1, len(stock_data)):
                    if stock_data['Adj Close'].iloc[i] >= target_price:
                        time_to_gain = (stock_data.index[i] - bottom_date).days
                        break




                return time_to_gain




            # Function to display summary statistics for drawdowns
            def display_summary_statistics(drawdowns_df):
                if not drawdowns_df.empty:
                    avg_correction_fall = drawdowns_df['Correction Fall (%)'].mean()
                    max_correction_fall = drawdowns_df['Correction Fall (%)'].max()
                    avg_days_to_recover = drawdowns_df['Days to Recover'].mean()
                    avg_fall_up_ratio = drawdowns_df['Fall/Up Move Ratio'].mean()
                    avg_days_to_gain_10 = drawdowns_df['Time to Gain 10%'].mean()




                    # Professional formatting with HTML and CSS
                    summary_html = f"""
                    <style>
                        .summary-box {{
                            background-color: #1f1f1f;
                            padding: 15px;
                            border-radius: 10px;
                            margin-bottom: 10px;
                        }}
                        .stat-title {{
                            color: #FFC300;
                            font-size: 20px;
                            font-weight: bold;
                            margin-bottom: 5px;
                        }}
                        .stat-value {{
                            color: #ffffff;
                            font-size: 18px;
                        }}
                    </style>
                    <div class="summary-box">
                        <div class="stat-title">Average Correction Fall:</div>
                        <div class="stat-value">{avg_correction_fall:.2f}%</div>
                    </div>
                    <div class="summary-box">
                        <div class="stat-title">Maximum Correction Fall:</div>
                        <div class="stat-value">{max_correction_fall:.2f}%</div>
                    </div>
                    <div class="summary-box">
                        <div class="stat-title">Average Days to Recover:</div>
                        <div class="stat-value">{int(avg_days_to_recover)} days</div>
                    </div>
                    <div class="summary-box">
                        <div class="stat-title">Average Fall/Up Move Ratio:</div>
                        <div class="stat-value">{avg_fall_up_ratio:.2f}</div>
                    </div>
                    <div class="summary-box">
                        <div class="stat-title">Average Days to Gain 10%:</div>
                        <div class="stat-value">{int(avg_days_to_gain_10)} days</div>
                    </div>
                    """
                    # Render the styled summary section
                    st.markdown(summary_html, unsafe_allow_html=True)



            # Create a professional progress bar effect with a label
            def progress_bar(value):
                progress_bar_html = f"""
                <style>
                    .progress-container {{
                        width: 100%;
                        background-color: #333;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.3);
                        margin-bottom: 10px;
                    }}
                    .progress-bar {{
                        width: {value}%;
                        height: 25px;
                        background: linear-gradient(90deg, #4a90e2, #002d62);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: #fff;
                        font-size: 14px;
                        font-weight: 600;
                        transition: width 0.5s ease;
                    }}
                    .progress-label {{
                        font-size: 16px;
                        font-weight: bold;
                        color: #333;
                        margin-bottom: 5px;
                    }}
                </style>
                <div class="progress-label">Progress Bar for Target % Achieved</div>
                <div class="progress-container">
                    <div class="progress-bar">{value}%</div>
                </div>
                """
                return progress_bar_html




            # Find top 5 closest stocks to their average correction
            def find_top_5_closest_to_avg_fall(nifty_50_stocks, start_date, end_date):
                stock_corrections = []
                for stock_name, ticker in nifty_50_stocks.items():
                    stock_data = get_stock_data_exclude_2020(ticker, start_date, end_date)
                    if not stock_data.empty:
                        nifty_50_data = get_nifty_50_data(start_date, end_date)
                        drawdowns_df, ongoing_df = calculate_swing_high_drawdowns(stock_data, nifty_50_data)
                        if not drawdowns_df.empty and not ongoing_df.empty:
                            avg_fall = drawdowns_df['Correction Fall (%)'].mean()
                            ongoing_correction = ongoing_df['Correction Fall (%)'].iloc[0]
                            difference = abs(ongoing_correction - avg_fall)
                            stock_corrections.append((stock_name, ticker, ongoing_correction, avg_fall, difference))
                stock_corrections_sorted = sorted(stock_corrections, key=lambda x: x[4])
                top_5_closest_stocks = stock_corrections_sorted[:5]
                return top_5_closest_stocks




            # Display the top 5 stocks closest to the average fall percentage
            def display_top_5_closest_stocks(top_5_stocks):
                if top_5_stocks:
                    st.write("### Top 5 Nifty 50 Stocks Closest to Their Average Correction Fall")
                    for idx, (stock_name, ticker, ongoing_correction, avg_fall, difference) in enumerate(top_5_stocks, start=1):
                        stock_html = f"""
                        <style>
                            .stock-box {{
                                background-color: #1f1f1f;
                                padding: 15px;
                                border-radius: 10px;
                                margin-bottom: 10px;
                                border-left: 5px solid #4a90e2;
                            }}
                            .stock-title {{
                                color: #FFC300;
                                font-size: 20px;
                                font-weight: bold;
                                margin-bottom: 5px;
                            }}
                            .stock-ticker {{
                                color: #ffffff;
                                font-size: 18px;
                                font-style: italic;
                            }}
                            .stock-details {{
                                color: #ffffff;
                                font-size: 16px;
                                margin-top: 5px;
                            }}
                        </style>
                        <div class="stock-box">
                            <div class="stock-title">{idx}. {stock_name}</div>
                            <div class="stock-ticker">({ticker})</div>
                            <div class="stock-details">
                                <strong>Ongoing Correction:</strong> {ongoing_correction:.2f}%<br>
                                <strong>Average Correction:</strong> {avg_fall:.2f}%<br>
                                <strong>Difference:</strong> {difference:.2f}%
                            </div>
                        </div>
                        """
                        st.markdown(stock_html, unsafe_allow_html=True)
                else:
                    st.write("### Top 5 Nifty 50 Stocks Closest to Their Average Correction Fall")
                    st.write("No data available for the top 5 stocks closest to their average fall percentage.")




            # Streamlit app layout setup
            st.title('Average Max Fall Drawdown Analysis')
            selected_stock = st.sidebar.selectbox('Select a Nifty 50 Stock for Max fall signal dashboard:', list(nifty_50_stocks.keys()))
            ticker = nifty_50_stocks[selected_stock]


            # Fetch stock data and Nifty 50 data for the specified date range
            stock_data = get_stock_data_exclude_2020(ticker, start_date, end_date)
            nifty_50_data = get_nifty_50_data(start_date, end_date)
            drawdowns_df, current_move_df = calculate_swing_high_drawdowns(stock_data, nifty_50_data)




            # Display calculated swing high-based drawdowns
            if not drawdowns_df.empty:
                st.write("### Calculated Swing High-Based Drawdowns")
                st.dataframe(drawdowns_df)
            else:
                st.write("### No significant drawdowns found based on the criteria")




            # Display current ongoing move details
            st.write("### Current Ongoing Move")
            st.dataframe(current_move_df)








            def check_and_highlight_ongoing(ongoing_df, avg_correction_fall, avg_fall_up_ratio, stock_data, nifty_50_data):
                # Retrieve ongoing drawdown values for condition checks
                correction_fall = ongoing_df['Correction Fall (%)'].iloc[0] if 'Correction Fall (%)' in ongoing_df.columns else None
                ongoing_fall_up_ratio = ongoing_df['Fall/Up Move Ratio'].iloc[0] if 'Fall/Up Move Ratio' in ongoing_df.columns else None
                cmp = stock_data['Adj Close'].iloc[-1]
                bottom_price = ongoing_df['Bottom Price'].iloc[0] if 'Bottom Price' in ongoing_df.columns else None
                target_recovery = ongoing_df['Target Recovery (%)'].iloc[0] if 'Target Recovery (%)' in ongoing_df.columns else None




                # Calculate CMP change percentage
                cmp_change_percentage = ((cmp - bottom_price) / bottom_price) * 100 if bottom_price else None




                # Calculate ongoing Nifty correction using latest price and recent peak
                recent_peak = nifty_50_data['Adj Close'].max()
                latest_price = nifty_50_data['Adj Close'].iloc[-1]
                ongoing_nifty_correction = ((latest_price - recent_peak) / recent_peak) * 100 if recent_peak else None




                # Calculate the average Nifty correction for stock's drawdown periods
                average_nifty_correction = ongoing_df['Nifty Correction (%)'].mean() if 'Nifty Correction (%)' in ongoing_df.columns else None




                # Buying conditions
                correction_condition_met = (avg_correction_fall - 5 <= correction_fall <= avg_correction_fall) or (correction_fall > avg_correction_fall)
                ratio_condition_met = ongoing_fall_up_ratio > 0.4 and ongoing_fall_up_ratio > avg_fall_up_ratio
                nifty_condition_met = (ongoing_nifty_correction is not None and average_nifty_correction is not None
                                    and ongoing_nifty_correction < average_nifty_correction)




                # Prepare explanations for met/missed values with checks for None values
                correction_text = f"Correction Fall: {correction_fall:.2f}% (Target Range: {avg_correction_fall - 5:.2f}% - {avg_correction_fall:.2f}%)"
                ratio_text = f"Fall/Up Move Ratio: {ongoing_fall_up_ratio:.2f} (Target: > {avg_fall_up_ratio:.2f} and > 0.4)"
                nifty_text = f"Ongoing Nifty Correction: {ongoing_nifty_correction:.2f}% (Average Nifty Correction: {average_nifty_correction:.2f}%)" \
                            if ongoing_nifty_correction is not None and average_nifty_correction is not None else \
                            "Nifty correction data is not available."




                # CMP condition
                cmp_direction = "up" if cmp > bottom_price else "down"
                cmp_text = f"CMP: {cmp:.2f}, which is {abs(cmp_change_percentage):.2f}% {cmp_direction} from the bottom price of {bottom_price:.2f}."
                target_zone_text = f"Target Zone: {target_recovery:.2f}%" if target_recovery else "Target Recovery data unavailable."




                # Determine conditions met status
                all_conditions_met = correction_condition_met and ratio_condition_met and nifty_condition_met
                box_color = "#d4edda" if all_conditions_met else "#e9ecef"
                border_color = "#28a745" if all_conditions_met else "#343a40"
                text_color = "#155724" if all_conditions_met else "#495057"
                check_icon = '<span style="color: green;">&#10003;</span>'
                cross_icon = '<span style="color: red;">&#10007;</span>'
                highlight_style = "background-color: #1a2a39; color: #ffffff; padding: 5px; border-radius: 5px;"




                # Prepare HTML output for conditions
                conditions_html = f"""
                <div style="padding: 10px; border: 2px solid {border_color}; border-radius: 10px; background-color: {box_color}; color: {text_color};">
                    <h4>Ongoing Status</h4>
                    <p>{correction_text} - {'Met' if correction_condition_met else 'Not Met'}</p>
                    <p>{ratio_text} - {'Met' if ratio_condition_met else 'Not Met'}</p>
                    <p>{nifty_text} - {'Met' if nifty_condition_met else 'Not Met'}</p>
                    <p><strong>CMP Status:</strong> {cmp_text}</p>
                    <p><strong>{target_zone_text}</strong></p>
                    <ul>
                        <li style="{highlight_style if correction_condition_met else ''}">
                            {check_icon if correction_condition_met else cross_icon}
                            <strong>Correction Fall Meets Criteria</strong>
                        </li>
                        <li style="{highlight_style if ratio_condition_met else ''}">
                            {check_icon if ratio_condition_met else cross_icon}
                            <strong>Fall/Up Move Ratio Meets Criteria</strong>
                        </li>
                        <li style="{highlight_style if nifty_condition_met else ''}">
                            {check_icon if nifty_condition_met else cross_icon}
                            <strong>Nifty Correction Below Average</strong>
                        </li>
                    </ul>
                </div>
                """
                st.sidebar.markdown(conditions_html, unsafe_allow_html=True)




                # Display sidebar summary for conditions met
                sidebar_market_status = f"""
                <div style="padding: 10px; border: 2px solid #333; border-radius: 5px; background-color: #f8f9fa; color: #333;">
                    <h4>Ongoing Process Status</h4>
                    <p>All Buy Conditions Met: {'Yes' if all_conditions_met else 'No'}</p>
                </div>
                """
                st.sidebar.markdown(sidebar_market_status, unsafe_allow_html=True)




            # Display summary statistics for drawdowns
            display_summary_statistics(drawdowns_df)




            # Calculate averages for buying conditions
            avg_correction_fall = drawdowns_df['Correction Fall (%)'].mean() if not drawdowns_df.empty else 0
            avg_fall_up_ratio = drawdowns_df['Fall/Up Move Ratio'].mean() if not drawdowns_df.empty else 0




            # Check ongoing conditions
            check_and_highlight_ongoing(current_move_df, avg_correction_fall, avg_fall_up_ratio, stock_data, nifty_50_data)




            # Display progress bar for target achieved if available
            if 'Percent of Target Achieved (%)' in current_move_df.columns and current_move_df['Percent of Target Achieved (%)'].iloc[0] is not None:
                target_achieved_value = current_move_df['Percent of Target Achieved (%)'].iloc[0]
                st.markdown(progress_bar(target_achieved_value), unsafe_allow_html=True)




            # Display price chart with drawdowns highlighted
            st.write(f"### {selected_stock} Price Chart with Drawdowns Highlighted")
            fig, ax = plt.subplots(figsize=(14, 8))
            ax.plot(stock_data['Adj Close'], color='#1f77b4', linewidth=2.5, label='Adjusted Close Price', alpha=0.9)




            # Highlight drawdowns on the chart
            for _, row in drawdowns_df.iterrows():
                peak_date = pd.to_datetime(row['Peak Date'])
                bottom_date = pd.to_datetime(row['Bottom Date'])
                peak_price = row['Peak Price']
                bottom_price = row['Bottom Price']
                ratio = row['Fall/Up Move Ratio']
                color = '#2ca02c' if ratio > 0.5 else '#d62728'
                ax.fill_between(stock_data.loc[peak_date:bottom_date].index,
                                stock_data['Adj Close'].loc[peak_date:bottom_date],
                                color=color, alpha=0.2)
                ax.scatter(peak_date, peak_price, color='green', marker='^', s=100, edgecolors='black', zorder=5)
                ax.text(peak_date, peak_price, f'Peak: {peak_price:.2f}', color='green', fontsize=10, fontweight='bold',
                        verticalalignment='bottom', horizontalalignment='left', backgroundcolor='white', zorder=10)
                ax.scatter(bottom_date, bottom_price, color='red', marker='v', s=100, edgecolors='black', zorder=5)
                ax.text(bottom_date, bottom_price, f'Bottom: {bottom_price:.2f}', color='red', fontsize=10, fontweight='bold',
                        verticalalignment='top', horizontalalignment='right', backgroundcolor='white', zorder=10)




            ax.set_title(f"{selected_stock} Adjusted Close Price with Highlighted Drawdowns", fontsize=18, fontweight='bold', color='#333333')
            ax.set_xlabel('Date', fontsize=14, fontweight='bold')
            ax.set_ylabel('Price (USD)', fontsize=14, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.4)
            ax.legend(loc='upper left', fontsize=12, frameon=True, facecolor='white', edgecolor='black')
            plt.xticks(rotation=45, fontsize=12)
            plt.yticks(fontsize=12)
            st.pyplot(fig)




            # Display top 5 stocks closest to average fall
            top_5_stocks = find_top_5_closest_to_avg_fall(nifty_50_stocks, start_date, end_date)
            display_top_5_closest_stocks(top_5_stocks)
            import streamlit as st


            @st.cache_data
            def generate_qualified_stocks(nifty_50_stocks, start_date, end_date):
                qualified_stocks = []
            
                for stock_name, ticker in nifty_50_stocks.items():
                    stock_data = get_stock_data_exclude_2020(ticker, start_date, end_date)
                    nifty_50_data = get_nifty_50_data(start_date, end_date)
                
                    drawdowns_df, ongoing_df = calculate_swing_high_drawdowns(stock_data, nifty_50_data)
                
                    if not drawdowns_df.empty and not ongoing_df.empty:
                        correction_fall = ongoing_df['Correction Fall (%)'].iloc[0]
                        fall_up_move_ratio = ongoing_df['Fall/Up Move Ratio'].iloc[0]
                        avg_stock_correction = drawdowns_df['Correction Fall (%)'].mean()
                        avg_stock_fall_up_ratio = drawdowns_df['Fall/Up Move Ratio'].mean()
                        avg_nifty_correction = drawdowns_df['Nifty Correction (%)'].mean()
                        previous_peak_price = ongoing_df['Peak Price'].iloc[0]
                        bottom_price = ongoing_df['Bottom Price'].iloc[0]
                        cmp = stock_data['Adj Close'].iloc[-1]


                        # Calculate ongoing Nifty 50 correction
                        if not nifty_50_data.empty:
                            recent_peak = nifty_50_data['Adj Close'].max()
                            latest_price = nifty_50_data['Adj Close'].iloc[-1]
                            ongoing_nifty_correction = ((latest_price - recent_peak) / recent_peak) * 100 if recent_peak != 0 else None
                        else:
                            ongoing_nifty_correction = None


                        # Calculate progress to break the previous peak
                        progress_to_break_peak = ((cmp - bottom_price) / (previous_peak_price - bottom_price)) * 100 if bottom_price != 0 else 0
                        progress_to_break_peak = min(progress_to_break_peak, 100)


                        # Calculate progress toward the 20-30% gain target
                        target_20_percent = bottom_price * 1.20
                        target_30_percent = bottom_price * 1.30
                        progress_to_20_percent = ((cmp - bottom_price) / (target_20_percent - bottom_price)) * 100 if bottom_price != 0 else 0
                        progress_to_30_percent = ((cmp - bottom_price) / (target_30_percent - bottom_price)) * 100 if bottom_price != 0 else 0


                        # Define lower and upper bounds for the average correction range
                        lower_avg_correction = avg_stock_correction - 5
                        upper_avg_correction = avg_stock_correction


                        # Logic for determining the correction status
                        if lower_avg_correction <= correction_fall <= upper_avg_correction:
                            correction_diff_value = correction_fall - avg_stock_correction
                            below_avg_correction_status = {
                                'Value': correction_diff_value,
                                'Color': 'blue',
                                'Message': f'In the range ({correction_diff_value:.2f}%)'
                            }
                        elif correction_fall > upper_avg_correction:
                            above_avg_correction_value = correction_fall - upper_avg_correction
                            below_avg_correction_status = {
                                'Value': above_avg_correction_value,
                                'Color': 'red',
                                'Message': f'Correction above the range by {above_avg_correction_value:.2f}%'
                            }
                        else:
                            # Case where the stock's correction fall is less than the lower range
                            below_avg_correction_value = lower_avg_correction - correction_fall
                            below_avg_correction_status = {
                                'Value': below_avg_correction_value,
                                'Color': 'green',
                                'Message': f'Still far from avg correction range by {below_avg_correction_value:.2f}%'
                            }


                        # Updated conditions based on the stock-specific averages
                        conditions_met = {
                            'Correction Fall': (lower_avg_correction <= correction_fall <= upper_avg_correction) or (correction_fall > upper_avg_correction),
                            'Fall/Up Move Ratio': (
                    fall_up_move_ratio is not None and avg_stock_fall_up_ratio is not None
                    and fall_up_move_ratio > 0.4 and fall_up_move_ratio > avg_stock_fall_up_ratio
                ),                
                            'Nifty Correction': ongoing_nifty_correction > avg_nifty_correction if avg_nifty_correction and ongoing_nifty_correction else False
                        }
                    
                        met_conditions_count = sum(conditions_met.values())
                    
                        if met_conditions_count >= 1:
                            qualified_stocks.append({
                                'Stock Name': stock_name,
                                'Conditions Met': met_conditions_count,
                                'Details': {
                                    'Correction Fall': {
                                        'Met': conditions_met['Correction Fall'],
                                        'Value': correction_fall,
                                        'Target': f"{lower_avg_correction:.2f}% - {upper_avg_correction:.2f}%",
                                        'Difference': f'{correction_diff_value:.2f}%' if lower_avg_correction <= correction_fall <= upper_avg_correction else 'N/A',
                                        'Difference Color': 'blue' if lower_avg_correction <= correction_fall <= upper_avg_correction else 'red' if correction_fall > upper_avg_correction else 'green',
                                        'Progress to Break Peak (%)': progress_to_break_peak
                                    },
                                    'Progress to 20% Target': {
                                        'Value': progress_to_20_percent,
                                        'Description': 'Progress toward 20% gain target from the bottom'
                                    },
                                    'Progress to 30% Target': {
                                        'Value': progress_to_30_percent,
                                        'Description': 'Progress toward 30% gain target from the bottom'
                                    },
                                    'Below Average Correction': {
                                        'Value': below_avg_correction_status['Value'],
                                        'Color': below_avg_correction_status['Color'],
                                        'Message': below_avg_correction_status['Message']
                                    },
                                    'Fall/Up Move Ratio': {
                                        'Met': conditions_met['Fall/Up Move Ratio'],
                                        'Value': fall_up_move_ratio,
                                        'Target': f"> {avg_stock_fall_up_ratio:.2f}",
                                        'Difference': fall_up_move_ratio - avg_stock_fall_up_ratio if conditions_met['Fall/Up Move Ratio'] else 'N/A'
                                    },
                                    'Nifty Correction': {
                                        'Met': conditions_met['Nifty Correction'],
                                        'Value': ongoing_nifty_correction,
                                        'Target': f"< {avg_nifty_correction:.2f}%",
                                        'Difference': ongoing_nifty_correction - avg_nifty_correction if conditions_met['Nifty Correction'] else 'N/A'
                                    }
                                },
                                'Stock Specific Averages': {
                                    'Average Correction Fall': f"{avg_stock_correction:.2f}%",
                                    'Average Fall/Up Move Ratio': f"{avg_stock_fall_up_ratio:.2f}"
                                }
                            })
                return qualified_stocks

            def display_qualified_stocks_with_clean_grid(qualified_stocks, conditions_met_filter):
                st.title("Nifty 50 Stocks Meeting Buying Conditions")

                # Filter stocks based on selected conditions met and exclude those that fulfilled 20% and 30% targets
                filtered_stocks = [
                    stock for stock in qualified_stocks
                    if stock['Conditions Met'] == conditions_met_filter
                    and stock['Details']['Progress to 20% Target']['Value'] < 100
                    and stock['Details']['Progress to 30% Target']['Value'] < 100
                ]

                # Separate "Most Wanted" stocks (those meeting Correction Fall and <50% Progress)
                most_wanted_stocks = [
                    stock for stock in filtered_stocks
                    if stock['Details']['Correction Fall']['Met']
                    and stock['Details']['Correction Fall']['Progress to Break Peak (%)'] < 50
                ]
                other_stocks = [stock for stock in filtered_stocks if stock not in most_wanted_stocks]

                # Sort other stocks alphabetically by stock name
                other_stocks = sorted(other_stocks, key=lambda x: x['Stock Name'])

                # Combine the sorted lists, with "Most Wanted" stocks at the top
                display_stocks = most_wanted_stocks + other_stocks

                if display_stocks:
                    st.markdown(f"<h3 style='color: #333;'>Stocks Meeting {conditions_met_filter} Condition(s)</h3>", unsafe_allow_html=True)

                            # CSS for smaller tags
                    grid_html = """
                    <style>
                        .grid-container {
                            display: grid;
                            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                            gap: 10px;
                            padding: 10px;
                        }
                        .stock-card {
                            background-color: #1f1f1f;
                            border: 1px solid #4a90e2;
                            border-radius: 10px;
                            padding: 15px;
                            color: #ffffff;
                            box-sizing: border-box;
                            text-align: left;
                            font-family: Arial, sans-serif;
                            position: relative;
                            overflow: visible;
                        }
                        .stock-title {
                            font-size: 16px;
                            font-weight: bold;
                            color: #FFC300;
                            margin-bottom: 5px;
                            text-transform: uppercase;
                        }
                        .most-wanted-tag, .best-value-pick-tag {
                            font-size: 10px;  /* Smaller font size */
                            font-weight: bold;
                            color: #FFD700;
                            position: absolute;
                            top: -5px;
                            left: -15px;
                            padding: 3px 7px;  /* Smaller padding */
                            transform: rotate(-45deg);
                            box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.2);
                            border-radius: 3px;
                            overflow: visible;
                        }
                        .most-wanted-tag {
                            background-color: #FF4500;
                        }
                        .best-value-pick-tag {
                            background-color: #00b33c;
                        }
                        .star {
                            color: #FFD700;
                            margin-right: 2px;
                            font-size: 10px;  /* Smaller star size */
                        }
                        .condition {
                            font-size: 14px;
                            margin: 5px 0;
                            color: #dddddd;
                        }
                        .highlight {
                            color: #ffffff;
                            font-weight: bold;
                        }
                        .met-condition {
                            color: #4CAF50;
                            font-weight: bold;
                        }
                        .progress-bar-container {
                            background-color: #333;
                            height: 8px;
                            width: 100%;
                            border-radius: 5px;
                            overflow: hidden;
                            margin-top: 5px;
                        }
                        .progress-bar {
                            height: 8px;
                            background: linear-gradient(90deg, #4a90e2, #002d62);
                        }
                        hr {
                            border: 0.5px solid #555;
                            margin: 10px 0;
                        }
                    </style>
                    <div class="grid-container">
                    """


                    # Generate each stock card
                    for stock in display_stocks:
                        # Retrieve details with formatting to 2 decimal places
                        avg_correction_fall = f"{float(stock['Stock Specific Averages']['Average Correction Fall'].replace('%', '')):.2f}%"
                        avg_fall_up_ratio = f"{float(stock['Stock Specific Averages']['Average Fall/Up Move Ratio']):.2f}"
                        correction_value = f"{stock['Details']['Correction Fall']['Value']:.2f}%"
                        correction_target = stock['Details']['Correction Fall']['Target']

                        # Convert correction_value and correction_target to floats
                        correction_value_float = float(correction_value.replace('%', '').strip())
                        lower_correction_target = float(correction_target.split('-')[0].replace('%', '').strip())
                        upper_correction_target = float(correction_target.split('-')[-1].replace('%', '').strip())

                        # Calculate the difference and determine color based on the position relative to the target range
                        if correction_value_float > upper_correction_target:
                            # Above the target range
                            correction_diff = f"{correction_value_float - upper_correction_target:.2f}%"
                            correction_diff_color = 'red'
                        elif lower_correction_target <= correction_value_float <= upper_correction_target:
                            # Within the target range
                            avg_target = (lower_correction_target + upper_correction_target) / 2
                            correction_diff = f"{correction_value_float - avg_target:.2f}%"
                            correction_diff_color = 'blue'
                        else:
                            # Below the target range
                            correction_diff = f"{lower_correction_target - correction_value_float:.2f}%"
                            correction_diff_color = 'green'

                        progress_to_break_peak = stock['Details']['Correction Fall']['Progress to Break Peak (%)']
                        progress_to_20_percent = stock['Details']['Progress to 20% Target']['Value']
                        progress_to_30_percent = stock['Details']['Progress to 30% Target']['Value']
                        below_avg_correction_msg = stock['Details']['Below Average Correction']['Message']
                        below_avg_correction_color = stock['Details']['Below Average Correction']['Color']
                        fall_up_ratio_value = f"{stock['Details']['Fall/Up Move Ratio']['Value']:.2f}"
                        fall_up_ratio_target = stock['Details']['Fall/Up Move Ratio']['Target']
                        nifty_correction_value = f"{stock['Details']['Nifty Correction']['Value']:.2f}%" if stock['Details']['Nifty Correction']['Value'] is not None else "N/A"
                        nifty_correction_target = stock['Details']['Nifty Correction']['Target']

                        # Determine status and class for each condition
                        correction_status = "Met" if stock['Details']['Correction Fall']['Met'] else "Not Met"
                        correction_class = "met-condition" if stock['Details']['Correction Fall']['Met'] else "condition"
                        fall_up_status = "Met" if stock['Details']['Fall/Up Move Ratio']['Met'] else "Not Met"
                        fall_up_class = "met-condition" if stock['Details']['Fall/Up Move Ratio']['Met'] else "condition"
                        nifty_status = "Met" if stock['Details']['Nifty Correction']['Met'] else "Not Met"
                        nifty_class = "met-condition" if stock['Details']['Nifty Correction']['Met'] else "condition"

                        # Add "Most Wanted" tag for stocks meeting special criteria
                        most_wanted_tag = "<div class='most-wanted-tag'><span class='star'>&#9733;</span>Most Wanted</div>" if stock in most_wanted_stocks else ""

                        # Add "Best Value Pick" tag if Correction Fall is above the upper average correction
                        best_value_pick_tag = "<div class='best-value-pick-tag'>Best Value Pick</div>" if correction_status == "Met" and correction_value_float > upper_correction_target else ""

                        # Create the stock card with formatted values
                        stock_card = f"""
                        <div class="stock-card">
                            {most_wanted_tag} {best_value_pick_tag} <!-- Most Wanted and Best Value Pick tags -->
                            <div class="stock-title">{stock['Stock Name']} (Conditions Met: {stock['Conditions Met']}/3)</div>
                            <div class="condition"><strong>Progress to Break Peak:</strong> <span class="highlight">{progress_to_break_peak:.2f}%</span></div>
                            <div class="progress-bar-container">
                                <div class="progress-bar" style="width: {progress_to_break_peak:.2f}%;"></div>
                            </div>
                            <div class="condition"><strong>Progress to 20% Target:</strong> <span class="highlight">{progress_to_20_percent:.2f}%</span></div>
                            <div class="condition"><strong>Progress to 30% Target:</strong> <span class="highlight">{progress_to_30_percent:.2f}%</span></div>
                            <div class="condition"><strong>Below Avg Correction:</strong> <span style="color: {below_avg_correction_color};">{below_avg_correction_msg}</span></div>
                            <hr>
                            <div class="{correction_class}"><strong>Correction Fall ({correction_status}):</strong> <span class="highlight">{correction_value}</span>, Target: {correction_target}, Diff: <span style="color: {correction_diff_color};">{correction_diff}</span></div>
                            <div class="{fall_up_class}"><strong>Fall/Up Move Ratio ({fall_up_status}):</strong> <span class="highlight">{fall_up_ratio_value}</span>, Target: {fall_up_ratio_target}</div>
                            <div class="{nifty_class}"><strong>Nifty Correction ({nifty_status}):</strong> <span class="highlight">{nifty_correction_value}</span>, Target: {nifty_correction_target}</div>
                        </div>
                        """
                        grid_html += stock_card

                    grid_html += "</div>"  # Close grid container

                    # Render the HTML with `st.components.v1.html`
                    components.html(grid_html, height=600, scrolling=True)

                else:
                    st.write(f"No stocks found meeting {conditions_met_filter} condition(s).")


            # Generate and cache qualified stocks only once
            qualified_stocks = generate_qualified_stocks(nifty_50_stocks, start_date, end_date)


            # Dropdown for filtering by conditions met - does not affect cached data
            conditions_met_filter = st.selectbox("Filter by Conditions Met", [1, 2, 3])


            # Display the qualified stocks based on the selected filter
            display_qualified_stocks_with_clean_grid(qualified_stocks, conditions_met_filter)


            # Function to display drawdowns and Nifty 50 comparison
            def display_drawdowns_and_nifty_comparison(stock_data, nifty_50_data):
                # Calculate the drawdowns and ongoing move for the selected stock
                drawdowns_df, current_move_df = calculate_swing_high_drawdowns(stock_data, nifty_50_data)
            
                # Display the drawdowns data with Nifty 50 fall comparison
                if not drawdowns_df.empty:
                    st.write("### Calculated Swing High-Based Drawdowns with Nifty 50 Comparison")
                    st.dataframe(drawdowns_df)  # This includes the 'Nifty Correction (%)' column
                else:
                    st.write("### No significant drawdowns found based on the criteria")
            
                # Display the ongoing move details
                st.write("### Current Ongoing Move")
                st.dataframe(current_move_df)




            # Main section to call and display drawdown data
            stock_data = get_stock_data_exclude_2020(ticker, start_date, end_date)
            nifty_50_data = get_nifty_50_data(start_date, end_date)




            def calculate_swing_high_drawdowns(stock_data, nifty_50_data):
                peaks_drawdowns = []
                current_move = {}
                current_peak = stock_data['High'].iloc[0]
                current_peak_index = stock_data.index[0]
                current_bottom = stock_data['Low'].iloc[0]
                current_bottom_index = stock_data.index[0]
                previous_bottom_date = current_bottom_index
                previous_bottom_price = current_bottom
                in_drawdown = False
                max_upside_move = 0




                for i in range(1, len(stock_data)):
                    price = stock_data['High'].iloc[i]
                    low_price = stock_data['Low'].iloc[i]




                    if price > current_peak:
                        if peaks_drawdowns:
                            previous_bottom_date = peaks_drawdowns[-1]['Bottom Date']
                            previous_bottom_price = peaks_drawdowns[-1]['Bottom Price']
                            max_upside_move = ((current_peak - previous_bottom_price) / previous_bottom_price) * 100
                        else:
                            max_upside_move = 0




                        duration_days = int((current_peak_index - previous_bottom_date).days)




                        if in_drawdown:
                            drawdown_percentage = (current_bottom - current_peak) / current_peak * 100
                            ratio = abs(drawdown_percentage) / max_upside_move if max_upside_move != 0 else None




                            if abs(drawdown_percentage) >= 15:
                                target_recovery = round(((current_peak - current_bottom) / current_bottom) * 100, 2)
                                recovery_days = int((stock_data.index[i] - current_bottom_index).days)




                                # Get the Nifty 50 adjusted close prices on the stock's peak and bottom dates
                                nifty_price_at_peak = nifty_50_data['Adj Close'].asof(current_peak_index)
                                nifty_price_at_bottom = nifty_50_data['Adj Close'].asof(current_bottom_index)




                                # Calculate the Nifty 50 fall percentage over the same period
                                if nifty_price_at_peak and nifty_price_at_bottom:
                                    nifty_fall_percentage = ((nifty_price_at_bottom - nifty_price_at_peak) / nifty_price_at_peak) * 100
                                else:
                                    nifty_fall_percentage = None




                                # Append all necessary data, including Nifty prices at peak and bottom dates
                                peaks_drawdowns.append({
                                    'Peak Date': current_peak_index,
                                    'Bottom Date': current_bottom_index,
                                    'Peak Price': current_peak,
                                    'Bottom Price': current_bottom,
                                    'Previous Bottom Date': previous_bottom_date,
                                    'Previous Bottom Price': previous_bottom_price,
                                    'Correction Fall (%)': round(abs(drawdown_percentage), 2),
                                    'Fall/Up Move Ratio': round(ratio, 2) if ratio is not None else None,
                                    'Max Upside Move (%)': round(max_upside_move, 2),
                                    'Days to Reach Peak': duration_days,
                                    'Recovery Date': stock_data.index[i],
                                    'Days to Recover': recovery_days,
                                    'Target Recovery (%)': target_recovery,
                                    'Nifty Price at Peak Date': nifty_price_at_peak,
                                    'Nifty Price at Bottom Date': nifty_price_at_bottom,
                                    'Nifty Correction (%)': round(abs(nifty_fall_percentage), 2) if nifty_fall_percentage is not None else None
                                })




                        current_peak = price
                        current_peak_index = stock_data.index[i]
                        current_bottom = price
                        in_drawdown = False
                    else:
                        in_drawdown = True
                        if low_price < current_bottom:
                            current_bottom = low_price
                            current_bottom_index = stock_data.index[i]




                # Convert the peaks_drawdowns list to a DataFrame and explicitly specify columns
                peaks_drawdowns_df = pd.DataFrame(peaks_drawdowns, columns=[
                    'Peak Date', 'Bottom Date', 'Peak Price', 'Bottom Price',
                    'Previous Bottom Date', 'Previous Bottom Price', 'Correction Fall (%)',
                    'Fall/Up Move Ratio', 'Max Upside Move (%)', 'Days to Reach Peak',
                    'Recovery Date', 'Days to Recover', 'Target Recovery (%)',
                    'Nifty Price at Peak Date', 'Nifty Price at Bottom Date', 'Nifty Correction (%)'
                ])




                # Ensure current_move_df is initialized, even if empty
                current_move_df = pd.DataFrame([current_move]) if current_move else pd.DataFrame()




                # Format dates in both DataFrames for display purposes
                for col in ['Peak Date', 'Bottom Date', 'Previous Bottom Date', 'Recovery Date']:
                    if col in peaks_drawdowns_df.columns:
                        peaks_drawdowns_df[col] = peaks_drawdowns_df[col].apply(format_date)
                    if col in current_move_df.columns:
                        current_move_df[col] = current_move_df[col].apply(format_date)




                return peaks_drawdowns_df, current_move_df
            # Display function for simplified drawdowns including Nifty 50 ongoing correction and average correction
            def display_simplified_drawdowns(stock_data, nifty_50_data):
                # Calculate the drawdowns and ongoing move for the selected stock
                drawdowns_df, current_move_df = calculate_swing_high_drawdowns(stock_data, nifty_50_data)
            
                # Keep essential columns, including Nifty prices if available
                if not drawdowns_df.empty:
                    # Define essential columns for the simplified display
                    essential_columns = ['Peak Date', 'Bottom Date', 'Correction Fall (%)', 'Nifty Correction (%)',
                                        'Nifty Price at Peak Date', 'Nifty Price at Bottom Date']
                
                    # Check for column availability in drawdowns_df
                    available_columns = [col for col in essential_columns if col in drawdowns_df.columns]
                    simplified_drawdowns_df = drawdowns_df[available_columns]
                
                    # Calculate average Nifty correction
                    average_nifty_correction = drawdowns_df['Nifty Correction (%)'].mean()
                
                    # Display the simplified drawdowns data with Nifty 50 fall comparison
                    st.write("### Calculated Swing High-Based Drawdowns with Nifty 50 Comparison")
                    st.dataframe(simplified_drawdowns_df)
                    st.write(f"**Average Nifty Correction for Stock's Drawdown Periods:** {average_nifty_correction:.2f}%")
                else:
                    st.write("### No significant drawdowns found based on the criteria")
            
                # Calculate ongoing Nifty correction
                if not nifty_50_data.empty:
                    # Get the most recent peak and latest price for Nifty
                    recent_peak = nifty_50_data['Adj Close'].max()
                    latest_price = nifty_50_data['Adj Close'].iloc[-1]
                    ongoing_nifty_correction = ((latest_price - recent_peak) / recent_peak) * 100 if recent_peak != 0 else None




                    # Display the ongoing move details, if necessary
                    if not current_move_df.empty:
                        # Add the ongoing Nifty correction to the current move DataFrame for display
                        current_move_df['Nifty Ongoing Correction (%)'] = ongoing_nifty_correction
                    
                        # Only display columns that exist in current_move_df
                        ongoing_columns = [col for col in ['Correction Fall (%)', 'Nifty Ongoing Correction (%)'] if col in current_move_df.columns]
                        st.write("### Current Ongoing Move with Nifty 50 Ongoing Correction")
                        st.dataframe(current_move_df[ongoing_columns])
                        st.write(f"**Ongoing Nifty Correction:** {ongoing_nifty_correction:.2f}%")
                    else:
                        st.write(f"**Ongoing Nifty Correction:** {ongoing_nifty_correction:.2f}%")
                else:
                    st.write("### Nifty 50 data is not available for calculating ongoing correction")
            # Fetch data up to the current date
            end_date = datetime.today().strftime('%Y-%m-%d')
            # Main section to call and display the simplified drawdown data
            stock_data = get_stock_data_exclude_2020(ticker, start_date, end_date)
            nifty_50_data = get_nifty_50_data(start_date, end_date)



            if not stock_details_df.empty:
                # Filter stocks highlighted in yellow
                yellow_highlighted_stocks = stock_details_df[
                    stock_details_df['% Fall from EMA 200'] >= stock_details_df['Avg Fall in Category (%)']
                ]

                if not yellow_highlighted_stocks.empty:
                    with st.expander("🔔 **Stocks Highlighted in Yellow**", expanded=True):
                        st.markdown("""
                            These stocks are highlighted in yellow because they satisfy the condition:  
                            **% Fall from EMA 200 ≥ Avg Fall in Category (%)**.
                        """)
                        yellow_table = yellow_highlighted_stocks[['Stock', 'CMP', 'EMA 200', '% Fall from EMA 200', 
                                                                'Historical Count in Category', 'Avg Fall in Category (%)', 
                                                                'Success Rate (%)']].copy()
                        yellow_table.columns = ['Stock', 'CMP', 'EMA 200', '% Fall', 'Historical Count', 'Avg Fall (%)', 'Success Rate (%)']
                        st.dataframe(yellow_table.style.format({'% Fall': '{:.2f}', 'Avg Fall (%)': '{:.2f}', 'Success Rate (%)': '{:.2f}'}))
                else:
                    st.success("✅ No stocks are highlighted in yellow.")

            # Extract "Most Wanted" and "Best Value" stocks from the qualified list
            most_wanted_stocks = []
            best_value_stocks = []

            for stock in qualified_stocks:
                try:
                    # Handle numeric or string values for correction fall
                    correction_value = stock['Details']['Correction Fall']['Value']
                    if isinstance(correction_value, str):
                        correction_value = float(correction_value.replace('%', '').strip())

                    # Parse target range and clean string values
                    target_range = stock['Details']['Correction Fall']['Target'].split('-')
                    lower_target = float(target_range[0].replace('%', '').strip())
                    upper_target = float(target_range[1].replace('%', '').strip())

                    # Determine if the stock is "Most Wanted"
                    if stock['Details']['Correction Fall']['Met'] and lower_target <= correction_value <= upper_target:
                        most_wanted_stocks.append(stock)

                    # Determine if the stock is "Best Value"
                    if stock['Details']['Correction Fall']['Met'] and correction_value > upper_target:
                        best_value_stocks.append(stock)

                except (KeyError, ValueError, IndexError, AttributeError):
                    continue  # Skip stocks with data errors

            # Normalize yellow-highlighted stock names to match the format of qualified stocks
            yellow_stock_names = set(
                yellow_highlighted_stocks['Stock']
                .str.strip()
                .str.upper()
                .str.replace('.', '', regex=False)
                .str.replace(' ', '', regex=False)
                if not yellow_highlighted_stocks.empty else []
            )

            # Normalize qualified stock names (from Most Wanted and Best Value)
            qualified_stock_names = set(
                stock['Stock Name']
                .strip()
                .upper()
                .replace('.', '', 1)  # Removing any leading periods
                .replace(' ', '')  # Removing spaces
                for stock in most_wanted_stocks + best_value_stocks
            )

            # Display Most Wanted Stocks
            with st.expander("📈 **Most Wanted Stocks**", expanded=False):
                if most_wanted_stocks:
                    most_wanted_table = pd.DataFrame([
                        {'Stock Name': stock['Stock Name'],
                        'Correction Fall (%)': stock['Details']['Correction Fall']['Value'],
                        'Target Range': stock['Details']['Correction Fall']['Target'],
                        'Progress to Break Peak (%)': stock['Details']['Correction Fall']['Progress to Break Peak (%)']}
                        for stock in most_wanted_stocks
                    ])
                    st.dataframe(most_wanted_table.style.format({'Correction Fall (%)': '{:.2f}', 'Progress to Break Peak (%)': '{:.2f}'}))
                else:
                    st.info("No stocks found for the 'Most Wanted' category.")

            # Display Best Value Stocks
            with st.expander("💎 **Best Value Stocks**", expanded=False):
                if best_value_stocks:
                    best_value_table = pd.DataFrame([
                        {'Stock Name': stock['Stock Name'],
                        'Correction Fall (%)': stock['Details']['Correction Fall']['Value'],
                        'Above Upper Target (%)': round(float(stock['Details']['Correction Fall']['Value']) -
                                                        float(stock['Details']['Correction Fall']['Target'].split('-')[-1].replace('%', '').strip()), 2),
                        'Progress to Break Peak (%)': stock['Details']['Correction Fall']['Progress to Break Peak (%)']}
                        for stock in best_value_stocks
                    ])
                    st.dataframe(best_value_table.style.format({'Correction Fall (%)': '{:.2f}', 'Above Upper Target (%)': '{:.2f}', 'Progress to Break Peak (%)': '{:.2f}'}))
                else:
                    st.info("No stocks found for the 'Best Value' category.")

            # Find common stock names between yellow-highlighted stocks and qualified stocks
            common_stocks = yellow_stock_names.intersection(qualified_stock_names)

            # Display Common Stocks with Detailed Data
            with st.expander("📊 **Common Stocks Between Yellow-Highlighted and Qualified Stocks**", expanded=True):
                if common_stocks:
                    st.markdown("### **Common Stocks with Details:**")
                    common_stock_details = yellow_highlighted_stocks[
                        yellow_highlighted_stocks['Stock']
                        .str.strip()
                        .str.upper()
                        .str.replace('.', '', regex=False)
                        .str.replace(' ', '', regex=False)
                        .isin(common_stocks)
                    ]
                    common_table = common_stock_details[['Stock', 'CMP', 'EMA 200', '% Fall from EMA 200', 
                                                        'Historical Count in Category', 'Avg Fall in Category (%)', 
                                                        'Success Rate (%)']].copy()
                    common_table.columns = ['Stock', 'CMP', 'EMA 200', '% Fall', 'Historical Count', 'Avg Fall (%)', 'Success Rate (%)']
                    st.dataframe(common_table.style.format({'% Fall': '{:.2f}', 'Avg Fall (%)': '{:.2f}', 'Success Rate (%)': '{:.2f}'}))
                else:
                    st.info("No common stocks found.")

    # Replace this with the actual logic of Dashboard 1
    st.write("This is where the logic for Dashboard 1 goes.")
    
    # Example placeholder logic
    st.write("Include your Buy Signal (EMA, RSI, Correction) logic here.")


    # Replace this with the actual logic of Dashboard 1
    st.write("This is where the logic for Dashboard 1 goes.")
    
    # Example placeholder logic
    st.write("Include your Buy Signal (EMA, RSI, Correction) logic here.")

