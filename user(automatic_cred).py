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
    import plotly.graph_objects as go
    
    # Define the Nifty 50 stock symbols
    nifty_50_symbols = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "HINDUNILVR.NS", "HDFC.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "SBIN.NS",
        # Add more Nifty 50 symbols as required
    ]
    
    def fetch_data(symbols, start_date, end_date):
        data = {}
        for symbol in symbols:
            try:
                stock_data = yf.download(symbol, start=start_date, end=end_date)
                if not stock_data.empty:
                    data[symbol] = stock_data
                else:
                    st.warning(f"No data found for {symbol}.")
            except Exception as e:
                st.error(f"Error fetching data for {symbol}: {e}")
        return data
    
    
    # Function to analyze significant falls and their aftermath
    def analyze_falls(data, days_after):
        results = []
        for symbol, df in data.items():
            df['Fall%'] = df['Close'].pct_change() * 100
            falls = df[df['Fall%'] <= -5]
            for index, row in falls.iterrows():
                after_fall_df = df.loc[index:].copy()
                after_fall_df['Below Fall'] = after_fall_df['Close'] < row['Close']
                continuous_fall_days = (
                    after_fall_df['Below Fall'].cumsum() - 
                    after_fall_df['Below Fall'].cumsum().where(~after_fall_df['Below Fall']).ffill().fillna(0)
                ).max()
    
                # Maximum consecutive days below fall price
                max_days_below_fall = 0
                count_below_fall = 0
                for close in after_fall_df['Close']:
                    if close < row['Close']:
                        count_below_fall += 1
                    else:
                        count_below_fall = 0
                    max_days_below_fall = max(max_days_below_fall, count_below_fall)
    
                percent_below_fall = ((after_fall_df['Close'].min() - row['Close']) / row['Close']) * 100
                
                analysis = {
                    'Symbol': symbol,
                    'Date': index,
                    'Close on Fall': row['Close'],
                    'Fall%': row['Fall%'],
                    'Continuous Fall Days': continuous_fall_days,
                    'Max Days Below Fall': max_days_below_fall,
                    'Percent Below Fall': percent_below_fall,
                    'After 1 Day': df['Close'].shift(-1).loc[index],
                    'After 1 Day % Change': ((df['Close'].shift(-1).loc[index] - row['Close']) / row['Close']) * 100,
                    'After 3 Days': df['Close'].shift(-3).loc[index],
                    'After 3 Days % Change': ((df['Close'].shift(-3).loc[index] - row['Close']) / row['Close']) * 100,
                    'After 5 Days': df['Close'].shift(-5).loc[index],
                    'After 5 Days % Change': ((df['Close'].shift(-5).loc[index] - row['Close']) / row['Close']) * 100,
                    f'After {days_after} Days': df['Close'].shift(-days_after).loc[index],
                    f'After {days_after} Days % Change': ((df['Close'].shift(-days_after).loc[index] - row['Close']) / row['Close']) * 100
                }
                results.append(analysis)
        return pd.DataFrame(results)
    
    # Function to calculate maximum fall and other metrics
    def calculate_max_fall(data):
        results = []
        for symbol, df in data.items():
            df['Fall%'] = df['Close'].pct_change() * 100
            
            max_fall_start_date = df['Close'].idxmax()
            max_fall_start_open = df['Open'].loc[max_fall_start_date]
            max_fall_period = df[df['Close'] < max_fall_start_open]
            max_fall_end_date = max_fall_period.index[-1] if not max_fall_period.empty else df.index[-1]
            max_fall_percent = ((df['Close'].loc[max_fall_end_date] - max_fall_start_open) / max_fall_start_open) * 100
            max_fall_start_price = df['Close'].loc[max_fall_start_date]
            max_fall_end_price = df['Close'].loc[max_fall_end_date]
            
            # Determine red and green candles in the max fall period
            max_fall_period = df.loc[max_fall_start_date:max_fall_end_date]
            red_candles = (max_fall_period['Close'] < max_fall_period['Open']).sum()
            green_candles = (max_fall_period['Close'] > max_fall_period['Open']).sum()
    
            # Determine maximum number of back-to-back red candles
            max_red_streak = 0
            current_red_streak = 0
            for close, open_ in zip(max_fall_period['Close'], max_fall_period['Open']):
                if close < open_:
                    current_red_streak += 1 
                    max_red_streak = max(max_red_streak, current_red_streak)
                else:
                    current_red_streak = 0
    
            results.append({
                'Symbol': symbol,
                'Max Fall%': max_fall_percent,
                'Max Fall Start Date': max_fall_start_date,
                'Max Fall Start Price': max_fall_start_price,
                'Max Fall End Date': max_fall_end_date,
                'Max Fall End Price': max_fall_end_price,
                'Red Candles': red_candles,
                'Green Candles': green_candles,
                'Max Red Candles': max_red_streak
            })
        return pd.DataFrame(results)
    
    # Function to plot stock performance
    def plot_stock_performance(data, symbol, fall_dates, range_after):
        fig = go.Figure()
        for date in fall_dates:
            date = pd.to_datetime(date)
            start_date = date - pd.Timedelta(days=5)
            end_date = date + pd.Timedelta(days=range_after)
            
            stock_data = data[symbol][start_date:end_date]
            
            fig.add_trace(go.Scatter(
                x=stock_data.index,
                y=stock_data['Close'],
                mode='lines+markers',
                line=dict(color='blue'),
                name=f'Performance near {date.date()}',
                text=[f'Date: {dt.date()}<br>Close: {price:.2f}' for dt, price in zip(stock_data.index, stock_data['Close'])],
                hoverinfo='text'
            ))
    
            # Add red dot for falling date
            fig.add_trace(go.Scatter(
                x=[date],
                y=[data[symbol]['Close'].loc[date]],
                mode='markers',
                marker=dict(color='red', size=10),
                name=f'Fall on {date.date()}',
                text=[f'Date: {date.date()}<br>Close: {data[symbol]["Close"].loc[date]:.2f}'],
                hoverinfo='text'
            ))
    
        fig.update_layout(
            title=f'Stock Performance of {symbol} around Significant Falls',
            xaxis_title='Date',
            yaxis_title='Close Price',
            hovermode='x unified'
        )
        st.plotly_chart(fig)
    
    # Fetch historical data for the year 2023
    data_2023 = fetch_data(nifty_50_symbols, '2023-01-01', '2023-12-31')
    
    # Streamlit dashboard
    st.title('Nifty 50 Stocks Analysis')
    st.subheader('Stocks with Falls Greater than 5% in a Day for the Year 2023')
    
    # User input for days after fall
    days_after = st.slider("Select days after fall for analysis", min_value=1, max_value=30, value=7)
    
    # Analyze the falls greater than 5% for 2023
    fall_analysis_2023 = analyze_falls(data_2023, days_after)
    
    # Calculate frequency of falls for 2023
    fall_frequency_2023 = fall_analysis_2023['Symbol'].value_counts().reset_index()
    fall_frequency_2023.columns = ['Symbol', 'Frequency']
    st.write(fall_frequency_2023)
    
    st.subheader('Detailed Analysis of Falls and Aftermath for 2023')
    st.write(fall_analysis_2023)
    
    # Plot stock performance for selected stock
    st.subheader('Stock Performance After Significant Falls for 2023')
    selected_stock_2023 = st.selectbox('Select a Stock', fall_frequency_2023['Symbol'].unique(), key='stock_2023')
    range_after_2023 = st.slider("Select range of days to display after the fall", min_value=5, max_value=60, value=30, key='range_2023')
    selected_fall_dates_2023 = fall_analysis_2023[fall_analysis_2023['Symbol'] == selected_stock_2023]['Date']
    plot_stock_performance(data_2023, selected_stock_2023, selected_fall_dates_2023, range_after_2023)
    
    # Select year for maximum fall analysis
    year = st.selectbox("Select year for maximum fall analysis", [2021, 2022, 2023])
    
    # Fetch historical data for the selected year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    data = fetch_data(nifty_50_symbols, start_date, end_date)
    
    # Calculate maximum fall and other metrics for the selected year
    max_fall_analysis = calculate_max_fall(data)
    
    st.subheader(f'Maximum Fall Analysis for {year}')
    st.write(max_fall_analysis)
    
    # Plot stock performance for selected stock in maximum fall analysis
    st.subheader(f'Stock Performance for Maximum Fall in {year}')
    selected_stock_max_fall = st.selectbox('Select a Stock', max_fall_analysis['Symbol'].unique(), key='stock_max_fall')
    range_after_max_fall = st.slider("Select range of days to display after the fall", min_value=5, max_value=60, value=30, key='range_max_fall')
    selected_fall_dates_max_fall = max_fall_analysis[max_fall_analysis['Symbol'] == selected_stock_max_fall][['Max Fall Start Date', 'Max Fall End Date']]
    plot_stock_performance(data, selected_stock_max_fall, selected_fall_dates_max_fall.values.flatten(), range_after_max_fall)

    # Replace this with the actual logic of Dashboard 1
    st.write("This is where the logic for Dashboard 1 goes.")
    
    # Example placeholder logic
    st.write("Include your Buy Signal (EMA, RSI, Correction) logic here.")


    # Replace this with the actual logic of Dashboard 1
    st.write("This is where the logic for Dashboard 1 goes.")
    
    # Example placeholder logic
    st.write("Include your Buy Signal (EMA, RSI, Correction) logic here.")
