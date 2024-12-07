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

    dashboards = {
        'Dashboard 1': os.path.join("Dashboard", "oneday_fall.py"),
        'Dashboard 2': os.path.join("Dashboard", "Index_Analysis.py"),
        'Dashboard 3': os.path.join("Dashboard", "stock screener+historical dashboard.py")
    }

    selected_dashboard = st.radio("Available Dashboards", list(dashboards.keys()))

    if st.button("Open Selected Dashboard"):
        if selected_dashboard.lower().replace(' ', '') in permissions:
            st.session_state['active_dashboard'] = dashboards[selected_dashboard]
        else:
            st.error("You do not have access to this dashboard.")

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
        else:
            filepath = st.session_state['active_dashboard']
            load_dashboard(filepath)
    else:
        choice = st.sidebar.radio("Choose an option", ["Sign Up", "Login"])

        if choice == "Sign Up":
            sign_up()
        else:
            show_login()

if __name__ == "__main__":
    handle_navigation()
