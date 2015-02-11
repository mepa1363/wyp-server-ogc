# -*- coding: utf-8 -*-
import ast
import collections
import json
import socket
import urllib2
import psycopg2
from bottle import route, run, request
import bottle

bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def aggregation(start_point, walkshed, crime_data, poi_data, distance_decay_function, walking_time_period):
    #list of POIs for the main walkshed
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
            poi_type_distance = distanceDecay(start_point, poi_data, walking_time_period)
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
            #list of POIs for the main walkshed
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
        #list of crimes for the main walkshed
        crime_list = dataPreparation(crime_data)
        crime_list = ast.literal_eval(crime_list)

        crime_weights = {"Arson": [1, 1, 1, 1], "Assault": [10], "Attempted Murder": [4.5, 4.5],
                         "Commercial Break-In": [.5, .5, .5, .5, .5, .5, .5, .5, .5, .5],
                         "Homicide": [9], "Residential Break-In": [.5, .5, .5, .5, .5, .5, .5, .5, .5, .5],
                         "Robbery": [2, 1.5, 1.5], "Sex Offence": [10],
                         "Theft": [.4, .4, .4, .4, .4, .4, .4, .4, .4, .4],
                         "Theft From Vehicle": [.3, .3, .3, .3, .3, .3, .3, .3, .3, .3],
                         "Vandalism": [.2, .2, .2, .2, .2, .2, .2, .2, .2, .2],
                         "Vehicle Theft": [.1, .1, .1, .1, .1, .1, .1, .1, .1, .1]}

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
                for i in xrange(crime_item_number):
                    crime_index += crime_weights[crime_item_type][i]
            else:
                for i in xrange(crime_item_weight_number):
                    crime_index += crime_weights[crime_item_type][i]

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

    #calculate the area of the walkshed
    area = calculateArea(walkshed)
    crime_polygon = walkshed[:-1]
    crime_polygon += ',"properties": {"type": "Walkshed", "area": %s, "score": "%d", "crime_index": %s, "color": "%s"}}' % (
        area, poi_index_normal, crime_index_normal, crime_color_hex)

    return crime_polygon


def dataPreparation(data):
    data_json = json.loads(data)
    data_type = []
    for item in data_json['features']:
        data_type.append(str(item['properties']['type']))
    data_type_counter = collections.Counter(data_type)
    data_for_aggregation = str(data_type_counter)[8:-1]
    return data_for_aggregation


def distanceDecay(start_point, data, walking_time_period):
    #first turning point (5 min = 300s)
    x1 = 300
    y1 = 1
    #second turning point (15 min = 900s)
    x2 = int(walking_time_period) * 60
    y2 = 0
    #in order to get rid of division by zero when x1=x2
    #the point is when x2<x1 (threshold) then all the weights will be 1
    if x1 == x2:
        x2 -= 1
    #linear equation
    m = (y2 - y1) / float(x2 - x1)
    b = y2 - m * x2
    data_json = json.loads(data)
    ref_poi_list = {}
    for item in data_json['features']:
        otp_url = "http://www.gisciencegroup.ucalgary.ca:8080/opentripplanner-api-webapp/ws/plan?arriveBy=false&time=6%3A58pm&ui_date=1%2F10%2F2013&mode=BICYCLE&optimize=QUICK&maxWalkDistance=5000&walkSpeed=1.38&date=2013-01-10&"
        location = item['geometry']['coordinates']
        location = '%s,%s' % (location[1], location[0])
        poi_type = str(item['properties']['type'])
        otp_url += "&toPlace=%s&fromPlace=%s" % (location, start_point)

        #check if the requirement is met (true/false)
        _isContinued = check_no_of_poi(ref_poi_list, poi_type)
        if _isContinued:
            try:
                otp_data = urllib2.urlopen(otp_url).read()
                otp_data = json.loads(otp_data)
            except urllib2.URLError, e:
                print e.reason
            except socket.timeout:
                print "Timed out!"
                #time distance between start point and other POIs in seconds
            if otp_data['plan']:
                time_distance = otp_data['plan']['itineraries'][0]['walkTime']
                if time_distance < x1:
                    weight = 1
                if (time_distance > x1) and (time_distance < x2):
                    weight = m * time_distance + b
                if time_distance > x2:
                    weight = 0
            else:
                weight = 0
            if poi_type in ref_poi_list:
                ref_poi_list[poi_type].append(weight)
                sorted(ref_poi_list[poi_type], key=int, reverse=True)
                ref_poi_list[poi_type].sort(reverse=True)
            else:
                ref_poi_list[poi_type] = ''.split()
                ref_poi_list[poi_type].append(weight)
                ref_poi_list[poi_type].sort(reverse=True)
    return ref_poi_list


def calculateArea(polygon):
    polygonJSON = json.loads(polygon)
    finalPolygon = "POLYGON(("
    for point in polygonJSON['coordinates'][0]:
        longitude = point[0]
        latitude = point[1]
        vertex = "%s %s" % (longitude, latitude)
        finalPolygon += "%s," % (vertex,)
    finalPolygon = finalPolygon[:-1]
    finalPolygon += "))"
    import config

    connection_string = config.conf()
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    select_query = "SELECT ST_Area(ST_Transform(ST_GeomFromText(%s, 4326), 3776));"
    parameters = [finalPolygon]
    cur.execute(select_query, parameters)
    rows = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return rows[0]


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


@route('/aggregation', method='POST')
def service():
    poi = request.POST.get('poi', default=None)
    crime = request.POST.get('crime', default=None)
    walkshed = request.POST.get('bikeshed', default=None)
    start_point = request.POST.get('start_point', default=None)
    distance_decay_function = request.POST.get('distance_decay_function', default=None).lower()
    walking_time_period = request.POST.get('biking_time_period', default=None)
    if start_point and poi and crime and walkshed and distance_decay_function and walking_time_period is not None:
        return aggregation(start_point, walkshed, crime, poi, distance_decay_function, walking_time_period)


run(host='0.0.0.0', port=7364, debug=True)

