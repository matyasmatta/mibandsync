import json

# Simple config loader, then you can use the simple get_config()["parameter"] syntax anywhere
def get_config(path="config.json"):
    with open(path) as f: 
        config = json.load(f)
    return config