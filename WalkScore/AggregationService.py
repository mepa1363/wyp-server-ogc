# -*- coding: utf-8 -*-
import ast
import collections
import json
import math

import psycopg2
from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def aggregation(start_point, radius, poi_data, distance_decay_function):
    if poi_data != '"NULL"':
        # POI types: Bank, Restaurant, Shopping, Grocery, Entertainment, School, Library, Health
        poi_weights = {"Bank": [1],  #bank
                       "Grocery": [3],  #grocery
                       "Restaurant": [.75, .45, .25, .25, .225, .225, .225, .225, .2, .2],  #restaurant and coffee
                       "Shopping": [.5, .45, .4, .35, .3],  #shopping
                       "Entertainment": [1],  #entertainment
                       "School": [1],  #school
                       "Library": [1],  #library
                       #"Health": [1]  #health
        }

        #calculate the sum of weights for poi
        poi_sum = 0
        for i in xrange(len(poi_weights)):
            poi_weights_number = poi_weights.items()[i][1]
            for j in xrange(len(poi_weights_number)):
                poi_sum += poi_weights_number[j]

        poi_index = 0

        if distance_decay_function == 'true':
            poi_type_distance = distanceDecay(start_point, poi_data, radius)
            poi_list = ast.literal_eval(str(poi_type_distance))
            #calculate raw poi score for the main walkshed
            for i in xrange(len(poi_list)):
                #poi type
                poi_list_type = poi_list.items()[i][0]
                #the number of POIs in each type
                poi_list_number = poi_list.items()[i][1]
                #the number of weights for each POI type
                poi_weights_number = len(poi_weights[poi_list_type])
                if len(poi_list_number) <= poi_weights_number:
                    for j in xrange(len(poi_list_number)):
                        poi_index += poi_weights[poi_list_type][j] * poi_list_number[j]
                else:
                    for j in xrange(len(poi_weights[poi_list_type])):
                        poi_index += poi_weights[poi_list_type][j] * poi_list_number[j]

        elif distance_decay_function == 'false':
            poi_list = dataPreparation(poi_data)
            poi_list = ast.literal_eval(poi_list)
            for i in xrange(len(poi_list)):
                poi_item_type = poi_list.items()[i][0]
                poi_item_number = poi_list.items()[i][1]
                poi_item_weight_number = len(poi_weights[poi_item_type])
                if poi_item_weight_number >= poi_item_number:
                    for j in xrange(poi_item_number):
                        poi_index += poi_weights[poi_item_type][j]
                else:
                    for j in xrange(poi_item_weight_number):
                        poi_index += poi_weights[poi_item_type][j]

        #calculate normalized poi score (percentage) for the main walkshed
        poi_index_normal = round(poi_index / poi_sum * 100)

    else:
        poi_index_normal = 0
    radius = float(radius) * 1000
    # calculate area of the walkshed
    area = math.pow(radius, 2) * math.pi
    start_point = start_point.split(',')
    start_point = "%s,%s" % (start_point[1], start_point[0])
    #there is no standard specification to encode circle as a geojson object, but there is a proposal that I used to do that:
    #https://github.com/GeoJSONWG/geojson-spec/wiki/Proposal---Circles-and-Ellipses-Geoms
    walkshed_circle = """{"type": "Circle", "coordinates": [%s], "radius": %s, "properties": {"radius_units": "m", "area": %s, "score": "%d"}}""" % (
        start_point, radius, area, poi_index_normal)

    print walkshed_circle

    return walkshed_circle


def dataPreparation(data):
    data_json = json.loads(data)
    data_type = []
    for item in data_json['features']:
        data_type.append(str(item['properties']['type']))
    data_type_counter = collections.Counter(data_type)
    data_for_aggregation = str(data_type_counter)[8:-1]
    return data_for_aggregation


def distanceDecay(start_point, data, radius):
    import config

    connection_string = config.conf()

    # first turning point (.25 miles)
    x1 = 402.336
    y1 = 1
    #second turning point (1 mile)
    x2 = float(radius) * 1000  #1609.34
    y2 = 0
    #in order to get rid of division by zero when x1=x2
    #the point is when x2<x1 (threshold) then all the weights will be 1
    if x1 == x2:
        x2 -= 1
    #linear equation
    m = (y2 - y1) / float(x2 - x1)
    b = y2 - m * x2
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    start_point = start_point.split(',')
    longitude = start_point[1]
    latitude = start_point[0]
    start_point = 'POINT (%s %s)' % (longitude, latitude)
    data_json = json.loads(data)
    ref_poi_list = {}
    for item in data_json['features']:
        location = item['geometry']['coordinates']
        location = 'POINT (%s %s)' % (location[0], location[1])
        poi_type = str(item['properties']['type'])

        #check if the requirement is met (true/false)
        _isContinued = check_no_of_poi(ref_poi_list, poi_type)
        if _isContinued:
            selectQuery = "SELECT ST_Distance(ST_Transform(ST_GeomFromText(%s, 4326), 3776), " \
                          "ST_Transform(ST_GeomFromText(%s, 4326), 3776));"
            parameters = [start_point, location]
            cur.execute(selectQuery, parameters)
            rows = cur.fetchall()
            distance = rows[0][0]
            if distance < x1:
                weight = 1
            if (distance > x1) and (distance < x2):
                weight = m * distance + b
            if distance > x2:
                weight = 0
            if poi_type in ref_poi_list:
                ref_poi_list[poi_type].append(weight)
                ref_poi_list[poi_type].sort(reverse=True)
            else:
                ref_poi_list[poi_type] = ''.split()
                ref_poi_list[poi_type].append(weight)
                ref_poi_list[poi_type].sort(reverse=True)
    return ref_poi_list


def check_no_of_poi(poi_list, poi_type):
    min_no_of_poi = {"Bank": 1,  # bank
                     "Grocery": 1,  #grocery
                     "Restaurant": 10,  #restaurant and coffee
                     "Shopping": 5,  #shopping
                     "Entertainment": 1,  #entertainment
                     "School": 1,  #school
                     "Library": 1,  #library
                     #"Health": 1,  #health
    }

    poi_requirement = {"Bank": True,  # bank
                       "Grocery": True,  #grocery
                       "Restaurant": True,  #restaurant and coffee
                       "Shopping": True,  #shopping
                       "Entertainment": True,  #entertainment
                       "School": True,  #school
                       "Library": True,  #library
                       #"Health": True,  #health
    }

    # poi_list can be empty when it is created for the first time using the main walkshed
    if poi_list:
        poi_list = ast.literal_eval(str(poi_list))
    full_weight_item_no = 0

    #a poi_type can b
    if poi_type in poi_list:
        if len(poi_list[poi_type]) >= min_no_of_poi[poi_type]:
            for item in poi_list[poi_type]:
                poi_weight = float(item)
                if poi_weight == 1:
                    full_weight_item_no += 1

    if full_weight_item_no >= min_no_of_poi[poi_type]:
        poi_requirement[poi_type] = False

    return poi_requirement[poi_type]


@route('/aggregation', method='POST')
def service():
    poi = request.POST.get('poi', default=None)
    start_point = request.POST.get('start_point', default=None)
    radius = request.POST.get('radius', default=None)
    distance_decay_function = request.POST.get('distance_decay_function', default=None).lower()
    if poi and start_point and radius and distance_decay_function is not None:
        return aggregation(start_point, radius, poi, distance_decay_function)


run(host='0.0.0.0', port=5364, debug=True)

