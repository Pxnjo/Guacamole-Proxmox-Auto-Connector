import requests, pyotp
from config import guac_server, key, guacamole_admin, admin_password
url=f"http://{guac_server}:8080/guacamole/"
totp_url=f"http://{guac_server}:8080/guacamole/api/tokens"

def describe_response(response):
    try:
        response_json = response.json()
    except ValueError:
        response_json = None
    return response.status_code, response.text, response_json
session = requests.Session()

def guacamole_access():

    guac_header = {
        'Content-Type':'application/x-www-form-urlencoded'
    }
    login = {
        "username": guacamole_admin,
        "password": admin_password
    }
    response = session.post(url, json=login, headers=guac_header)
    if response.status_code == 200:
        print("Login iniziale avvenuto con successo. Procedendo per 2FA ...")

        # Codice che identifica il qr code
        clean_key = key.replace(" ", "").strip()
        totp = pyotp.TOTP(clean_key)
        new_totp = totp.now()
        totp_json = {
            "username": guacamole_admin,
            "password": admin_password,
            "guac-totp": new_totp
        }
        response_2fa = session.post(totp_url, data=totp_json, headers=guac_header)
        if response_2fa.status_code == 200:
            token = response_2fa.json().get("authToken")
            print(f"Login completato con successo! Token: {token}")
            return token
        else:
            print(f"Login fallito! {describe_response(response_2fa)}")
    else:
        print(f"Login iniziale fallito! Status code: {describe_response(response)}")
clean_key = key.replace(" ", "").strip()
totp = pyotp.TOTP(clean_key)
new_totp = totp.now()