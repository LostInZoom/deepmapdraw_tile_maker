# -*- coding: utf-8 -*-

from shapely import box, intersection, affinity
import geopandas as gpd
from PIL import Image, ImageDraw


### DEF

def create_mask(extent, polygons, zoom, img_size, img_path=False, verbose=False):
    '''
    Create an image from an extent and draw black polygons on it 

    Parameters
    ----------
    extent : tuple (west, south, east, north)
        
    polygons : list of polygons (geometry column in postgis)
        The polygons we want to draw on our mask
        
    zoom : float
        Number of real life meters per pixel
        
    img_size : tuple of int (x, y) in pixel
        
    img_path : string, optional
        If specified, create a file to save the mask. The default is False.
        
    verbose : bool, optional
        Print information in prompt. The default is False.

    Returns
    -------
    mask : PIL image
        Return the created mask

    '''

    # Creation of an rectangle extent polygon
    w, s, e, n = extent
    tilebox = box(w, s, e, n)
    
    
    # Intersection between the extent polygon and the polygons we want to draw
    if verbose: print("Intersection between extent and polygons...")
    
    intersections = []
    for polygon in polygons:
      intersect = intersection(tilebox, polygon)
      if not intersect.is_empty: intersections.append(intersect)
    
    if verbose: print("Number of polygons created through intersection: ", len(intersections))
    
    
    # Creation of an empty mask (blank image)
    mask = Image.new(mode='LA', size=img_size, color='white')
    
    if intersections:
        
        # simplify multipolygons
        p = []
        for geometry in intersections:
            if geometry.geom_type == 'Polygon': p.append(geometry)
            if geometry.geom_type == 'MultiPolygon':
                for poly in geometry.geoms: p.append(poly)
        
        intersections = p
        
        
        # Create one image per polygon and fuse them later (mandatory to take into account overlapping polygons with at least one hole)
        if verbose: print("Drawing polygon images...")
        images = []
        for polygon in intersections:
            
            # creation of an image with PIL
            img = Image.new(mode='LA', size=img_size, color=(0, 0)) # LA --> color = (black/white, alpha (transparency))
            draw = ImageDraw.Draw(img)
            
            # Conversion des points du polygone depuis son échelle et son emprise. à une nouvelle échelle et coordonnées d'origine 256*256
            poly_to_draw = affinity.translate(polygon, xoff=-w, yoff=-s)
            poly_to_draw = affinity.scale(poly_to_draw,
                                                 xfact=1/zoom,
                                                 yfact=1/zoom,
                                                 origin=(0, 0))
            
            # Draw exterior polygon in black
            coords_list = poly_to_draw.exterior.coords
            draw.polygon(coords_list, fill="black") # black = (0, 255)
            
            # Draw interior polygons (holes) in transparent
            int_polys = poly_to_draw.interiors
            for poly in int_polys:
                coords_list = poly.coords
                draw.polygon(coords_list, fill=(0, 0))
                
            images.append(img)
                
        if verbose: print("Fusing polygon images")
        
        # Fuse images with mask
        for img in images:
            mask.paste(img, mask=img)
        
        # flip mask because PIL 'y' are inverted
        mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
    
    
    if verbose: print("Mask created")

    # Save image if needed                  
    if img_path: 
        mask.save(img_path)
        if verbose: print("Mask saved as " + img_path)
    
    return mask
    



################## TESTS ##################
if __name__ == "main":
    
    ### PARAMS
    ZOOM_RES_3857 = {          
        0: 156543.0339280410, 1: 78271.5169640205, 2: 39135.7584820102, 
        3: 19567.8792410051, 4: 9783.9396205026, 5: 4891.9698102513, 	
        6: 2445.9849051256, 7: 1222.9924525628, 8: 611.4962262814, 
        9: 305.7481131407, 10: 152.8740565704, 11: 76.4370282852, 	
        12: 38.2185141426, 13: 19.1092570713, 14: 9.5546285356, 	
        15: 4.7773142678, 16: 2.3886571339, 17: 1.1943285670, 
        18: 0.5971642835, 19: 0.2985821417, 20: 0.1492910709, 21: 0.0746455354 
    }

    ZOOM_LEVEL = 12
    ZOOM = ZOOM_RES_3857[ZOOM_LEVEL]

    # shapefile_test:
    EXTENT = (144000, 6115000, 154000, 6125000)

    # import data as gdf from shp (or from db)
    gdf = gpd.read_file("tests create masks/test.shp")
    POLYGONS = gdf.geometry.to_crs(3857)

    IMG_SIZE = (256, 256)

    IMG_PATH = 'test.png'
    
    ### EXECUTE
    create_mask(EXTENT, POLYGONS, ZOOM, IMG_SIZE, IMG_PATH)