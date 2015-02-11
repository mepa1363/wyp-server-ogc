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


def management(start_point, biking_time_period, distance_decay_function):
    geoserver_wps_url = 'http://127.0.0.1:8080/geoserver/ows?service=wps&version=1.0.0&request=execute&identifier='

    otp_dataInputs = 'StartPoint=%s;BikingPeriod=%s;BikeshedOutput=SHED' % (
        start_point, biking_time_period)
    otp_url = geoserver_wps_url + 'gs:Bikeshed_Centralized&datainputs=' + otp_dataInputs

    bikeshed = urllib2.urlopen(otp_url).read()
    bikeshed = parseXML(bikeshed, 'wps:LiteralData')

    if bikeshed != '':
        bikeshed_json = json.loads(bikeshed)
        if bikeshed_json['type'] == "Polygon":

            print "bikeshed: %s" % (bikeshed,)

            #invoke poi service
            poi_wps_url = 'http://127.0.0.1:8080/geoserver/ows'
            poi_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>gs:POI_Bike_Centralized</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>Bikeshed</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
  <wps:ResponseForm>
    <wps:RawDataOutput>
      <ows:Identifier>POIResult</ows:Identifier>
    </wps:RawDataOutput>
  </wps:ResponseForm>
</wps:Execute>""" % (bikeshed,)
            poi_wps_request = urllib2.Request(url=poi_wps_url, data=poi_xml_data,
                                              headers={'Content-Type': 'application/xml'})
            poi_data = urllib2.urlopen(poi_wps_request).read()

            print "poi data: %s" % (poi_data,)

            #invoke crime wps
            crime_wps_url = 'http://127.0.0.1:8080/geoserver/ows'
            crime_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>gs:Crime_Bike_Centralized</ows:Identifier>
  <wps:DataInputs>
    <wps:Input>
      <ows:Identifier>Bikeshed</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
  </wps:DataInputs>
  <wps:ResponseForm>
    <wps:RawDataOutput>
      <ows:Identifier>CrimeResult</ows:Identifier>
    </wps:RawDataOutput>
  </wps:ResponseForm>
</wps:Execute>""" % (bikeshed,)
            crime_wps_request = urllib2.Request(url=crime_wps_url, data=crime_xml_data,
                                                headers={'Content-Type': 'application/xml'})
            crime_data = urllib2.urlopen(crime_wps_request).read()

            print "crime data: %s" % (crime_data,)

            #retrieve aggregated data (final result)
            #As the volume of input data is too large for HTTP GET request, HTTP POST is used to invoke GeoServer Aggregation WPS

            aggregation_wps_url = 'http://127.0.0.1:8080/geoserver/ows'
            aggregation_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<wps:Execute version="1.0.0" service="WPS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.opengis.net/wps/1.0.0" xmlns:wfs="http://www.opengis.net/wfs" xmlns:wps="http://www.opengis.net/wps/1.0.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:wcs="http://www.opengis.net/wcs/1.1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xsi:schemaLocation="http://www.opengis.net/wps/1.0.0 http://schemas.opengis.net/wps/1.0.0/wpsAll.xsd">
  <ows:Identifier>gs:Aggregation_Bike_Centralized</ows:Identifier>
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
      <ows:Identifier>Bikeshed</ows:Identifier>
      <wps:Data>
        <wps:LiteralData>%s</wps:LiteralData>
      </wps:Data>
    </wps:Input>
    <wps:Input>
      <ows:Identifier>BikingTimePeriod</ows:Identifier>
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
</wps:Execute>""" % (poi_data, crime_data, start_point, bikeshed, biking_time_period, distance_decay_function)
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
    result = '{"walkshed": %s, "poi": %s, "crime": %s}' % (aggregation_data, poi_data, crime_data)

    return result


@route('/management')
def service():
    start_point = request.GET.get('start_point', default=None)
    biking_time_period = request.GET.get('biking_time_period', default=None)
    distance_decay_function = request.GET.get('distance_decay_function', default=None)

    if start_point and biking_time_period is not None:
        return management(start_point, biking_time_period, distance_decay_function)


run(host='0.0.0.0', port=7363, debug=True)
