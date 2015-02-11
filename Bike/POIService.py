# -*- coding: utf-8 -*-
import json
import urllib2

from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def getPOIs(walkshed):
    polygon = getPolygon(walkshed)
    # grocery, shopping, park & entertainment, book
    #usage: node[shop=bakery]
    osm_feature_list = {
        'grocery': ['shop=alcohol', 'shop=bakery', 'shop=beverages', 'shop=butcher', 'shop=convenience', 'shop=general',
                    'shop=department_store', 'shop=farm', 'shop=mall', 'shop=supermarket'],  #grocery
        'shopping': ['shop'],  #shopping
        'park&entertainment': ['leisure', 'historic', 'sport'],  #entertainment
        'bookstore': ['shop=books']  #library
    }

    #bank, restaurant & cafe, park & entertainment, school, book, hospital
    #usage: node["amenity=atm"]
    osm_amenity_list = {'atm', 'bank',  #bank
                        'bar', 'pub', 'restaurant', 'fast_food', 'food_court', 'cafe',  #restaurant
                        'marketplace',  #shopping
                        'arts_centre', 'cinema', 'nightclub', 'theatre',
                        #entertainment and also from osm_feature_list
                        'school', 'kindergarten', 'college', 'university',  #school
                        'library',  #library and also from osm_feature_list
                        'clinic', 'dentist', 'doctors', 'hospital', 'pharmacy', 'veterinary'  #health
    }

    _amenity_query = ''
    for item in osm_amenity_list:
        _amenity_query += 'node(poly:"%s")["amenity"="%s"];' % (polygon, item)

    _feature_query = ''
    for item in osm_feature_list:
        _category_member = osm_feature_list[item]
        if len(_category_member) == 1:
            _feature_query += 'node(poly:"%s")[%s];' % (polygon, _category_member[0])
        else:
            for sub_item in _category_member:
                _feature_query += 'node(poly:"%s")[%s];' % (polygon, sub_item)

    _output = 'json'

    _query = '[out:%s];(%s);out body;' % (_output, _amenity_query + _feature_query)

    _overpass_url = 'http://overpass-api.de/api/interpreter'

    _overpass_request = urllib2.Request(url=_overpass_url, data=_query, headers={'Content-Type': 'application/json'})

    poi_data = urllib2.urlopen(_overpass_request).read()

    #getting rid of non-ASCII characters
    poi_data = removeNonAscii(poi_data)

    #getting rid of special characters like &
    poi_data = poi_data.replace('&', 'and')
    poi_data = poi_data.replace(';', ' ')

    poi_data_json = json.loads(poi_data)

    _elements = poi_data_json['elements']

    result_json = '"NULL"'

    if len(_elements) >= 1:

        result_json = '{"type": "FeatureCollection", "features": ['

        for item in _elements:
            _lat = item['lat']
            _lon = item['lon']
            _location = "[%s,%s]" % (_lon, _lat)
            _tags = item['tags']

            _icon = 'http://webmapping.ucalgary.ca/maki/marker-18.png'
            _type = 'POI'
            #POI types: Bank, Restaurant, Shopping, Grocery, Entertainment, School, Library, Health
            if 'shop' in _tags:
                _type = 'Grocery'
                if _tags['shop'] == 'alcohol' or _tags['shop'] == 'beverages':
                    _icon = 'http://webmapping.ucalgary.ca/maki/alcohol-shop-18.png'
                elif _tags['shop'] == 'bakery':
                    _icon = 'http://webmapping.ucalgary.ca/maki/bakery-18.png'
                elif _tags['shop'] == 'books':
                    _icon = 'http://webmapping.ucalgary.ca/maki/library-18.png'
                else:
                    _icon = 'http://webmapping.ucalgary.ca/maki/shop-18.png'
                    _type = 'Shopping'
            elif 'leisure' in _tags:
                _icon = 'http://webmapping.ucalgary.ca/maki/playground-18.png'
                _type = 'Entertainment'
            elif 'sport' in _tags:
                _icon = 'http://webmapping.ucalgary.ca/maki/basketball-18.png'
                _type = 'Entertainment'
            elif 'historic' in _tags:
                _icon = 'http://webmapping.ucalgary.ca/maki/town-hall-18.png'
                _type = 'Entertainment'
            elif 'amenity' in _tags:
                if _tags['amenity'] == 'atm' or _tags['amenity'] == 'bank':
                    _icon = 'http://webmapping.ucalgary.ca/maki/bank-18.png'
                    _type = 'Bank'
                elif _tags['amenity'] == 'bar' or _tags['amenity'] == 'pub':
                    _icon = 'http://webmapping.ucalgary.ca/maki/bar-18.png'
                    _type = 'Restaurant'
                elif _tags['amenity'] == 'restaurant':
                    _icon = 'http://webmapping.ucalgary.ca/maki/restaurant-18.png'
                    _type = 'Restaurant'
                elif _tags['amenity'] == 'cafe':
                    _icon = 'http://webmapping.ucalgary.ca/maki/cafe-18.png'
                    _type = 'Restaurant'
                elif _tags['amenity'] == 'fast_food' or _tags['amenity'] == 'food_court':
                    _icon = 'http://webmapping.ucalgary.ca/maki/fast-food-18.png'
                    _type = 'Restaurant'
                elif _tags['amenity'] == 'marketplace':
                    _icon = 'http://webmapping.ucalgary.ca/maki/shop-18.png'
                    _type = 'Grocery'
                elif _tags['amenity'] == 'arts_centre':
                    _icon = 'http://webmapping.ucalgary.ca/maki/art-gallery-18.png'
                    _type = 'Entertainment'
                elif _tags['amenity'] == 'cinema':
                    _icon = 'http://webmapping.ucalgary.ca/maki/cinema-18.png'
                    _type = 'Entertainment'
                elif _tags['amenity'] == 'nightclub':
                    _icon = 'http://webmapping.ucalgary.ca/maki/music-18.png'
                    _type = 'Entertainment'
                elif _tags['amenity'] == 'theatre':
                    _icon = 'http://webmapping.ucalgary.ca/maki/theatre-18.png'
                    _type = 'Entertainment'
                elif _tags['amenity'] == 'school' or _tags['amenity'] == 'kindergarten':
                    _icon = 'http://webmapping.ucalgary.ca/maki/school-18.png'
                    _type = 'School'
                elif _tags['amenity'] == 'college' or _tags['amenity'] == 'university':
                    _icon = 'http://webmapping.ucalgary.ca/maki/college-18.png'
                    _type = 'School'
                elif _tags['amenity'] == 'library':
                    _icon = 'http://webmapping.ucalgary.ca/maki/library-18.png'
                    _type = 'Library'
                elif _tags['amenity'] == 'hospital' or _tags['amenity'] == 'clinic' or _tags['amenity'] == 'dentist' or \
                                _tags['amenity'] == 'doctors' or _tags['amenity'] == 'veterinary':
                    _icon = 'http://webmapping.ucalgary.ca/maki/hospital-18.png'
                    _type = 'Health'
                elif _tags['amenity'] == 'pharmacy':
                    _icon = 'http://webmapping.ucalgary.ca/maki/pharmacy-18.png'
                    _type = 'Health'

            if 'name' in _tags:
                _name = _tags['name']
            else:
                _name = _type
            result_json += '{"type": "Feature","geometry": {"type": "Point", "coordinates":%s}, "properties": {"name": "%s", "type": "%s", "icon": "%s"}},' % (
                _location, _name, _type, _icon)

        result_json = result_json[:-1]
        result_json += ']}'

    return result_json


