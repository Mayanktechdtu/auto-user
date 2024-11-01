import streamlit as st
from datetime import datetime
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase Admin for Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["service_account"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Pyrebase for Authentication
firebase_config = {
    "apiKey": st.secrets["firebase_apiKey"],
    "authDomain": st.secrets["firebase_authDomain"],
    "projectId": st.secrets["firebase_projectId"],
    "storageBucket": st.secrets["firebase_storageBucket"],
    "messagingSenderId": st.secrets["firebase_messagingSenderId"],
    "appId": st.secrets["firebase_appId"]
}
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Function to retrieve client data by email
def get_client_by_email(email):
    client_docs = db.collection("clients").where("email", "==", email).stream()
    for client_doc in client_docs:
        return client_doc.to_dict()
    return None

# User Sign Up and retrieve credentials
def sign_up():
    st.title("Sign Up")
    email = st.text_input("Enter your email:")
    if st.button("Generate Login Credentials"):
        client_data = get_client_by_email(email)
        if client_data:
            username = client_data['username']
            password = "test1234"  # Simplified example password generation
            try:
                auth.create_user_with_email_and_password(email, password)
                db.collection("clients").document(username).update({"password": password})
                st.success("Login credentials created successfully!")
                st.write(f"**Username**: {username}")
                st.write(f"**Password**: {password}")
            except:
                st.error("Error creating user in Firebase Auth.")
        else:
            st.error("Email not registered. Contact admin.")

# User Login
def login():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            client_data = get_client_by_email(email)
            if client_data:
                expiry_date = datetime.strptime(client_data['expiry_date'], '%Y-%m-%d')
                if datetime.now() > expiry_date:
                    st.error(f"Access expired on {expiry_date.strftime('%Y-%m-%d')}. Contact admin.")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = client_data['username']
                    st.session_state['permissions'] = client_data['permissions']
                    db.collection("clients").document(client_data['username']).update({"login_status": True})
                    st.success(f"Welcome, {client_data['username']}!")
            else:
                st.error("User not found.")
        except:
            st.error("Invalid email or password.")

# Main Dashboard after login
def main_dashboard():
    username = st.session_state.get('username', 'User')
    permissions = st.session_state.get('permissions', [])
    st.write(f"Welcome, {username}!")
    st.write("### Available Dashboards")
    for dashboard in ['dashboard1', 'dashboard2', 'dashboard3', 'dashboard4']:
        st.write(f"✔️ {dashboard}" if dashboard in permissions else f"❌ {dashboard} - No Access")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        db.collection("clients").document(username).update({"login_status": False})

# Handle navigation
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
            login()

if __name__ == "__main__":
    handle_navigation()
