import requests

def get_token(client_id, client_secret):
    """Authenticates using client credential and secret and returns an access_token and token_type to be used
    in future API calls."""


    url = "https://cloudsso.cisco.com/as/token.oauth2"

    payload = "grant_type=client_credentials&client_id=" + client_id + "&client_secret=" + client_secret
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'cache-control': "no-cache",
            }

    response = requests.request("POST", url, data=payload, headers=headers)

    access_token = response.json()["access_token"]
    token_type = response.json()["token_type"]

    print(response.text)

    return {
        "access_token": access_token,
        "token_type": token_type
    }
