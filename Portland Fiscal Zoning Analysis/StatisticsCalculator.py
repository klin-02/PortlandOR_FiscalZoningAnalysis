import geopandas as gp
import pandas as pd
from matplotlib import pyplot as plt
from pandas._libs.lib import NoDefaultDoNotUse

def GeoRDDAnalysis(lots_gdf, zoning_gdf):
    lots_gdf = gp.GeoDataFrame(lots_gdf)
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    tup = __JoinZones__(zoning_gdf)

    non_euclidean_gdf = tup[0]
    euclidean_gdf = tup[1]
    lots_gdf = __DistFromBorder__(lots_gdf, non_euclidean_gdf, euclidean_gdf)


'''
Takes in zoning polygons and unions them 
Based on if they are euclidean or not
Returns tuple of (non_euclidean_polygons, euclidean_polygons)
'''
def __JoinZones__(df1) -> tuple:
    df1 = gp.GeoDataFrame(df1)

    non_euclidean_codes = ["CX", "EX", "RX", "CE", 
                           "CM1", "CM2", "CM3", 
                           "CR", "CI1", "CI2", "IR"]
    euclidean_codes = ["RF", "R20", "R10", "R7", 
                       "R5", "R2.5", "RMP", "IH",
                       "IG1", "IG2", "EG1", "EG2"
                       "RM1", "RM2", "RM3", "RM4",]

    non_euclidean_zones = df1[df1["ZONE"].isin(non_euclidean_codes)]
    euclidean_zones = df1[df1["ZONE"].isin(euclidean_codes)]

    non_euclidean_zones = non_euclidean_zones[["geometry"]]
    non_euclidean_zones = non_euclidean_zones.union_all()
    
    euclidean_zones = euclidean_zones[["geometry"]]
    euclidean_zones = euclidean_zones.union_all()

    non_euclidean_zones.plot()
    plt.show()

    euclidean_zones.plot()
    plt.show()

    return (non_euclidean_zones, euclidean_zones)

'''
Calculate distance from Euclidean/non-euclidean Zoning border
Create the continous running var for the GeoRDD analysis
'''
def __DistFromBorder__(lots_gdf, non_euclidean_gdf, euclidean_gdf) -> gp.GeoDataFrame:
    lots_gdf = gp.GeoDataFrame(lots_gdf)
    non_euclidean_gdf = gp.GeoDataFrame(non_euclidean_gdf)
    euclidean_gdf = gp.GeoDataFrame(euclidean_gdf)

    lots_gdf = lots_gdf.set_geometry(lots_gdf.centroid)

    non_euclidean_lots = lots_gdf.sjoin(non_euclidean_gdf)
    euclidean_lots = lots_gdf.sjoin(euclidean_gdf)

    #make sure to convert epsg 2913 international ft to miles
    non_euclidean_lots["distance to border (mi)"] = non_euclidean_lots.distance(non_euclidean_gdf) / 0.00018939

    #multiply by -1 to denote control variable (left side of graph)
    euclidean_lots["distance to border (mi)"] = (euclidean_lots.distance(euclidean_gdf) / 0.00018939) * -1

    lots_gdf = pd.concat([non_euclidean_lots, euclidean_lots])

    return gp.GeoDataFrame(lots_gdf, geometry="geometry")
