# -*- coding: utf-8 -*-
import json
import urllib2

from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def getPOIs(polygon):
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


def getPolygon(polygonJSON):
    #polygonJSON = json.loads(polygon)
    new_polygon = ''
    for point in polygonJSON['coordinates'][0]:
        longitude = point[0]
        latitude = point[1]
        new_polygon += '%s %s ' % ("{0:.3f}".format(float(latitude)), "{0:.3f}".format(float(longitude)))
    new_polygon = new_polygon[:-1]
    return new_polygon


def invoke(walkshed):
    walkshed = json.loads(walkshed)
    if walkshed['type'] == 'FeatureCollection':
        _collected_poi = '{"type": "FeatureCollection", "features": ['
        for item in walkshed['features']:
            polygon = getPolygon(item['geometry'])
            _poi = getPOIs(polygon)[43:-2]
            if _poi != "":
                _collected_poi += '%s,' % (_poi,)
        _collected_poi = _collected_poi[:-1]
        _collected_poi += ']}'

    elif walkshed['type'] == 'Polygon':
        polygon = getPolygon(walkshed)
        _collected_poi = getPOIs(polygon)
    elif walkshed['type'] == 'Feature':
        polygon = getPolygon(walkshed['geometry'])
        _collected_poi = getPOIs(polygon)
    return _collected_poi


#walkshed = """{"type": "FeatureCollection", "features": [{"type": "Feature","geometry": {"type":"Polygon","coordinates":[[[-114.062839120934,51.0468539551355],[-114.062954062,51.0466915177],[-114.064034943,51.0460573708],[-114.065407,51.045259],[-114.065519077,51.0452222931],[-114.066875346,51.0461271966],[-114.06786752,51.0467945439],[-114.068329972,51.0475962018],[-114.067801571,51.0479032245],[-114.067225408424,51.0482431387224],[-114.067641816,51.0485222603],[-114.067685511145,51.0486084526112],[-114.067766345,51.0485837731],[-114.069092232,51.0495087248],[-114.069482513294,51.0497829806501],[-114.0701734,51.0495435],[-114.071392390308,51.0503880901554],[-114.071534349,51.0503032989],[-114.07357888,51.049835458],[-114.074753037,51.0506334812],[-114.075384748325,51.0510800549367],[-114.075997474,51.0507319322],[-114.078448103,51.0510291453],[-114.0793834,51.0516994],[-114.079485428,51.0522629191],[-114.079432711,51.0524967371],[-114.078494792,51.0532864736],[-114.0784632,51.053293],[-114.076443266,51.0537031554],[-114.076365701974,51.0537003890196],[-114.076457206,51.0537399058],[-114.080917071,51.053806494],[-114.080660898,51.0555355098],[-114.08007294,51.0573857648],[-114.079185445,51.0586273867],[-114.0773318,51.0607683],[-114.076870156,51.0612532144],[-114.075574194,51.0623056998],[-114.074324912,51.0628583391],[-114.071545416,51.0630263728],[-114.067477968,51.0638053697],[-114.06507937845,51.0624897670513],[-114.065278106,51.0633566734],[-114.065020684,51.0635163374],[-114.064248539535,51.0639984583182],[-114.0648819,51.0644109032],[-114.065017287,51.0652420832],[-114.0650174,51.0653786],[-114.065016844,51.0655159865],[-114.064695547399,51.0658048480514],[-114.0649469,51.0660285],[-114.0649639,51.0660518],[-114.0649917,51.0660952],[-114.064992052,51.0662171621],[-114.06477771,51.0670218956],[-114.064063852,51.0674510278],[-114.063369729,51.0678842612],[-114.063359848653,51.0678903230522],[-114.064104625,51.0683500156],[-114.064846596,51.0688023625],[-114.065478976,51.0697088748],[-114.064751417,51.0701670521],[-114.064023851,51.0706204426],[-114.064004141,51.0706329106],[-114.063289399,51.0710667823],[-114.0625367,51.0715195],[-114.061093947,51.0706178294],[-114.059926533,51.0698993579],[-114.059629145,51.0697132154],[-114.060223454,51.0687953086],[-114.0605947,51.0685605116],[-114.061643569047,51.0678687200412],[-114.060982975,51.0674443581],[-114.0611953,51.0669026],[-114.061582445418,51.0660736628229],[-114.060201481,51.0643946333],[-114.060849379491,51.0639877080408],[-114.060516502,51.0637693878],[-114.059926373,51.0633854497],[-114.059828667,51.0633227819],[-114.059993169,51.0624355255],[-114.060635924945,51.0620101458516],[-114.059932011,51.0615638193],[-114.059893008,51.0615387784],[-114.059896507,51.0606434692],[-114.059936517,51.0606186809],[-114.060909533623,51.0600200388285],[-114.06048611,51.0597448734],[-114.059548794,51.0588566165],[-114.059918181491,51.0586064388741],[-114.0540431,51.0514593],[-114.0533144,51.0512801],[-114.052601539,51.0511144451],[-114.0528187,51.0511543],[-114.054118414,51.0513852293],[-114.0552244,51.0517546],[-114.056941,51.0522187],[-114.0577306,51.0524668],[-114.0602111,51.053028],[-114.063039954,51.0525042131],[-114.065053946,51.0518200189],[-114.06572350114,51.0515838766649],[-114.065085923,51.0513453975],[-114.06499144,51.0512813774],[-114.063691621057,51.050396523783],[-114.062642644,51.0509897818],[-114.061559839,51.0502428182],[-114.060314975,51.0493846562],[-114.060130305,51.0492549215],[-114.060318469,51.0483097727],[-114.060420023,51.0482501741],[-114.061860515,51.0474146005],[-114.062839120934,51.0468539551355]]]}}]}"""


