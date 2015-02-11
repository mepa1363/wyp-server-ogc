import json

import psycopg2
from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024

#This function returns the crime happened within the given polygon
def pointInPolygon(polygon):
    import config

    connection_string = config.conf()

    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    polygonJSON = json.loads(polygon)
    finalPolygon = "POLYGON(("
    for point in polygonJSON['coordinates'][0]:
        longitude = point[0]
        latitude = point[1]
        vertex = "%s %s" % (longitude, latitude)
        finalPolygon += "%s," % (vertex,)
    finalPolygon = finalPolygon[:-1]
    finalPolygon += "))"
    selectQuery = "SELECT id, ST_AsText(crime_location), crime_time, crime_type FROM cps_crime_data.crime_data WHERE ST_Within(crime_location, ST_GeomFromText(%s, 4326));"
    parameters = [finalPolygon]
    cur.execute(selectQuery, parameters)
    rows = cur.fetchall()
    if len(rows) > 0:
        result_json = '{"type": "FeatureCollection", "features": ['
        for i in xrange(len(rows)):
            id = rows[i][0]
            location = rows[i][1]
            location = location[6:].split(' ')
            longitude = location[0]
            latitude = location[1][:-1]
            location = "[%s,%s]" % (longitude, latitude)
            time = rows[i][2]
            time = "%s-%s-%s %s:%s:00" % (time.year, time.month, time.day, time.hour, time.minute)
            type = rows[i][3]
            result_json += '{"type": "Feature","geometry": {"type": "Point", "coordinates":%s}, "properties": {"id": %s, "time": "%s","type": "%s"}},' % (
                location, id, time, type)
        result_json = result_json[:-1]
        result_json += ']}'
    else:
        result_json = '"NULL"'
    conn.commit()
    cur.close()
    conn.close()
    return result_json


@route('/crime')
def service():
    polygon = request.GET.get('bikeshed', default=None)
    if polygon is not None:
        return pointInPolygon(polygon)


run(host='0.0.0.0', port=7366, debug=True)

#http://127.0.0.1:7366/crime?walkshed={"type":"Polygon","coordinates":[[[-114.09364571378056,51.057144582993836],[-114.09286815708892,51.05359381755474],[-114.09101115708,51.050834058520664],[-114.09075927937053,51.05080998647081],[-114.0870286,51.0516827],[-114.08586777200182,51.04970977429437],[-114.0835059,51.0489783],[-114.08184778623112,51.0498709384076],[-114.081181,51.0536508],[-114.0793914,51.0547065],[-114.077687,51.0557314],[-114.0756248,51.0568823],[-114.0750158,51.0570965],[-114.0736901,51.0573512],[-114.06926177015508,51.055915080229724],[-114.06619893997784,51.05694155563417],[-114.06579011626843,51.0581622658825],[-114.067673398873,51.058916548778726],[-114.07143185670641,51.061423362491404],[-114.07184987616904,51.06168921938163],[-114.0741837,51.0613545],[-114.07794224224338,51.06228401160695],[-114.07918450576179,51.06260346516831],[-114.07993046849634,51.06280359284396],[-114.08066137191179,51.062350982627464],[-114.08244401432806,51.06127600012983],[-114.08582266933304,51.061346817139835],[-114.08616082731021,51.06129711945887],[-114.0888935,51.0575163],[-114.09170271289915,51.05843118482227],[-114.09364571378056,51.057144582993836]]]}
