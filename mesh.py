# -*- coding: utf-8 -*-

import pandas as pd
import geopandas as gpd

from shapely import box

### GET DATA FROM DB
def query_to_df(query, engine):
    return pd.read_sql(query, engine)
    
def query_to_gdf(query, engine, geom_col="geom"):
    return gpd.GeoDataFrame.from_postgis(query, engine, geom_col="geom")


### CREATION OF TILES EXTENTS

def extents_to_shp(extents, path):
    '''
    Create a shapefile from a list of extent tuples (W, S, E, N)

    Parameters
    ----------
    extents : list of tuples
        (west, south, east, north)
    path : string
        path and name of the shapefile
    '''
    # Create extent polygons
    polygons = []
    for extent in extents:
        w, s, e, n = extent
        poly = box(w, s, e, n)
        polygons.append(poly)
    # Add them to the geoserie
    s = gpd.GeoSeries(polygons, crs="EPSG:3857")
    # Save to shapefile
    s.to_file(path)
    

def get_extents_from_sets(engine, zoom_level, basemap):
    # Create dataframe from sets table in db (where are the maps information)
    query = "SELECT * FROM deepmapdraw.sets WHERE zoom = {} AND basemap = '{}'".format(zoom_level, basemap)
    sets_df = query_to_df(query, engine)
    
    # Create an index column to iterate on retrieved sets without problem
    sets_df = sets_df.reset_index() 
    
    # Retrieve map extents from sets (format W,S,E,N)
    map_extents = []
    for index, row in sets_df.iterrows():
        map_extent = (row['x_min'], row['y_max'], row['x_max'], row['y_min']) ### WARNING XMIN ET XMAX ECHANGES DANS LA BDD
        map_extents.append(map_extent)
    
    return map_extents
        
    
def get_anchors_gdf_from_db(engine, zoom_level, basemap):
    # Create dataframe from sets table in db (where are the maps information)
    query = "SELECT * FROM deepmapdraw.anchors WHERE zoom = {} AND basemap = '{}'".format(zoom_level, basemap)
    return query_to_gdf(query, engine)

    

def create_mesh_extents(canvas_extent, overlapse, safety, size, srs, zoom_level, verbose=False):
    # take one set extent from mapdraw and cut tiles extent inside it 
    srs[zoom_level]
    if verbose: print("Construction du mesh...")
    if verbose: print("Marge de sécurité: ", safety)
    
    # west, south, east, north of the canvas
    wc, sc, ec, nc = canvas_extent
    
    # Calcul de la taille de la zone de travail en enlevant la marge de sécurité
    canvas_width = abs(ec - wc) * (1 - (safety * 2))
    canvas_heigth = abs(nc - sc) * (1 - (safety * 2))
    if verbose: print("Largeur de la zone de travail: ", canvas_width)
    if verbose: print("Hauteur de la zone de travail: ", canvas_heigth)
    
    # Calcule de la taille IRL d'une maille, selon le zoom désiré
    zoom = srs[zoom_level]
    tile_width = size[0] * zoom
    tile_heigth = size[1] * zoom
    
    # Calcul du nombre de maille qu'on peut mettre en abscisses et en ordonnées, en prenant en compte l'overlapse
    nb_tiles_width = int((canvas_width - tile_width) / (tile_width * (1 - overlapse))) + 1
    nb_tiles_heigth = int((canvas_heigth - tile_heigth) / (tile_heigth * (1 - overlapse))) + 1
    if verbose: print("Nombre de mailles en largeur: ", nb_tiles_width)
    if verbose: print("Nombre de mailles en hauteur: ", nb_tiles_heigth)
    
    # Creation des extents de chaque maille
    extents = []
    
    # On parcourt la map de gauche à droite puis de haut en bas
    for y in range(nb_tiles_heigth):
        for x in range(nb_tiles_width):
            w = wc + (safety * canvas_width) + x * tile_width * (1 - overlapse)
            n = nc - (safety * canvas_heigth) - y * tile_heigth * (1 - overlapse)
            e = w + tile_width
            s = n - tile_heigth
            extent = [w, s, e, n]
            extents.append(extent)
     
    ### old tiles de bas en haut puis de gauche à droite
    # for x in range(nb_tiles_width):
    #     for y in range(nb_tiles_heigth):
    #         w = wc + (safety * canvas_width) + x * tile_width * (1 - overlapse)
    #         s = sc + (safety * canvas_heigth) + y * tile_heigth * (1 - overlapse)
    #         e = w + tile_width
    #         n = s + tile_heigth
    #         extent = [w, s, e, n]
    #         extents.append(extent)        
            
    
    if verbose: print("mesh terminé.")
    if verbose: print(nb_tiles_width * nb_tiles_heigth, "tuiles")
    return extents




################## TESTS ##################
if __name__ == "__main__":
    
    
    ##### IMPORT
    # engine for postgis connexion:
    import psycopg2 # needed even if "unused"
    from sqlalchemy import create_engine
    
    import json
    
    ##### PARAMS
    
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
    ZOOM_LEVEL = 12
    ZOOM = SRS[ZOOM_LEVEL]
    BASEMAP = 'pign'
    
    # Connexion to db with sqlalchemy
    ENGINE_PARAM = "postgresql://postgres:Postgres32167!@localhost:5432/lizexp"
    engine = create_engine(ENGINE_PARAM)
    
    # Mesh parameters (tiles creation)
    OVERLAPSE = 0.1 # between 0 and 0.99
    SAFETY = 0
    TILE_SIZE = (256, 256)
    
    # Paths
    SET_EXTENTS_SHP_PATH = 'tests/set_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.shp'
    TILE_EXTENTS_SHP_PATH = 'tests/tile_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.shp'
    TILE_EXTENTS_JSON_PATH = 'tests/tile_extents_' + BASEMAP + '_z' + str(ZOOM_LEVEL) + '.json'
    
    
    
    ##### RUN 
    
    print("Retrieve set extents from db")
    set_extents = get_extents_from_sets(engine, ZOOM_LEVEL, BASEMAP)
    print(len(set_extents), "set extents loaded")
    
    print("Create set extents shapefile in tests folder")
    extents_to_shp(set_extents, SET_EXTENTS_SHP_PATH)
    
    print("Create tile extents from set extents")
    tile_extents = []
    for set_extent in set_extents:
        mesh = create_mesh_extents(set_extent, OVERLAPSE, SAFETY, TILE_SIZE, SRS, ZOOM_LEVEL, verbose=False)
        for tile_extent in mesh: tile_extents.append(tile_extent)
    print(len(tile_extents), "tile extents created")
    
    print("Create tile extents shapefile in tests folder")
    extents_to_shp(tile_extents, TILE_EXTENTS_SHP_PATH)
    
    print("Create tile extents json in tests folder")
    with open(TILE_EXTENTS_JSON_PATH, 'w') as f:
        json.dump(tile_extents, f, indent=2) # indent=2 is not needed but makes the file human-readable
    
    print("Load json file")
    with open(TILE_EXTENTS_JSON_PATH, 'r') as f:
        tile_extents = json.load(f)
    print(len(tile_extents), "tile extents loaded")
   
    
    