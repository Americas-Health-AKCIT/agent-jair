import json
import time
import requests
import streamlit as st
from utils.firebase_admin_init import verify_token
from firebase_admin import auth
from config.config import settings  # Add this line

## -------------------------------------------------------------------------------------------------
## Firebase Auth API -------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8" }
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def delete_user_account(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(settings.firebase_web_api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

VALID_ROLES = {"adm", "auditor"}

def set_user_role(uid: str, role: str = "auditor") -> None:
    """Set custom claims (roles) for a user"""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    
    try:
        auth.set_custom_user_claims(uid, {'role': role})
    except Exception as e:
        print(f"Error setting user role: {e}")
        raise e
    

def sign_in(email:str, password:str) -> None:
    try:
        # Attempt to sign in with email and password
        auth_data = sign_in_with_email_and_password(email,password)
        id_token = auth_data['idToken']
        refresh_token = auth_data['refreshToken']  # Get refresh token

        # Verify token server-side
        decoded_token = verify_token(id_token)
        if not decoded_token:
            st.session_state.auth_warning = 'Error: Invalid authentication'
            return

        # Get account information
        user_info = get_account_info(id_token)["users"][0]

        # If email is not verified, send verification email and do not sign in
        if not user_info["emailVerified"]:
            send_email_verification(id_token)
            st.session_state.auth_warning = 'Cheque seu email e clique no link de verificação. Ao verificar, clique no botão "Entrar" novamente.'

        # Save user info and token to session state and rerun
        else:
            st.session_state.login_timestamp = time.time()
            st.session_state.user_info = user_info
            st.session_state.id_token = id_token
            st.session_state.refresh_token = refresh_token 
            st.session_state.user_role = decoded_token.get('role', 'auditor')  # default to auditor if no role set
            st.rerun()

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_EMAIL","EMAIL_NOT_FOUND","INVALID_PASSWORD","MISSING_PASSWORD"}:
            st.session_state.auth_warning = 'Erro: Use um email e senha válidos.'
            print(error_message)
        elif error_message in {"INVALID_LOGIN_CREDENTIALS"}:
            st.session_state.auth_warning = 'Erro: O email ou senha não conferem. Coloque as credenciais corretas ou entre em contato com o administrador.'
            print(error_message)
        else:
            st.session_state.auth_warning = 'Erro: Por favor, tente novamente ou mais tarde.'
            print(error_message)

    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'


def get_current_user_info(id_token: str) -> dict:
    """Get detailed information about the currently logged in user"""
    try:
        # Get basic account info
        user_info = get_account_info(id_token)["users"][0]
        
        # Get role from decoded token
        decoded_token = auth.verify_id_token(id_token)
        
        # Combine the information
        current_user = {
            "email": user_info.get("email"),
            "emailVerified": user_info.get("emailVerified"),
            "role": decoded_token.get("role", "auditor"),
            "lastLoginAt": user_info.get("lastLoginAt"),
            "createdAt": user_info.get("createdAt"),
            "uid": user_info.get("localId")
        }
        
        return current_user
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None


def create_account(email:str, password:str, role: str = "auditor") -> None:
    if role not in VALID_ROLES:
        st.session_state.auth_warning = f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
        return

    try:
        # Create account (and save id_token)
        user_data = create_user_with_email_and_password(email, password)
        id_token = user_data['idToken']
        
        # Get user UID from the token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # Set user role
        set_user_role(uid, role)

        # Create account and send email verification
        send_email_verification(id_token)
        st.session_state.auth_success = 'Cheque seu email e clique no link de verificação. Ao verificar, clique no botão "Entrar" novamente.'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message == "EMAIL_EXISTS":
            st.session_state.auth_warning = 'Erro: Email já cadastrado.'
        elif error_message in {"INVALID_EMAIL","INVALID_PASSWORD","MISSING_PASSWORD","MISSING_EMAIL","WEAK_PASSWORD"}:
            st.session_state.auth_warning = 'Erro: Use um email e senha válidos.'
            print(error_message)
        else:
            st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'
            print(error_message)
    
    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'


def create_account_adm(email, password, role: str = "auditor"):
    """Create a user account using admin privileges"""
    if role not in VALID_ROLES:
        st.session_state.auth_warning = f"Role inválida. Deve ser um dos seguintes: {', '.join(VALID_ROLES)}"
        return

    try:
        user = auth.create_user(
            email=email,
            password=password
        )
        set_user_role(user.uid, role)
        st.session_state.auth_success = f'Conta criada com sucesso para {email}'
    except auth.EmailAlreadyExistsError:
        st.session_state.auth_warning = 'Erro: Email já cadastrado.'
    except ValueError as e:
        if "Invalid email" in str(e):
            st.session_state.auth_warning = 'Erro: Use um email válido.'
        elif "Password must be at least 6 characters" in str(e):
            st.session_state.auth_warning = 'Erro: A senha deve ter pelo menos 6 caracteres.'
        else:
            st.session_state.auth_warning = 'Erro: Use um email e senha válidos.'
            print(str(e))
    except Exception as e:
        st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'
        print(str(e))


def reset_password(email:str) -> None:
    try:
        send_password_reset_email(email)
        st.session_state.auth_success = 'Link de redefinição de senha enviado para seu email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"MISSING_EMAIL","INVALID_EMAIL","EMAIL_NOT_FOUND"}:
            st.session_state.auth_warning = 'Erro: Use um email válido.'
            print(error_message)
        else:
            st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'  
            print(error_message)  
    
    except Exception:
        st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'


def reset_password_adm(email, new_password):
    """Reset a user's password using admin privileges"""
    try:
        # Check if user exists first
        user = auth.get_user_by_email(email)
        auth.update_user(
            user.uid,
            password=new_password
        )
        st.session_state.auth_success = f'Senha alterada com sucesso para o usuário {email}'
    except auth.UserNotFoundError:
        st.session_state.auth_warning = f'Usuário com email {email} não encontrado.'
    except Exception as e:
        st.session_state.auth_warning = f'Erro ao redefinir senha: {str(e)}'


def sign_out() -> None:
    st.session_state.clear()
    st.session_state.auth_success = 'Você saiu da sua conta com sucesso'


def delete_account(password:str) -> None:
    try:
        # Confirm email and password by signing in (and save id_token)
        auth_data = sign_in_with_email_and_password(st.session_state.user_info['email'],password)
        id_token = auth_data['idToken']
        
        # Verify token server-side
        decoded_token = verify_token(id_token)
        if not decoded_token:
            st.session_state.auth_warning = 'Erro: Autenticação inválida'
            return
        
        # Attempt to delete account
        delete_user_account(id_token)
        st.session_state.clear()
        st.session_state.auth_success = 'Sua conta foi deletada com sucesso'

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_PASSWORD", "MISSING_PASSWORD"}:
            st.session_state.auth_warning = 'Erro: Senha inválida'
        else:
            st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'
        print(error_message)

    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Erro: Por favor, tente novamente mais tarde.'


def delete_account_adm(email):
    """Delete a user account using admin privileges"""
    try:
        user = auth.get_user_by_email(email)
        auth.delete_user(user.uid)
        st.session_state.auth_success = f'Conta do usuário {email} deletada com sucesso!'
    except auth.UserNotFoundError:
        st.session_state.auth_warning = f'Usuário com email {email} não encontrado.'
    except Exception as e:
        st.session_state.auth_warning = f'Erro ao deletar conta: {str(e)}'
