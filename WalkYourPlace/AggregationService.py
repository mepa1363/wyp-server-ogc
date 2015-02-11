# -*- coding: utf-8 -*-
import ast
import collections
import json
import math

import psycopg2
from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def aggregation(start_point, radius, crime_data, poi_data, distance_decay_function):
    if poi_data != '"NULL"':
        poi_weights = {"Bank": [1],  #bank
                       "Grocery": [3],  #grocery
                       "Restaurant": [.75, .45, .25, .25, .225, .225, .225, .225, .2, .2],  #restaurant and coffee
                       "Shopping": [.5, .45, .4, .35, .3],  #shopping
                       "Entertainment": [1],  #entertainment
                       "School": [1],  #school
                       "Library": [1],  #library
                       "Health": [1]  #health
        }

        #calculate the sum of weights for poi
        poi_sum = 0
        for i in xrange(len(poi_weights)):
            poi_weights_number = poi_weights.items()[i][1]
            for j in xrange(len(poi_weights_number)):
                poi_sum += poi_weights_number[j]

        #calculate raw poi score for the main walkshed
        poi_index = 0

        if distance_decay_function == 'true':
            #list of POIs for the main walkshed
            poi_type_distance = distanceDecay(start_point, poi_data, radius)
            poi_list = ast.literal_eval(str(poi_type_distance))
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

    if crime_data != '"NULL"':
        crime_weights = {"Arson": [1, 1, 1, 1], "Assault": [10], "Attempted Murder": [4.5, 4.5],
                         "Commercial Break-In": [.5, .5, .5, .5, .5, .5, .5, .5, .5, .5],
                         "Homicide": [9], "Residential Break-In": [.5, .5, .5, .5, .5, .5, .5, .5, .5, .5],
                         "Robbery": [2, 1.5, 1.5], "Sex Offence": [10],
                         "Theft": [.4, .4, .4, .4, .4, .4, .4, .4, .4, .4],
                         "Theft From Vehicle": [.3, .3, .3, .3, .3, .3, .3, .3, .3, .3],
                         "Vandalism": [.2, .2, .2, .2, .2, .2, .2, .2, .2, .2],
                         "Vehicle Theft": [.1, .1, .1, .1, .1, .1, .1, .1, .1, .1]}

        #list of crimes for the main walkshed
        crime_list = dataPreparation(crime_data)
        crime_list = ast.literal_eval(crime_list)

        #calculate the sum of weights for crime
        crime_sum = 0
        for i in xrange(len(crime_weights)):
            crime_weights_number = crime_weights.items()[i][1]
            for j in xrange(len(crime_weights_number)):
                crime_sum += crime_weights_number[j]

        #calculate raw crime score for the main walkshed
        crime_index = 0
        for i in xrange(len(crime_list)):
            crime_item_type = crime_list.items()[i][0]
            crime_item_number = crime_list.items()[i][1]
            crime_item_weight_number = len(crime_weights[crime_item_type])
            if crime_item_weight_number >= crime_item_number:
                for j in xrange(crime_item_number):
                    crime_index += crime_weights[crime_item_type][j]
            else:
                for j in xrange(crime_item_weight_number):
                    crime_index += crime_weights[crime_item_type][j]

        #calculate normalized crime score (percentage) for the main walkshed
        crime_index_normal = round(crime_index / crime_sum * 100)
    else:
        crime_index_normal = 0

    if (crime_index_normal >= 0) and (crime_index_normal < 20):
        crime_color_hex = '#39B54A'
    elif (crime_index_normal >= 20) and (crime_index_normal < 40):
        crime_color_hex = '#8DC63F'
    elif (crime_index_normal >= 40) and (crime_index_normal < 60):
        crime_color_hex = '#FFF200'
    elif (crime_index_normal >= 60) and (crime_index_normal < 80):
        crime_color_hex = '#F7941E'
    elif (crime_index_normal >= 80) and (crime_index_normal <= 100):
        crime_color_hex = '#ED1C24'

    radius = float(radius) * 1000
    #calculate area of the walkshed
    area = math.pow(radius, 2) * math.pi
    start_point = start_point.split(',')
    start_point = "%s,%s" % (start_point[1], start_point[0])
    #there is no standard specification to encode circle as a geojson object, but there is a proposal that I used to do that:
    #https://github.com/GeoJSONWG/geojson-spec/wiki/Proposal---Circles-and-Ellipses-Geoms
    crime_circle = """{"type": "Circle", "coordinates": [%s], "radius": %s, "properties": {"radius_units": "m", "area": %s, "score": "%d", "crime_index": %s, "color": "%s"}}""" % (
        start_point, radius, area, poi_index_normal, crime_index_normal, crime_color_hex)

    return crime_circle


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

    #first turning point (.25 miles)
    x1 = 402.336
    y1 = 1
    #second turning point (1 mile)
    x2 = float(radius) * 1000  #1609.34
    y2 = 0
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
    min_no_of_poi = {"Bank": 1,  #bank
                     "Grocery": 1,  #grocery
                     "Restaurant": 10,  #restaurant and coffee
                     "Shopping": 5,  #shopping
                     "Entertainment": 1,  #entertainment
                     "School": 1,  #school
                     "Library": 1,  #library
                     "Health": 1  #health
    }

    poi_requirement = {"Bank": True,  #bank
                       "Grocery": True,  #grocery
                       "Restaurant": True,  #restaurant and coffee
                       "Shopping": True,  #shopping
                       "Entertainment": True,  #entertainment
                       "School": True,  #school
                       "Library": True,  #library
                       "Health": True  #health
    }
    #poi_list can be empty when it is created for the first time using the main walkshed
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


