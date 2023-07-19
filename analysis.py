from main import init
import json

data = init("data.db")

result = dict()
for i in range(len(data.activity.type)):
    result[data.timestamps[i]] = data.activity.type[i]

with open("result.json", "w") as f:
    json.dump(result, f, indent=4)

i = int()
edges = dict()
for item in result:
    if result[item] == "sleeping" and previous_item  != "sleeping":
        edges[item] = {}
        edges[item]["time"] = data.get_local_time(item)
        for i in range(180):
            i += 1
            test = result[item-60*i]
            if test == "sleeping":
                edges[item]["180min_nosleep"] = False
                break
            edges[item]["180min_nosleep"] =  True
    previous_item = result[item]
    i += 1

for item in edges:
    i = int()
    moving_count, walking_count = int(), int()
    for i in range(240):
        i += 1
        if result[item-i*60] == "rest_hand_stationary":
            pass
        if result[item-i*60] == "walking":
            walking_count += 1
        if result[item-i*60] == "rest_hand_moving":
            moving_count += 1
        if moving_count > 6 or walking_count > 2 or (moving_count > 4 and walking_count > 1):
            i = i - moving_count - walking_count
            break
    edges[item]["time_to_asleep"] = i

for item in edges:
    if edges[item]["time_to_asleep"] < 180 and edges[item]["180min_nosleep"] == True:
        hour = edges[item]["time"][11:13]
        if int(hour) > 12:
            date = edges[item]["time"][0:10]
        if int(hour) < 12:
            date = edges[item]["time"][0:10]
            day = int(date[8:10])
            day = day - 1
            if day < 10:
                date = edges[item]["time"][0:7] + "-0" + str(day) 
            else:
                date = edges[item]["time"][0:7] + "-" + str(day)
        if 12 < int(hour) < 18:
            edges[item]["type"] = "nap"
        else:
            edges[item]["type"] = "night"
        edges[item]["day"] = date

with open("edges.json", "w") as f:
    json.dump(edges, f, indent=4)
print(edges)