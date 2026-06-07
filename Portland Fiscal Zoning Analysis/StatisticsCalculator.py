import geopandas as gp
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2


def GeoRDDAnalysis(highways_gdf, redlining_gdf, lots_gdf, zoning_gdf):
    import Services.RDDService as rs

    highways_gdf = gp.GeoDataFrame(highways_gdf)
    redlining_gdf = gp.GeoDataFrame(redlining_gdf)
    lots_gdf = gp.GeoDataFrame(lots_gdf)
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    zone_tup = __JoinZones__(zoning_gdf)

    highd_zones = zone_tup[0]
    lowd_zones = zone_tup[1]
    lots_tup = __DistFromBorder__(lots_gdf, highd_zones, lowd_zones)

    highd_lots = lots_tup[0]
    lowd_lots = lots_tup[1]

    highd_lots = __IndependentProcessor__(highd_lots)
    lowd_lots = __IndependentProcessor__(lowd_lots)

    lots_gdf = pd.concat([highd_lots, lowd_lots])
    lots_gdf = lots_gdf.drop(["index_right"], axis=1)

    lots_gdf = __CalcPlacebos__(lots_gdf, highways_gdf, redlining_gdf)

    lots_gdf = gp.GeoDataFrame(lots_gdf)

    #actual
    rs.Fit(lots_gdf, x_label="distance to border (mi)", y_label="total value/acre")

    #covars
    rs.Fit(lots_gdf, x_label="distance to border (mi)", y_label="YEARBUILT")

    #placebos
    rs.Fit(lots_gdf, x_label="distance to border (mi)", y_label="distance to redlined border (mi)")
    rs.Fit(lots_gdf, x_label="distance to border (mi)", y_label="distance to highway (mi)")

def __IndependentProcessor__(gdf) -> gp.GeoDataFrame:
    gdf = __CalcTVPerAcre__(gdf)
    gdf = __RemoveOutliers__(gdf)
    gdf = __CalcCovariates__(gdf)

    return gdf

'''
Takes in zoning polygons and unions them 
Based on if they are high density or not
Returns tuple of (highd_zones, lowd_polygons)
'''
def __JoinZones__(zoning_gdf) -> tuple:
    highd_codes = ["RMP", "RM1", "RM2", "RM3", 
                   "RM4", "RX", "CM1", "CM2",
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

def __CalcTVPerAcre__(lots_gdf) -> gp.GeoDataFrame:
    lots_gdf["total value/acre"] = lots_gdf["TOTALVAL"] / lots_gdf["GIS_ACRES"]
    return lots_gdf

'''
Use Mahalanobis Distance to remove outliers from the data
Apply independently to control/treatment
Outliers in this data are generally just Areal Unit Problems
'''
def __RemoveOutliers__(gdf):
    #only include x and y var
    data = gdf[["distance to border (mi)", "total market value/acre"]].values

    mean = np.mean(data, axis=0)

    covm =  np.cov(data, rowvar=False)
    inv_covm = np.linalg.inv(covm)

    distances = []
    for row in data:
        distances.append(mahalanobis(row, mean, inv_covm))
    
    threshold = np.sqrt(chi2.ppf(0.975, df=2))
    gdf = gdf[distances < threshold]

    return gdf

'''
Check confounding, preestablished x vars
In this method, I check year built
Checked independently per zone
'''
def __CalcCovariates__(gdf) -> gp.GeoDataFrame:
    nonzero_gdf = gdf[gdf["YEARBUILT"] != 0]

    #replace 0 values with the median of the area
    median = nonzero_gdf["YEARBUILT"].median()   
    gdf["YEARBUILT"] = gdf["YEARBUILT"].replace(0, median)

    return gdf

'''
Calc Placebo values to help ensure that only ONE var is causing treatment
I analyze dist to a number of agents of division, redlining & highways
to see if zoning follows segregated boundaries
Assumes that lots_gdf geometries are centroids
'''
def __CalcPlacebos__(lots_gdf, highways_gdf, redlining_gdf):
    #initial processing
    h_linestring = highways_gdf.union_all()

    redline_areas = ["C", "D"]
    redlined = redlining_gdf[redlining_gdf["holc_grade"].isin(redline_areas)]
    r_poly = redlined.union_all()

    lots_gdf["distance to redlined border (mi)"] = lots_gdf.distance(r_poly.boundary) * 0.00018939

    lots_gdf["distance to highway (mi)"] = lots_gdf.distance(h_linestring) * 0.00018939
    return lots_gdf

def __PlotScatter__(gdf, x_label, y_label):
    gdf.plot(x=x_label, y=y_label, kind="scatter")
    plt.show()