@route('/aggregation')
def service():
    start_point = request.GET.get('start_point', default=None)
    radius = request.GET.get('radius', default=None)
    poi = request.GET.get('poi', default=None)
    crime = request.GET.get('crime', default=None)
    distance_decay_function = request.GET.get('distance_decay_function', default=None)
    if start_point and radius and poi and crime and distance_decay_function is not None:
        return aggregation(start_point, radius, crime, poi, distance_decay_function)


run(host='0.0.0.0', port=6364, debug=True)

#http://127.0.0.1:6364/aggregation?start_point=51.05723044585338,-114.11717891693115&radius=1.60934&poi={"type": "FeatureCollection", "features": [{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.134837,51.0661097]}, "properties": {"name": "Foothills Medical Centre", "type": "Health", "icon": "http://webmapping.ucalgary.ca/maki/hospital-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1214326,51.0703261]}, "properties": {"name": "McMahon Stadium", "type": "Entertainment", "icon": "http://webmapping.ucalgary.ca/maki/playground-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1029714,51.0658026]}, "properties": {"name": "Safeway", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1081809,51.0665754]}, "properties": {"name": "Juree's Thai Place", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/restaurant-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1171178,51.0714039]}, "properties": {"name": "Stadium Nissan", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1313272,51.0581672]}, "properties": {"name": "School", "type": "School", "icon": "http://webmapping.ucalgary.ca/maki/school-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1166708,51.069971]}, "properties": {"name": "Saigon Y2K", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/restaurant-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1168394,51.0704339]}, "properties": {"name": "Dairy Queen", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/fast-food-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1168768,51.0707531]}, "properties": {"name": "Big T's", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/restaurant-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1285067,51.0673516]}, "properties": {"name": "Gus's Cafe and Pizzeria", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/cafe-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1340084,51.0645684]}, "properties": {"name": "Foothills Hospital", "type": "Health", "icon": "http://webmapping.ucalgary.ca/maki/hospital-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1099305,51.0463083]}, "properties": {"name": "Pumphouse Theatre", "type": "Entertainment", "icon": "http://webmapping.ucalgary.ca/maki/theatre-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1073937,51.0664405]}, "properties": {"name": "Second Cup", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/cafe-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.0950631,51.0595395]}, "properties": {"name": "South Silk Road Chinese Restaurant", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/restaurant-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1358175,51.0579432]}, "properties": {"name": "Oriental Palace", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/restaurant-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1366383,51.0580781]}, "properties": {"name": "Lic's", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/cafe-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1365417,51.058041]}, "properties": {"name": "Avatara Pizza", "type": "Restaurant", "icon": "http://webmapping.ucalgary.ca/maki/fast-food-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1069569,51.0468975]}, "properties": {"name": "Renfrew Chrylser Jeep", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1057794,51.0540165]}, "properties": {"name": "Oasis Hair Salon", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1057581,51.05395]}, "properties": {"name": "Soul Food Books Etc.", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/library-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1057927,51.0542719]}, "properties": {"name": "Oasis Flower Shop", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1077032,51.0664423]}, "properties": {"name": "Highlander Wine and Spirits", "type": "Shopping", "icon": "http://webmapping.ucalgary.ca/maki/alcohol-shop-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1284918,51.0675382]}, "properties": {"name": "Calgary Laboratory Services Patient Service Centre", "type": "Health", "icon": "http://webmapping.ucalgary.ca/maki/hospital-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.0995402,51.065479]}, "properties": {"name": "Calgary Laboratory Services Patient Service Centre", "type": "Health", "icon": "http://webmapping.ucalgary.ca/maki/hospital-18.png"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.1283452,51.0673883]}, "properties": {"name": "Foothills Medical Clinic", "type": "Health", "icon": "http://webmapping.ucalgary.ca/maki/hospital-18.png"}}]}&crime={"type": "FeatureCollection", "features": [{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.125793,51.056122]}, "properties": {"id": 132, "time": "2012-11-6 16:30:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.100792,51.064167]}, "properties": {"id": 148, "time": "2012-11-8 12:0:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112068,51.064468]}, "properties": {"id": 154, "time": "2012-11-9 7:45:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.101593,51.059536]}, "properties": {"id": 208, "time": "2012-11-7 12:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.125206,51.066307]}, "properties": {"id": 241, "time": "2012-11-10 13:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.125793,51.056122]}, "properties": {"id": 285, "time": "2012-11-6 16:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 299, "time": "2012-11-7 13:40:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 302, "time": "2012-11-7 15:23:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.108696,51.050079]}, "properties": {"id": 305, "time": "2012-11-7 15:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.100792,51.064167]}, "properties": {"id": 336, "time": "2012-11-8 12:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112068,51.064468]}, "properties": {"id": 366, "time": "2012-11-9 7:45:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.107796,51.056175]}, "properties": {"id": 467, "time": "2012-11-9 18:0:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.125206,51.066307]}, "properties": {"id": 473, "time": "2012-11-10 13:0:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.118515,51.053444]}, "properties": {"id": 712, "time": "2012-11-20 23:31:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112785,51.060883]}, "properties": {"id": 840, "time": "2012-11-21 16:0:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.111565,51.052135]}, "properties": {"id": 950, "time": "2012-11-18 23:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112518,51.052135]}, "properties": {"id": 956, "time": "2012-11-18 14:14:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.136864,51.056927]}, "properties": {"id": 975, "time": "2012-11-19 20:28:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 1027, "time": "2012-11-15 18:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.101395,51.051014]}, "properties": {"id": 1129, "time": "2012-11-20 16:58:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112785,51.060883]}, "properties": {"id": 1135, "time": "2012-11-21 16:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.132828,51.066589]}, "properties": {"id": 1296, "time": "2012-11-24 13:50:00","type": "Sex Offence"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.108406,51.06675]}, "properties": {"id": 1459, "time": "2012-11-27 23:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.104164,51.06712]}, "properties": {"id": 1475, "time": "2012-11-28 17:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.136047,51.059322]}, "properties": {"id": 1633, "time": "2012-12-3 19:0:00","type": "Commercial Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.137238,51.051895]}, "properties": {"id": 1669, "time": "2012-11-28 21:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 1698, "time": "2012-12-2 8:15:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 1744, "time": "2012-12-2 12:20:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.136047,51.059322]}, "properties": {"id": 1759, "time": "2012-12-3 19:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.130913,51.064659]}, "properties": {"id": 1878, "time": "2012-12-15 6:15:00","type": "Assault"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.128967,51.06918]}, "properties": {"id": 2071, "time": "2012-12-12 10:50:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.104164,51.06712]}, "properties": {"id": 2132, "time": "2012-12-15 23:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 2196, "time": "2012-12-19 19:10:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.094894,51.05555]}, "properties": {"id": 2306, "time": "2013-1-11 22:10:00","type": "Assault"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.114799,51.069458]}, "properties": {"id": 2389, "time": "2013-1-13 20:30:00","type": "Robbery"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.110275,51.066925]}, "properties": {"id": 2391, "time": "2013-1-17 4:10:00","type": "Robbery"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.103966,51.065289]}, "properties": {"id": 2465, "time": "2013-1-15 10:15:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 2512, "time": "2013-1-12 12:5:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 2548, "time": "2013-1-14 14:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.094894,51.05555]}, "properties": {"id": 2609, "time": "2013-1-11 22:10:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.130913,51.064659]}, "properties": {"id": 2662, "time": "2012-12-2 1:0:00","type": "Assault"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112785,51.060883]}, "properties": {"id": 2752, "time": "2012-12-22 15:15:00","type": "Assault"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.122742,51.056385]}, "properties": {"id": 2785, "time": "2012-12-26 4:50:00","type": "Assault"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.103638,51.060665]}, "properties": {"id": 2977, "time": "2012-12-14 0:0:00","type": "Commercial Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.121696,51.055237]}, "properties": {"id": 3126, "time": "2012-12-20 8:0:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112785,51.060883]}, "properties": {"id": 3132, "time": "2012-12-22 15:15:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.122742,51.056385]}, "properties": {"id": 3146, "time": "2012-12-26 4:50:00","type": "Residential Break-In"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.101105,51.050312]}, "properties": {"id": 3225, "time": "2012-12-26 4:10:00","type": "Robbery"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.117393,51.068134]}, "properties": {"id": 3274, "time": "2012-12-1 0:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.106819,51.067226]}, "properties": {"id": 3611, "time": "2012-12-31 2:0:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.112831,51.061737]}, "properties": {"id": 3614, "time": "2013-1-1 21:30:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.116272,51.064144]}, "properties": {"id": 3618, "time": "2013-1-1 18:30:00","type": "Theft From Vehicle"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 3679, "time": "2012-12-4 14:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.120911,51.052612]}, "properties": {"id": 3748, "time": "2012-12-7 9:15:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 3814, "time": "2012-12-9 11:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 3885, "time": "2012-12-12 19:20:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.103638,51.060665]}, "properties": {"id": 3896, "time": "2012-12-14 0:0:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.099167,51.06469]}, "properties": {"id": 3928, "time": "2012-12-19 11:30:00","type": "Theft"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.130913,51.064659]}, "properties": {"id": 4050, "time": "2012-12-20 21:55:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.101105,51.050312]}, "properties": {"id": 4104, "time": "2012-12-26 4:20:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.122742,51.056385]}, "properties": {"id": 4105, "time": "2012-12-26 4:50:00","type": "Vandalism"}},{"type": "Feature","geometry": {"type": "Point", "coordinates":[-114.113167,51.059937]}, "properties": {"id": 4264, "time": "2013-1-8 2:14:00","type": "Vandalism"}}]}&distance_decay_function=true