def getPolygon(polygon):
    polygonJSON = json.loads(polygon)
    new_polygon = ''
    for point in polygonJSON['coordinates'][0]:
        longitude = point[0]
        latitude = point[1]
        new_polygon += '%s %s ' % ("{0:.3f}".format(float(latitude)), "{0:.3f}".format(float(longitude)))
    new_polygon = new_polygon[:-1]
    return new_polygon


# To get rid of non-ASCII characters
def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


@route('/poi')
def service():
    polygon = request.GET.get('bikeshed', default=None)
    if polygon is not None:
        return getPOIs(polygon)


run(host='0.0.0.0', port=7365, debug=True)

#http://127.0.0.1:7365/poi?bikeshed={"type":"Polygon","coordinates":[[[-114.1208126,51.0524827],[-114.1175544,51.0497981],[-114.1168411,51.0466604],[-114.1122553,51.0449444],[-114.1111382,51.0445466],[-114.1066318,51.0431373],[-114.1043556,51.0422568],[-114.1006652,51.0393066],[-114.098224,51.037759],[-114.0946774,51.0365493],[-114.093059,51.0358619],[-114.0900645,51.0364087],[-114.0870391,51.0356823],[-114.0826417,51.0342973],[-114.0793853,51.0341756],[-114.0777963,51.0341865],[-114.0757707,51.0324817],[-114.0764641,51.0289772],[-114.0770038,51.0280467],[-114.07688,51.02801],[-114.0729523,51.028067],[-114.0715271,51.0278292],[-114.0714073,51.0278414],[-114.0691487,51.0295385],[-114.0666477,51.029554],[-114.0664406,51.0295428],[-114.0641234,51.029468],[-114.0622188,51.0291729],[-114.0598283,51.0287194],[-114.057018,51.0304629],[-114.0537827,51.0300321],[-114.0527137,51.0296971],[-114.05117,51.0301],[-114.0508041,51.0311923],[-114.0505227,51.0353392],[-114.0489741,51.036797],[-114.0478927,51.0385562],[-114.0447728,51.0408772],[-114.0423213,51.038672],[-114.0422311,51.0378341],[-114.0435281,51.0342064],[-114.0410676,51.0329534],[-114.0389801,51.03253],[-114.0367888,51.0328699],[-114.0361923,51.0341044],[-114.0339596,51.037828],[-114.031019,51.0378174],[-114.0302658,51.037832],[-114.0283611,51.0378328],[-114.0251465,51.0357703],[-114.0229154,51.0378149],[-114.0218333,51.04083],[-114.0207416,51.0454872],[-114.0208483,51.0455527],[-114.0229463,51.0456828],[-114.0267342,51.0461391],[-114.0304292,51.0488343],[-114.0316552,51.0523672],[-114.0324098,51.0536285],[-114.0330147,51.0545338],[-114.0350247,51.056571],[-114.037403,51.059691],[-114.0391971,51.0607535],[-114.0418407,51.0618351],[-114.0449565,51.0632607],[-114.0483451,51.0654994],[-114.0508071,51.066861],[-114.0524816,51.0683544],[-114.0561274,51.0707114],[-114.0599334,51.0737495],[-114.0618425,51.0751582],[-114.062422,51.075515],[-114.0650363,51.0765119],[-114.0674809,51.0774051],[-114.0715384,51.0778378],[-114.0740104,51.0764884],[-114.0764614,51.0742758],[-114.0789154,51.0727741],[-114.0831163,51.0700943],[-114.085001,51.0691963],[-114.08733,51.0678504],[-114.0882333,51.0655947],[-114.0919892,51.0643545],[-114.0940921,51.0637082],[-114.0961298,51.0622795],[-114.0978394,51.0611861],[-114.1006879,51.0596598],[-114.1038357,51.0603422],[-114.1063016,51.0607218],[-114.1104544,51.0591213],[-114.1129418,51.0591208],[-114.1140131,51.0591206],[-114.1154635,51.0586516],[-114.1165808,51.058182],[-114.1184853,51.0572198],[-114.1203235,51.0528695],[-114.1208126,51.0524827]]]}
