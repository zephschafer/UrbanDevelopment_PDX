import requests
import fiona
import geopandas as gpd
import pandas as pd
from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import *
from tqdm import tqdm_notebook as tqdm
import psycopg2
import os

# Define Handler for Multipolygons
# Source <https://gist.github.com/mhweber/cf36bb4e09df9deee5eb54dc6be74d26>
def explode(indata):
    indf = indata
    outdf = gpd.GeoDataFrame(columns=indf.columns)
    for idx, row in indf.iterrows():
        if type(row.geometry) == Polygon:
            outdf = outdf.append(row,ignore_index=True)
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row]*recs,ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom,'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf,ignore_index=True)
    return outdf

def scrape(api,tablename):
    # Read GeoJSON
    b = bytes(requests.get(api).content)
    with fiona.BytesCollection(b) as f:
        crs = f.crs
        gdf = gpd.GeoDataFrame.from_features(f, crs=crs)
    # Prep GDF for Mapping
    gdf['multipoly'] = (gdf['geometry'].geom_type=='MultiPolygon').astype(int)
    if gdf['multipoly'].sum() > 0:
        gdf = explode(gdf)
    gdf.columns = [x.lower() for x in gdf.columns]
    # Define Postgres Engine
    engine = create_engine("postgresql://zephschafer@localhost/tempspatial")
    srid = int(f.crs['init'][-4:])
    # Prep GDF for Postgres
    gdf['geom'] = gdf['geometry']\
                .apply(lambda x: WKTElement(x.wkt, srid = srid))
    gdf.drop(columns=['geometry'], inplace=True)
    # Export to Postgres
    if_exists = 'append'
    try:
        gdf.to_sql(tablename, engine, if_exists = if_exists, index = False,\
                         dtype={'geom': Geometry('Polygon'\
                                                 , srid = srid)})
    except:
        connection = engine.connect()
        connection.execute("ALTER TABLE " + tablename \
                                 + " ALTER COLUMN geom TYPE geometry(Geometry,4326);")
        gdf.to_sql(tablename, engine, if_exists = if_exists, index=False,\
                   dtype={'geom': Geometry('Polygon'\
                                           , srid = srid)})
        connection.close()
    return gdf
