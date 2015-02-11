import psycopg2
from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024

#This function returns the crime happened within the given polygon
def pointInCircle(start_point, radius):
    import config

    connection_string = config.conf()

    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    radius = float(radius) * 1000  #in meters
    start_point = start_point.split(',')
    start_point = "SRID=4326;POINT(%s %s)" % (start_point[1], start_point[0])
    selectQuery = "SELECT id, ST_AsText(crime_location), crime_time, crime_type " \
                  "FROM cps_crime_data.crime_data " \
                  "WHERE ST_DWithin(ST_GeogFromText(%s), geography(crime_location), %s);"
    parameters = [start_point, radius]
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
    start_point = request.GET.get('start_point', default=None)
    radius = request.GET.get('radius', default=None)
    if start_point and radius is not None:
        return pointInCircle(start_point, radius)


run(host='0.0.0.0', port=6366, debug=True)

#http://127.0.0.1:6366/crime?start_point=51.05723044585338,-114.11717891693115&radius=1.60934
