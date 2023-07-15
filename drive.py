# Credit to @turdus-merula and @Shahar Gino
# https://stackoverflow.com/a/39225272 and https://stackoverflow.com/a/68265129

import requests
import os
import urllib.request
from getfilelistpy import getfilelist
from os import path, makedirs, remove, rename

def get_file(id, destination):
    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)
    return destination    

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

def get_folder(remote_folder, local_dir="./", debug_en=False, api_key="", api_key_path =""):

    if api_key:
        # push key brute force
        pass
    elif api_key_path:
        # get API key from text file (for privacy)
        try:
            with open(api_key_path) as f: 
                api_key = f.readline()
        except:
            raise FileNotFoundError("File provided in drive.get_folder() for API was not found")
    else:
        raise ValueError("No api_key determining arguement was passed into drive.get_folder() function")

    success = True
    try:
        resource = {
            "api_key": api_key,
            "id": remote_folder.split('/')[-1].split('?')[0],
            "fields": "files(name,id)",
        }
        res = getfilelist.GetFileList(resource)
        if debug_en: print('Found #%d files' % res['totalNumberOfFiles'])
        destination = local_dir
        if not path.exists(destination):
            makedirs(destination)
        for file_dict in res['fileList'][0]['files']:
            if debug_en: print('Downloading %s' % file_dict['name'])
            if api_key:
                source = "https://www.googleapis.com/drive/v3/files/%s?alt=media&key=%s" % (file_dict['id'], api_key)
            else:
                source = "https://drive.google.com/uc?id=%s&export=download" % file_dict['id']  # only works for small files (<100MB)
            destination_file = path.join(destination, file_dict['name'])
            urllib.request.urlretrieve(source, destination_file)
        
        return destination + "/data.db"

    except Exception as err:
        print(err)
        success = False
        raise Exception

if __name__ == "__main__":
    obj_id = '1IUKWpOUHVYOWnuQ127cLofcL2d3_ZLZr'
    destination = "./"
    get_folder(obj_id, destination, api_key_path=r"D:\Dokumenty\Klíče\drive_api.txt")