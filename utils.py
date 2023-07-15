import json

# Simple config loader, then you can use the simple /utils./get_config()["parameter"] syntax anywhere
def get_config(path="D:\Dokumenty\Klíče\config.json"):
    with open(path) as f: 
        config = json.load(f)
    return config