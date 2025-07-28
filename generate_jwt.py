import jwt, time

key = "BR9T03V848TvSQQz5mLK2umLXtMx6a8M"       # from Kong response
secret = "1DWm9a3hEpWURNiccXSN0Mlmbz3p9TaB"    # from Kong response

payload = {
    "iss": key,             # issuer must be the key
    "exp": int(time.time()) + 300,  # expires in 5 min
    "sub": "api-user"
}

token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
