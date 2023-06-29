import requests

gadgetbridge_url = "http://192.168.10.188:9191"

data_url = f"{gadgetbridge_url}/api/v1/activities"
response = requests.get(data_url)

if response.status_code == 200:
    data = response.json()
    # Process the retrieved data as per your requirements
    print(data)
else:
    print("Error fetching data from Gadgetbridge.")
