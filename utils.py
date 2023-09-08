import json
import numpy as np
import os
import datetime
from tqdm import tqdm

# Warning and Error handling logger that is used throughout the code
class Logger:
    def __init__(self, max_file_size_bytes=10 * 1024 * 1024):
        self.filename = "main.log"
        self.max_file_size_bytes = max_file_size_bytes
        self.check_and_create_log_file()

    def check_and_create_log_file(self):
        if not os.path.isfile(self.filename):
            with open(self.filename, "w") as file:
                file.write("")  # Create an empty log file if it doesn't exist

    def get_log_file_size(self):
        return os.path.getsize(self.filename) if os.path.exists(self.filename) else 0

    def write(self, log_type="error", data="", timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now()

        file_size = self.get_log_file_size()
        if file_size >= self.max_file_size_bytes:
            raise ValueError(f"Log file size exceeds {self.max_file_size_bytes} bytes")

        with open(self.filename, "a") as file:
            log_entry = f"{timestamp} [{log_type.upper()}]: {data}\n"
            file.write(log_entry)

# Simple config loader, then you can use the simple /utils./get_config()["parameter"] syntax anywhere
def get_config(path="E:\mibandsync_data\config.json"):
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
            if item is not None and not isinstance(item, (int, float)):
                return False
        return True
    def number_only_legacy(input):
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
    def number_only_new(input, THRESHOLD = 0.4):
        result = list()
        counter = int()
        item = int()

        def merge_lists(list1, list2):
            merged_list = []

            for val1, val2 in zip(list1, list2):
                if val1 is not None:
                    merged_list.append(val1)
                else:
                    merged_list.append(val2)

            # Append any remaining values from list2
            if len(list2) > len(list1):
                merged_list.extend(list2[len(list1):])

            return merged_list

        def get_recent(input = input, lenght=10):
            nonlocal counter, item, THRESHOLD
            recent = list()
            attempt_count = int()

            while True:
                if recent == []:
                    for i in range(lenght):
                        try:
                            if input[counter+i-5] != item:
                                recent.append(input[counter+i-5])
                        except:
                            pass
                    attempt_count += 1
                if len(recent) >= 0.5*lenght:
                    break
                else:
                    Logger().write(log_type="warning", data="When calculating recent the resulting list was suspiciously short.")
            recent = [x for x in recent if x is not None and x > THRESHOLD]
            return recent
        
        def validate_item(item, input=input):
            nonlocal THRESHOLD
            if item == None:
                return False
            elif item == 0:
                return False
            elif item < THRESHOLD*np.average([x for x in input if x is not None]):
                return False
            else:
                return True

        if get_config()["progress_bars"]: progress_bar = tqdm(total=len(input), desc="Validating data points")
        for item in input:
            if validate_item(item):
                result.append(item)
            else:
                recent_values = get_recent(input=merge_lists(result, input))
                if isinstance(input[0], int):
                    result.append(round(np.average(recent_values)))
                else:
                    result.append(np.average(recent_values))
            counter += 1
            if get_config()["progress_bars"]: progress_bar.update(1)
        if get_config()["progress_bars"]: progress_bar.close()

        return result
                        
    if contains_only_numbers(input):
        return number_only_new(input)

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

if __name__ == "__main__":
    val = [30480, 33960, 31560, 34620, None, 31500, 30000, 34140, 31260, 35160, None, 36840, 35460, 33420]
    correct_nones(val)