# -*- coding: utf-8 -*-


from mesh import create_mesh_extents, get_extents_from_sets, extents_to_shp, get_anchors_gdf_from_db
#from params import *

import json

import os

import pandas as pd
import geopandas as gpd

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


### CONNEXION TO SERVER FLUX with owslib
WMS_URL = 'https://wxs.ign.fr/essentiels/geoportail/r/wms'
WMS_LAYER = 'GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2'
TIMEOUT = 300

# Mesh parameters (tiles creation)
TILE_SIZE = (256, 256)
OVERLAPSE = 0 # between 0 and 0.99
SAFETY = 0



### PATHS 


BENCHMARK_PATH = "benchmark/pign_z14/"
MAP_NAME = "urban2"

JSON_PATH = BENCHMARK_PATH + MAP_NAME + "/" + MAP_NAME + ".geojson"
OUTPUT_IMG_PATH = BENCHMARK_PATH + MAP_NAME + "/tiles/"


def main():
    ### CREATE TILES FROM EXTENT
    
    # get extent
    map_extent = get_map_extent(JSON_PATH)
    
    # create tile extents
    tile_extents = create_mesh_extents(map_extent, OVERLAPSE, SAFETY, TILE_SIZE, SRS, ZOOM_LEVEL, verbose=False)

    # Create and save tile images in tiles folder
    # 1er chiffre = num_ligne, 2e chiffre = num_colonne
    
    
    ### IMAGES AND MASKS CREATION
    
     
    # Connexion to WMS server (image creation)
    print("Connexion to wms server...")
    wms = WebMapService(WMS_URL, timeout=TIMEOUT)
    if not wms: return print("Connexion failed, process aborted.")
    else: print("Connected to " + WMS_URL) 
    
    
    # Loop
    i = 0 # numéro de l'image
    l = 1 # ligne de la tuile dans la map
    c = 1 # colonne de la tuile dans la map
    w1 = 0 # coord west de la dernière tuile créée
    
    for tile_extent in tile_extents:
        i += 1
        w, s, e, n = tile_extent
        
        # si la nouvelle coord west est inférieure ca veut dire qu'on arrive au bout de la ligne et qu'on passe a la ligne du dessous
        if (i > 1 and w <= w1):
            l += 1 
            c = 1
        
        tile_name = str(l) + str(c)
        # On incremente la colonne
        c += 1
        # On met en mémoire la coord west pour la prochaine itération
        w1 = w
        
        
        print("Creation of image and mask number ", i, " out of ", len(tile_extents))
        
        img = wms.getmap(   layers = [WMS_LAYER],
                            srs = 'EPSG:3857', # Pseudo Mercator
                            bbox = tile_extent, # Enveloppe West South East North # Attention il faut respecter les proportions de size
                            size = TILE_SIZE, 
                            format='image/png',
                            timeout=TIMEOUT
                            )
        path = OUTPUT_IMG_PATH + '/' + tile_name + '.png'
        out = open(path, 'wb')
        out.write(img.read())
        out.close()

    

def get_map_extent(json_path):
    # Extent is only in the json if at least one layer has been drawn
    # In the json, "extent" is composed of two lists of 2 coordinates: west north corner and east south corner
    # We convert it in a tuple (W, S, E, N)
    with open(json_path, 'r') as f:
        dic = json.load(f)
        extent_corners = dic["features"][0]["properties"]["extent"]
        w, n, e, s = extent_corners[0][0], extent_corners[0][1], extent_corners[1][0], extent_corners[1][1]
        extent_tuple = (w, s, e, n)
        return extent_tuple
        
    
def get_zoom_level(json_path):
    with open(json_path, 'r') as f:
        dic = json.load(f)
        return dic["features"][0]["zoom"]
    

def recompose_maps():
    # parse a folder with tiles in it, and create corresponding images with concatenation
    pass


