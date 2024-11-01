import streamlit as st
from datetime import datetime
import sqlite3
import random
import string

# Connect to the SQLite database
conn = sqlite3.connect('clients_new.db')
cursor = conn.cursor()

# Function to retrieve client data by email
def get_client_by_email(email):
    cursor.execute('SELECT username, password, expiry_date, permissions, login_status FROM clients WHERE email = ?', (email,))
    client = cursor.fetchone()
    if client:
        return {
            'username': client[0],
            'password': client[1],
            'expiry_date': client[2],
            'permissions': client[3].split(','),
            'login_status': client[4]
        }
    return None

# Function to retrieve client data by username
def get_client_by_username(username):
    cursor.execute('SELECT username, password, expiry_date, permissions, login_status FROM clients WHERE username = ?', (username,))
    client = cursor.fetchone()
    if client:
        return {
            'username': client[0],
            'password': client[1],
            'expiry_date': client[2],
            'permissions': client[3].split(','),
            'login_status': client[4]
        }
    return None

# Function to generate a random password
def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(characters) for i in range(length))

# Function to update the password (without affecting login status)
def update_password(username, password):
    cursor.execute('UPDATE clients SET password = ? WHERE username = ?', (password, username))
    conn.commit()

# Function to update login status (active/inactive)
def update_login_status(username, status):
    cursor.execute('UPDATE clients SET login_status = ? WHERE username = ?', (status, username))
    conn.commit()

# Sign Up: Verify Email and Retrieve or Generate Credentials
def sign_up():
    st.title("Sign Up")
    email = st.text_input("Enter your registered email:")
    if st.button("Generate Login Credentials"):
        client_data = get_client_by_email(email)
        
        if client_data:
            username = client_data['username']
            password = client_data['password']
            
            # If no password exists, generate and store it without changing login status
            if not password:
                password = generate_random_password()
                update_password(username, password)
            
            # Display credentials to the user
            st.success("Login credentials retrieved successfully!")
            st.write(f"**Username**: {username}")
            st.write(f"**Password**: {password}")

            # Store credentials in session state for autofill and sidebar display
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
            # Check if the user is already logged in
            if client_data['login_status'] == 1:
                st.warning("You are already logged in on another device or session.")
                
                # Option to clear previous session
                if st.button("Clear Previous Session and Login Again"):
                    update_login_status(username, 0)  # Set login status to inactive
                    st.info("Previous session cleared. Please click 'Login' again to continue.")
                    st.experimental_rerun()  # Refresh the page to allow a new login
                return  # Stop further processing until login is retried
            
            # Verify password
            if client_data['password'] == password:
                expiry_date = datetime.strptime(client_data['expiry_date'], '%Y-%m-%d')
                if datetime.now() > expiry_date:
                    st.error(f"Your access expired on {expiry_date.strftime('%Y-%m-%d')}. Please contact admin.")
                else:
                    # Successful login and set login status to active
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = client_data['username']
                    st.session_state['permissions'] = client_data['permissions']
                    st.session_state['expiry_date'] = client_data['expiry_date']
                    update_login_status(username, 1)  # Set login status to active
                    st.success(f"Welcome, {username}!")
            else:
                st.error("Invalid password.")
        else:
            st.error("Username not found.")



# Main Dashboard after login
def main_dashboard():
    username = st.session_state.get('username', 'User')
    permissions = st.session_state.get('permissions', [])
    expiry_date = st.session_state.get('expiry_date', datetime.now().strftime("%Y-%m-%d"))

    st.write(f"Welcome, {username}!")
    st.write(f"Your access expires on: {expiry_date}")

    st.write("### Available Dashboards")
    for dashboard in ['dashboard1', 'dashboard2', 'dashboard3', 'dashboard4', 'dashboard5', 'dashboard6']:
        if dashboard in permissions:
            st.write(f"✔️ {dashboard}")
        else:
            st.write(f"❌ {dashboard} - No Access")

    # Logout button to clear session and reset login status
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        update_login_status(username, 0)  # Reset login status to inactive
        st.experimental_set_query_params()  # Refresh the page

# Handle Navigation
def handle_navigation():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        main_dashboard()
    else:
        choice = st.sidebar.radio("Choose an option", ["Sign Up", "Login"])

        if choice == "Sign Up":
            sign_up()
        else:
            show_login()

# Run the user dashboard
if __name__ == "__main__":
    handle_navigation()
