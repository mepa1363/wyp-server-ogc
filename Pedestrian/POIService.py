# -*- coding: utf-8 -*-
import json
import urllib2

from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def getPOIs(walkshed):
    polygon = getPolygon(walkshed)
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


#To get rid of non-ASCII characters
def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


@route('/poi')
def service():
    polygon = request.GET.get('walkshed', default=None)
    if polygon is not None:
        return getPOIs(polygon)


run(host='0.0.0.0', port=8365, debug=True)

#http://127.0.0.1:8365/poi?walkshed={"type":"Polygon","coordinates":[[[-114.13258446221629,51.05667765949581],[-114.13254056321318,51.05780123264723],[-114.13152943754814,51.05928339714371],[-114.12950549567188,51.06011065488163],[-114.1279654,51.0595932],[-114.12445710928647,51.062350863156894],[-114.12371101357336,51.063263785101434],[-114.12310669501387,51.06399487923505],[-114.12123542899363,51.0661290239349],[-114.11806424260443,51.06644301813297],[-114.11786253384714,51.066370448767316],[-114.1164274,51.063358],[-114.1134139,51.0622939],[-114.1131162,51.0622073],[-114.1129392,51.0620646],[-114.11184,51.0609932],[-114.1073205,51.0596571],[-114.1063016,51.060466691883235],[-114.10383914444445,51.06000902380952],[-114.10321092026163,51.05965823334367],[-114.10018115215432,51.057739378598626],[-114.09998273312733,51.05760439367275],[-114.1038694944397,51.05455092810189],[-114.10400678562115,51.054463627570605],[-114.10475924522562,51.05399662522794],[-114.10556177053202,51.053499575688136],[-114.10861280557579,51.05160815940013],[-114.11152012383799,51.049742240547495],[-114.1129164,51.0497427],[-114.11648368491431,51.04959693181472],[-114.11835347765114,51.04940523337369],[-114.1215325,51.0523811],[-114.1221979,51.0527387],[-114.122947,51.053085],[-114.12355379949769,51.05334646431694],[-114.125129,51.053914],[-114.128853,51.055076],[-114.129204,51.055165],[-114.1308835,51.0556508],[-114.13194309123665,51.05595505984363],[-114.13258446221629,51.05667765949581]]]}
