import requests
 
token_url = "http://172.17.255.170:8084/realms/basyx/protocol/openid-connect/token"
 
data = {
    "client_id": "basyx-web",
    "grant_type": "password",
    "username": "basyx-admin",
    "password": "basyx-admin"
}
 
response = requests.post(token_url, data=data)
 
print(response.status_code)
token = response.json()["access_token"]
print(token)
 
print("--------------------------------")
 
 
url = "http://localhost:8081/submodels"
 
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {token}"
}
 
response = requests.get(url, headers=headers)
 
print(response.status_code)
print(response.json())