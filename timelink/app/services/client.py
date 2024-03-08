""" Following the fief-client docs at
https://docs.fief.dev/integrate/python/

"""
import os
from fief_client import Fief

fief_url = os.getenv('FIEF_URL')
fief_key = os.getenv('FIEF_KEY')
fief_secret = os.getenv('FIEF_SECRET')

fief = Fief(fief_url, fief_key, fief_secret)

redirect_url = "http://localhost:8000/callback"

auth_url = fief.auth_url(redirect_url, scope=["openid"])
print(f"Open this URL in your browser: {auth_url}")

code = input("Paste the callback code: ")

tokens, userinfo = fief.auth_callback(code, redirect_url)
print(f"Tokens: {tokens}")
print(f"Userinfo: {userinfo}")
