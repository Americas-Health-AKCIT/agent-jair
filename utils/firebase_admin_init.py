import firebase_admin
from firebase_admin import credentials, auth
import streamlit as st
from datetime import datetime
import requests
from config.config import settings
import time

# Initialize Firebase Admin with service account
if not firebase_admin._apps:
    cred = credentials.Certificate('service_account.json')
    firebase_admin.initialize_app(cred)

def verify_token(id_token):
    """Verify the Firebase ID token"""
    try:
        # Check if login timestamp exists
        if 'login_timestamp' not in st.session_state:
            st.session_state.login_timestamp = time.time()
        
        # Check if 8 hours have passed since login
        current_time = time.time()
        hours_elapsed = (current_time - st.session_state.login_timestamp) / 3600
        
        if hours_elapsed >= 8:
            print("8-hour session expired")
            st.session_state.clear()
            st.session_state.auth_warning = 'Session expired after 8 hours. Please sign in again.'
            st.rerun()

        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10) # Permitir 10 segundos de diferença

        return decoded_token

    except auth.ExpiredIdTokenError:
        # For 1-hour Firebase token expiration, just get a new token
        try:
            # Silently refresh the token if within 8-hour window
            if 'refresh_token' in st.session_state:
                new_token = refresh_firebase_token(st.session_state.refresh_token)
                if new_token:
                    st.session_state.id_token = new_token
                    return auth.verify_id_token(new_token)
        except Exception as e:
            print(f"Token refresh error: {e}")
        return None
    except Exception as e:
        print(f"Token verification error: {e}")
        return None 


def refresh_firebase_token(refresh_token):
    """Refresh Firebase ID token using refresh token"""
    try:
        # Firebase Auth REST API endpoint for token refresh
        url = f"https://securetoken.googleapis.com/v1/token?key={settings.firebase_web_api_key}"
        
        # Make request to refresh token
        response = requests.post(url, 
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
        )
        response.raise_for_status()
        
        # Return new ID token
        return response.json()['id_token']
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None