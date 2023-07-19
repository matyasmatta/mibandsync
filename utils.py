import json
import numpy as np

# Simple config loader, then you can use the simple /utils./get_config()["parameter"] syntax anywhere
def get_config(path="D:\Dokumenty\Klíče\config.json"):
    try:
        with open(path) as f: 
            config = json.load(f)
        return config
    except:
        raise ImportError("Invalid config.json file")

# Corrects list which contain empty items (provides only method for numbers-only lists and another for general lists)
def correct_nones(input):
    def contains_only_numbers(lst):
        for item in lst:
            if not isinstance(item, (int, float)):
                return False
        return True
    if contains_only_numbers(input) == True:
        current_data,data_smooth, i = list(), list(), int()
        for item in input:
            i += 1
            current_data.append(item)
            if len(current_data) > 10: current_data.pop(0)
            rounding_list = [value for value in current_data if value is not None]
            if not rounding_list: 
                try:
                    data_smooth.append(round(np.average(data_smooth[i-5:i+5])))
                except:
                    index_of_first = i
                    for item in input:
                        if input[index_of_first]: 
                            result = input[index_of_first]
                            break
                        else:
                            index_of_first += 1
                    data_smooth.append(result)
            else: data_smooth.append(round(np.average(rounding_list)))
        return data_smooth
    else:
        result = list()
        item_count = int()
        for item in input:
            if item == "" or item is None:
                i = 1
                while True:
                    try:
                        item = result[-i]
                    except:
                        i += 1
                        if i > len(result):
                            j = int()
                            while True:
                                try:
                                    item = input[item_count+j]
                                    if item != None and item != "":
                                        break
                                    else:
                                        j += 1
                                except:
                                    j += 1
                    if item != None and item != "":
                        break
                result.append(item)
            else:
                result.append(item)
            item_count += 1
        return result