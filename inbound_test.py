import requests

url = "https://api.bland.ai/v1/inbound/{phone_number}"

headers = {"authorization": "<authorization>"}

response = requests.request("GET", url, headers=headers)

print(response.text)