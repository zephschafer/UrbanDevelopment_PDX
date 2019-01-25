import requests
import fiona
import geopandas as gpd
import pandas as pd
from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import *
from tqdm import tqdm_notebook as tqdm
import psycopg2
import os
from scraper_tools.py import scrape, explode

# Define Scrape Parameters
querysize = str(100)
offsetmax = raw_input("Extent of requests (suggestion: 2000):   ")
offsets = [str(x) for x in range(1, offsetmax, int(querysize))]

# Execute Scrape Using API's pagination
for queryoffset in tqdm(offsets):
    buildingsAPI = 'https://www.portlandmaps.com/arcgis/rest/services/Public/COP_OpenData_Property/MapServer/184/query?where=1%3D1&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset='\
                    + queryoffset + '&resultRecordCount='\
                    + querysize + '&queryByDistance=&returnExtentsOnly=false&datumTransformation=&parameterValues=&rangeValues=&f=geojson'
    api = buildingsAPI
    exportname = "buildings"
    tablename = exportname
    scrape(api)

# Sample Query for Check
with engine.connect() as conn, conn.begin():
    sql = """SELECT COUNT(geom) FROM """ + tablename + """ LIMIT 1;"""
    results = conn.execute(sql)
    for result in results:
        print "Seeded DB has " + str(result) " rows."
    conn.close()

# Export the Query for Mapbox
con = psycopg2.connect(database='tempspatial', user='zephschafer')
query = 'SELECT * FROM ' + tablename + ';'
df = gpd.GeoDataFrame.from_postgis(query, con, geom_col='geom' )
try:
    os.remove('data/' + exportname + '.geojson')
    df.to_file('data/' + exportname + '.geojson', driver =  'GeoJSON')
except:
    df.to_file('data/' + exportname + '.geojson', driver =  'GeoJSON')
