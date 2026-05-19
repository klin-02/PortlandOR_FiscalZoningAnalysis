import geopandas as gp
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2


def GeoRDDAnalysis(lots_gdf, zoning_gdf):
    import Services.RDDService as rs

    lots_gdf = gp.GeoDataFrame(lots_gdf)
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    zone_tup = __JoinZones__(zoning_gdf)

    highd_zones = zone_tup[0]
    lowd_zones = zone_tup[1]
    lots_tup = __DistFromBorder__(lots_gdf, highd_zones, lowd_zones)

    highd_lots = lots_tup[0]
    lowd_lots = lots_tup[1]

    highd_lots = __CalcTMVPerAcre__(highd_lots)
    lowd_lots = __CalcTMVPerAcre__(lowd_lots)

    highd_lots = __RemoveOutliers__(highd_lots)
    lowd_lots = __RemoveOutliers__(lowd_lots)

    lots_gdf = pd.concat([highd_lots, lowd_lots])

    lots_gdf = gp.GeoDataFrame(lots_gdf)

    '''
    lots_gdf.plot(x="distance to border (mi)", y="total market value/acre", kind="scatter")
    plt.show()
    '''

    rs.Fit(lots_gdf, x_label="distance to border (mi)", y_label="total market value/acre")

'''
Takes in zoning polygons and unions them 
Based on if they are high density or not
Returns tuple of (highd_zones, lowd_polygons)
'''
def __JoinZones__(zoning_gdf) -> tuple:
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    highd_codes = ["RMP", "RM1", "RM2", "RM3", 
                   "RM4", "RX", "CM1", "CM2"
                   "CM3", "CE", "CX", "CR"]
    lowd_codes = ["RF", "R20", "R10", "R7",
                   "R5", "R2.5"]

    highd_zones = zoning_gdf[zoning_gdf["ZONE"].isin(highd_codes)]
    lowd_zones = zoning_gdf[zoning_gdf["ZONE"].isin(lowd_codes)]

    highd_zones = highd_zones[["geometry"]]   
    lowd_zones = lowd_zones[["geometry"]]

    return (highd_zones, lowd_zones)

'''
Calculate distance from Euclidean/non-euclidean Zoning border
Create the continuous running var for the GeoRDD analysis
'''
def __DistFromBorder__(lots_gdf, highd_gdf, lowd_gdf) -> tuple:
    lots_gdf = gp.GeoDataFrame(lots_gdf)
    highd_gdf = gp.GeoDataFrame(highd_gdf)
    lowd_gdf = gp.GeoDataFrame(lowd_gdf)

    lots_gdf = lots_gdf.set_geometry(lots_gdf.centroid)

    highd_lots = lots_gdf.sjoin(highd_gdf)
    lowd_lots = lots_gdf.sjoin(lowd_gdf)

    #convert to shapely polygon for dist calcs
    highd_poly = highd_gdf.union_all()
    lowd_poly = lowd_gdf.union_all()

    #make sure to convert epsg 2913 international ft to miles
    highd_lots["distance to border (mi)"] = highd_lots.distance(lowd_poly) * 0.00018939

    #multiply by -1 to denote control variable (left side of graph)
    lowd_lots["distance to border (mi)"] = (lowd_lots.distance(highd_poly) * 0.00018939) * -1

    return (highd_lots, lowd_lots)

def __CalcTMVPerAcre__(lots_gdf) -> gp.GeoDataFrame:
    lots_gdf = gp.GeoDataFrame(lots_gdf)

    lots_gdf["total market value/acre"] = lots_gdf["TOTALVAL"] / lots_gdf["GIS_ACRES"]
    return lots_gdf

'''
Use Mahanalobis Distance to remove outliers from the data
Apply independently to control/treatment
Outliers in this data are generally just Areal Unit Problems
'''
def __RemoveOutliers__(lots_gdf):
    lots_gdf = gp.GeoDataFrame(lots_gdf)

    #only include x and y var
    data = lots_gdf[["distance to border (mi)", "total market value/acre"]].values

    mean = np.mean(data, axis=0)

    covm =  np.cov(data, rowvar=False)
    inv_covm = np.linalg.inv(covm)

    distances = []
    for row in data:
        distances.append(mahalanobis(row, mean, inv_covm))
    
    threshold = np.sqrt(chi2.ppf(0.975, df=2))
    lots_gdf = lots_gdf[distances < threshold]

    '''
    Q1 = np.percentile(lots_gdf["total market value/acre"], 25)
    Q3 = np.percentile(lots_gdf["total market value/acre"], 75)
    IQR = Q3 - Q1

    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR

    lots_gdf = lots_gdf[lots_gdf["total market value/acre"] < upper]
    lots_gdf = lots_gdf[lots_gdf["total market value/acre"] > lower]
    '''

    return lots_gdf

'''
Calculate some variables that could affect the result
Helps make results more statistically valid/relevant
In this method, I calculate percent pavement area 
and tree canopy cover for 1 km cells across Portland
'''
#def __CalcCovariates__(lots_gdf) -> gp.GeoDataFrame: