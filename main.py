# -*- coding: utf-8 -*-



#import images_from_wms as my_lib
from create_masks import create_mask
from mesh import create_mesh_extents, get_extents_from_sets, extents_to_shp, get_anchors_gdf_from_db
#from params import *

import json

import os

import pandas as pd
import geopandas as gpd

# engine for postgis connexion:
import psycopg2 # needed even if "unused"
from sqlalchemy import create_engine

# connexion to wms server
from owslib.wms import WebMapService


### PARAMETERS

# taken from https://geoservices.ign.fr/documentation/geoservices/wmts.html
# m/px for each zoom level (m/px=resolution)
# default projection for geoportail is EPSG:3857
ZOOM_RES_3857 = {          
    0: 156543.0339280410, 1: 78271.5169640205, 2: 39135.7584820102, 
    3: 19567.8792410051, 4: 9783.9396205026, 5: 4891.9698102513, 	
    6: 2445.9849051256, 7: 1222.9924525628, 8: 611.4962262814, 
    9: 305.7481131407, 10: 152.8740565704, 11: 76.4370282852, 	
    12: 38.2185141426, 13: 19.1092570713, 14: 9.5546285356, 	
    15: 4.7773142678, 16: 2.3886571339, 17: 1.1943285670, 
    18: 0.5971642835, 19: 0.2985821417, 20: 0.1492910709, 21: 0.0746455354 
}

# Database parameters
SRS = ZOOM_RES_3857
ZOOM_LEVEL = 14
ZOOM = SRS[ZOOM_LEVEL]
BASEMAP = 'pign'

# Connexion to db with sqlalchemy
ENGINE_PARAM = "postgresql://postgres:Postgres32167!@localhost:5432/lizexp"
ENGINE = create_engine(ENGINE_PARAM)

### CONNEXION TO SERVER FLUX with owslib
WMS_URL = 'https://wxs.ign.fr/essentiels/geoportail/r/wms'
WMS_LAYER = 'GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2'
TIMEOUT = 300

# Mesh parameters (tiles creation)
TILE_SIZE = (512, 512)
OVERLAPSE = 0.7 # between 0 and 0.99
SAFETY = 0

EMPTY_MASKS = False


### PATHS 

PROJECTS_FOLDER = 'projects/'

# (No need to change following paths)

#INPUT_MASK_PATH = 'anchors_pign_z12.shp' # automatic

#PROJECT_PATH = PROJECTS_FOLDER + BASEMAP + '_z' + str(ZOOM_LEVEL) + '_s' + str(TILE_SIZE[0]) + '_ol' + str(int(OVERLAPSE*100)) + '/'
PROJECT_PATH = PROJECTS_FOLDER + 'pign_z14_s512_ol70_noempty/'

# Extents
ANCHORS_SHP_PATH = PROJECT_PATH + 'shp/anchors_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.shp'
SET_EXTENTS_SHP_PATH = PROJECT_PATH + 'shp/set_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.shp'
TILE_EXTENTS_SHP_PATH = PROJECT_PATH + 'shp/tile_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.shp'
TILE_EXTENTS_JSON_PATH = PROJECT_PATH + 'tile_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.json'
# Outputs
OUTPUT_IMG_PATH =  PROJECT_PATH +'images'
OUTPUT_TARGET_PATH =  PROJECT_PATH +'targets'



def main():
    
    # Create project folders if it does not exist --> write a function
    # project folder, shp folder
    
    
    
    ### EXTENTS
    
    print("Retrieve set extents from db")
    set_extents = get_extents_from_sets(ENGINE, ZOOM_LEVEL, BASEMAP)
    print(len(set_extents), "set extents loaded")
    
    # Optional
    print("Create set extents shapefile")
    extents_to_shp(set_extents, SET_EXTENTS_SHP_PATH)
    
    print("Create tile extents from set extents")
    tile_extents = []
    for set_extent in set_extents:
        mesh = create_mesh_extents(set_extent, OVERLAPSE, SAFETY, TILE_SIZE, SRS, ZOOM_LEVEL, verbose=False)
        for tile_extent in mesh: tile_extents.append(tile_extent)
    print(len(tile_extents), "tile extents created")
    
    # Optional
    print("Create tile extents shapefile")
    extents_to_shp(tile_extents, TILE_EXTENTS_SHP_PATH)
    
    # Need to do it only once
    print("Create tile extents json in tests folder")
    with open(TILE_EXTENTS_JSON_PATH, 'w') as f:
        json.dump(tile_extents, f, indent=2) # indent=2 is not needed but makes the file human-readable
        
    
    # load extents
    print("Loading extents...")
    with open(TILE_EXTENTS_JSON_PATH, 'r') as f:
        tile_extents = json.load(f)
    print(len(tile_extents), " extents loaded")
        
    
    
    ### LOAD ANCHORS AND SIMPLIFY MULTIPOLYGONS
    
    # Load anchors polygons (and multipolygons) from db
    print("Load anchors from db")
    anchors_gdf = get_anchors_gdf_from_db(ENGINE, ZOOM_LEVEL, BASEMAP)
    
    # Create anchors shapefile (optional)
    print("Create anchors shapefile")
    anchors_gdf.to_file(ANCHORS_SHP_PATH)
    
    # Load anchors as gdf from shp (or from db)
    print("Loading polygons from shapefile")
    anchors_gdf = gpd.read_file(ANCHORS_SHP_PATH)
    geometries = anchors_gdf.geometry.to_crs(3857)
    
    # Multipolygons to polygons
    polygons = []
    for geometry in geometries:
        if geometry.geom_type == 'Polygon': polygons.append(geometry)
        if geometry.geom_type == 'MultiPolygon':
            for poly in geometry.geoms: polygons.append(poly)    
    print(len(polygons), "polygons loaded")
    
    
    
    ### IMAGES AND MASKS CREATION
    
     
    # Connexion to WMS server (image creation)
    print("Connexion to wms server...")
    wms = WebMapService(WMS_URL, timeout=TIMEOUT)
    if not wms: return print("Connexion failed, process aborted.")
    else: print("Connected to " + WMS_URL) 
    
    
    # Loop
    i = 0
    for tile_extent in tile_extents:
        i += 1
        
        print("Creation of image and mask number ", i, " out of ", len(tile_extents))
        
        ### Create mask
        path = OUTPUT_TARGET_PATH + '/' + str(i) + '_mask.png'
        mask = create_mask(tile_extent, polygons, ZOOM, TILE_SIZE, img_path=path, verbose=False, empty=EMPTY_MASKS)
        
        # if mask is False it means it wasn't created, thus we don't create the corresponding image
        if not mask : continue
        
        ### Create image
        img = wms.getmap(   layers = [WMS_LAYER],
                            srs = 'EPSG:3857', # Pseudo Mercator
                            bbox = tile_extent, # Enveloppe West South East North # Attention il faut respecter les proportions de size
                            size = TILE_SIZE, 
                            format='image/png',
                            timeout=TIMEOUT
                            )
        path = OUTPUT_IMG_PATH + '/' + str(i) + '.png'
        out = open(path, 'wb')
        out.write(img.read())
        out.close()
        
    return print("Job is done")