#To get rid of non-ASCII characters
def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


@route('/poi')
def service():
    polygon = request.GET.get('walkshed', default=None)
    if polygon is not None:
        return invoke(polygon)


run(host='0.0.0.0', port=9365, debug=True)

#http://127.0.0.1:8365/poi?walkshed={"type":"Polygon","coordinates":[[[-114.13258446221629,51.05667765949581],[-114.13254056321318,51.05780123264723],[-114.13152943754814,51.05928339714371],[-114.12950549567188,51.06011065488163],[-114.1279654,51.0595932],[-114.12445710928647,51.062350863156894],[-114.12371101357336,51.063263785101434],[-114.12310669501387,51.06399487923505],[-114.12123542899363,51.0661290239349],[-114.11806424260443,51.06644301813297],[-114.11786253384714,51.066370448767316],[-114.1164274,51.063358],[-114.1134139,51.0622939],[-114.1131162,51.0622073],[-114.1129392,51.0620646],[-114.11184,51.0609932],[-114.1073205,51.0596571],[-114.1063016,51.060466691883235],[-114.10383914444445,51.06000902380952],[-114.10321092026163,51.05965823334367],[-114.10018115215432,51.057739378598626],[-114.09998273312733,51.05760439367275],[-114.1038694944397,51.05455092810189],[-114.10400678562115,51.054463627570605],[-114.10475924522562,51.05399662522794],[-114.10556177053202,51.053499575688136],[-114.10861280557579,51.05160815940013],[-114.11152012383799,51.049742240547495],[-114.1129164,51.0497427],[-114.11648368491431,51.04959693181472],[-114.11835347765114,51.04940523337369],[-114.1215325,51.0523811],[-114.1221979,51.0527387],[-114.122947,51.053085],[-114.12355379949769,51.05334646431694],[-114.125129,51.053914],[-114.128853,51.055076],[-114.129204,51.055165],[-114.1308835,51.0556508],[-114.13194309123665,51.05595505984363],[-114.13258446221629,51.05667765949581]]]}
