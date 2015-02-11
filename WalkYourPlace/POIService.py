# -*- coding: utf-8 -*-
import json
import urllib2

from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def getPOIs(start_point, radius):
    radius = float(radius) * 1000
    #grocery, shopping, park & entertainment, book
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

    #query example: (
    # node(around:2000,51.0461,-114.0712)[shop=convenience];
    # node(around:2000,51.0461,-114.0712)["amenity"="pub"];
    # );
    # out body;

    _amenity_query = ''
    for item in osm_amenity_list:
        _amenity_query += 'node(around:%s,%s)["amenity"="%s"];' % (radius, start_point, item)

    _feature_query = ''
    for item in osm_feature_list:
        _category_member = osm_feature_list[item]
        if len(_category_member) == 1:
            _feature_query += 'node(around:%s,%s)[%s];' % (radius, start_point, _category_member[0])
        else:
            for sub_item in _category_member:
                _feature_query += 'node(around:%s,%s)[%s];' % (radius, start_point, sub_item)

    _output = 'json'

    _query = '[out:%s];(%s);out body;' % (_output, _feature_query + _amenity_query)

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


#To get rid of non-ASCII characters
def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


# start_point = '51.098239989909565,-114.14949417114258'
# radius = '1.25'  #unit: m
# print getPOIs(start_point, radius)

@route('/poi')
def service():
    start_point = request.GET.get('start_point', default=None)
    radius = request.GET.get('radius', default=None)
    if start_point and radius is not None:
        return getPOIs(start_point, radius)


run(host='0.0.0.0', port=6365, debug=True)

#http://127.0.0.1:6365/poi?start_point=51.05723044585338,-114.11717891693115&radius=1.60934
