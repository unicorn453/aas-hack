import requests
 
token_url = "https://172.17.250.103:8445/realms/basyx/protocol/openid-connect/token"
 
data = {
    "client_id": "basyx-script",
    "grant_type": "password",
    "username": "user00",
    "password": "user00"
}
 
response = requests.post(token_url, data=data, verify=False)
 
print(response.status_code)
token = response.json()["access_token"]
print(token)
 
print("--------------------------------")
 
 
url = "https://172.17.250.103:8445/submodels"
 
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {token}"
}
 
response = requests.get(url, headers=headers, verify=False)
 
print(response.status_code)
print(response.json())