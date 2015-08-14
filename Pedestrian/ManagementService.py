import json
import urllib2
from xml.dom.minidom import parseString

from bottle import route, run, request
import bottle


bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024


def parseXML(string_xml, element):
    xml_dom = parseString(string_xml)
    node_list = xml_dom.getElementsByTagName(element)[0].childNodes
    result = ''
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            result = node.data
    return result


def management(start_point, walking_time_period, walking_speed, distance_decay_function):
    geoserver_wps_url = 'http://127.0.0.1:8080/geoserver/ows?service=wps&version=1.0.0&request=execute&identifier='

    otp_dataInputs = 'StartPoint=%s;WalkingPeriod=%s;WalkingSpeed=%s;WalkshedOutput=SHED' % (
        start_point, walking_time_period, walking_speed)
    otp_url = geoserver_wps_url + 'gs:Walkshed_Pedestrian_Centralized&datainputs=' + otp_dataInputs

    walkshed = urllib2.urlopen(otp_url).read()
    walkshed = parseXML(walkshed, 'wps:LiteralData')

    if walkshed != '':
        walkshed_json = json.loads(walkshed)
        if walkshed_json['type'] == "Polygon":
            print "walkshed: %s" % (walkshed,)

            #invoke poi service
            #bikeshed = urllib2.quote(bikeshed)

            poi_dataInputs = 'Walkshed=%s' % (walkshed,)
            poi_wps_url = geoserver_wps_url + 'gs:POI_Pedestrian_Centralized&datainputs=' + poi_dataInputs

            #retrieve POI data
            poi_data = urllib2.urlopen(poi_wps_url).read()

            #extract POI data from XML response
            poi_data = parseXML(poi_data, 'wps:LiteralData')

            print "poi data: %s" % (poi_data,)

            crime_dataInputs = 'Walkshed=%s' % (walkshed,)
            crime_wps_url = geoserver_wps_url + 'gs:Crime_Pedestrian_Centralized&datainputs=' + crime_dataInputs

            #retrieve crime data
            crime_data = urllib2.urlopen(crime_wps_url).read()

            #extract crime data from XML response
            crime_data = parseXML(crime_data, 'wps:LiteralData')

            print "crime data: %s" % (crime_data,)

            #retrieve aggregated data (final result)
            #As the volume of input data is too large for HTTP GET request, HTTP POST is used to invoke GeoServer Aggregation WPS

            aggregation_wps_url = 'http://127.0.0.1:8080/geoserver/ows'
            aggregation_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>gs:Aggregation_Pedestrian_Centralized</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>POI</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>Crime</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>StartPoint</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>Walkshed</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>WalkingTimePeriod</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>DistanceDecayFunction</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
  <wps:ResponseForm>
    <wps:RawDataOutput>
      <ows:Identifier>AggregationResult</ows:Identifier>
    </wps:RawDataOutput>
  </wps:ResponseForm>
</wps:Execute>""" % (poi_data, crime_data, start_point, walkshed, walking_time_period, distance_decay_function)
            aggregation_wps_request = urllib2.Request(url=aggregation_wps_url, data=aggregation_xml_data,
                                                      headers={'Content-Type': 'application/xml'})

            aggregation_data = urllib2.urlopen(aggregation_wps_request).read()

            print "aggregation data: %s" % (aggregation_data,)
        else:
            aggregation_data = '"NULL"'
            poi_data = '"NULL"'
            crime_data = '"NULL"'
    else:
        aggregation_data = '"NULL"'
        poi_data = '"NULL"'
        crime_data = '"NULL"'
        #return aggregation_data
    result = '{"walkshed": %s, "poi": %s}' % (aggregation_data, poi_data)
    return result


@route('/management')
def service():
    start_point = request.GET.get('start_point', default=None)
    walking_time_period = request.GET.get('walking_time_period', default=None)
    walking_speed = request.GET.get('walking_speed', default=None)
    distance_decay_function = request.GET.get('distance_decay_function', default=None)

    if start_point and walking_time_period and walking_speed and distance_decay_function is not None:
        return management(start_point, walking_time_period, walking_speed, distance_decay_function)


run(host='0.0.0.0', port=8363, debug=True)

#http://127.0.0.1:8363/management?start_point=51.05723044585338,-114.11717891693115&walking_time_period=15&walking_speed=1.38&distance_decay_function=false
