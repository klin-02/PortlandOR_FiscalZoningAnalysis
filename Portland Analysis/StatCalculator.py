import geopandas as gp
import pandas as pd
import numpy as np
import multiprocessing as mp
from matplotlib import pyplot as plt
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2
from shapely import intersection

def GeoRDDAnalysis(highways_gdf, redlining_gdf, lots_gdf, zoning_gdf):
    from Services.RDDService import RDDService as rs

    highways_gdf = gp.GeoDataFrame(highways_gdf)
    redlining_gdf = gp.GeoDataFrame(redlining_gdf)
    lots_gdf = gp.GeoDataFrame(lots_gdf)
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    zone_tup = _JoinZones_(zoning_gdf)

    highd_zones = zone_tup[0]
    lowd_zones = zone_tup[1]
    lots_tup = _DistFromBorder_(lots_gdf, highd_zones, lowd_zones)

    highd_lots = lots_tup[0]
    lowd_lots = lots_tup[1]

    highd_lots = _RDDIndependentPrep_(highd_lots)
    lowd_lots = _RDDIndependentPrep_(lowd_lots)

    lots_gdf = pd.concat([highd_lots, lowd_lots])
    lots_gdf = lots_gdf.drop(["index_right"], axis=1)

    lots_gdf = _CalcPlacebos_(lots_gdf, highways_gdf, redlining_gdf)

    lots_gdf = gp.GeoDataFrame(lots_gdf)

    rdd = rs(lots_gdf, x_label="distance to border (mi)", y_label="total value/acre")
    rdd.Fit()

    covar_rdd = rs(lots_gdf, x_label="distance to border (mi)", y_label="YEARBUILT")
    covar_rdd.Fit()

    placebo1_rdd = rs(lots_gdf, x_label="distance to border (mi)", y_label="distance to redlined border (mi)")
    placebo1_rdd.Fit()

    placebo2_rdd = rs(lots_gdf, x_label="distance to border (mi)", y_label="distance to highway (mi)")
    placebo2_rdd.Fit()

    print("")

def _RDDIndependentPrep_(gdf) -> gp.GeoDataFrame:
    gdf = _RemoveOutliers_(gdf)
    gdf = _CalcCovariates_(gdf)

    return gdf

'''
Takes in zoning polygons and unions them 
Based on if they are high density or not
Returns tuple of (highd_zones, lowd_polygons)
'''
def _JoinZones_(zoning_gdf) -> tuple:
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
def _DistFromBorder_(lots_gdf, highd_gdf, lowd_gdf) -> tuple:
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

'''
Use Mahalanobis Distance to remove outliers from the data
Apply independently to control/treatment
Outliers in this data are generally just Areal Unit Problems
'''
def _RemoveOutliers_(gdf):
    #only include x and y var
    data = gdf[["distance to border (mi)", "total value/acre"]].values

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
def _CalcCovariates_(gdf) -> gp.GeoDataFrame:
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
def _CalcPlacebos_(lots_gdf, highways_gdf, redlining_gdf):
    #initial processing
    h_linestring = highways_gdf.union_all()

    redline_areas = ["C", "D"]
    redlined = redlining_gdf[redlining_gdf["holc_grade"].isin(redline_areas)]
    r_poly = redlined.union_all()

    lots_gdf["distance to redlined border (mi)"] = lots_gdf.distance(r_poly.boundary) * 0.00018939

    lots_gdf["distance to highway (mi)"] = lots_gdf.distance(h_linestring) * 0.00018939
    return lots_gdf

def _PlotScatter_(gdf, x_label, y_label):
    gdf.plot(x=x_label, y=y_label, kind="scatter")
    plt.show()

'''
Analyze the possibility of fiscal zoning occuring w/Diff in Disc
Look at observations pre-HB2001 (2018) and post-Portland implementation (2022)
Account for COVID-induced changes in the American city w/dist. to CBD and density
'''
def DiffInDiscAnalysis(historics_gdf, footprints_gdf, neighborhoods_gdf, zoning_gdf):
    from Services.DiDService import DiDService as ds

    historics_gdf = _CalcDiDCovars_(historics_gdf, footprints_gdf, neighborhoods_gdf)

    zone_tup = _JoinZones_(zoning_gdf)

    highd_zones = zone_tup[0]
    lowd_zones = zone_tup[1]
    historics_tup = _DistFromBorder_(historics_gdf, highd_zones, lowd_zones)

    highd_historics = historics_tup[0]
    lowd_historics = historics_tup[1]

    post_t1 = _DiDIndepdentPrep_(highd_historics, drop="total value/acre (2018)", col="total value/acre (2022)", after=True, treatment=True)
    post_t0 = _DiDIndepdentPrep_(highd_historics, drop="total value/acre (2022)", col="total value/acre (2018)", after=False, treatment=True)
    pre_t1 = _DiDIndepdentPrep_(lowd_historics, drop="total value/acre (2018)", col="total value/acre (2022)", after=True, treatment=False)
    pre_t0 = _DiDIndepdentPrep_(lowd_historics, drop="total value/acre (2022)", col="total value/acre (2018)", after=False, treatment=False)

    historics_gdf = pd.concat([post_t1, post_t0, pre_t1, pre_t0])
    historics_gdf = gp.GeoDataFrame(historics_gdf)

    covlabels_list = ["building coverage", "dist. to CBD (mi)"]

    #with covars
    Ds_Wcovars = ds(
        historics_gdf, 
        x_label="distance to border (mi)", 
        y_label="total value/acre", 
        treatment_label="treatment", time_label="time", 
        cluster_label="sid", 
        covlabels_list=covlabels_list
        )
    Ds_Wcovars.Fit()

    #without covars
    Ds_Nocovars = ds(
        historics_gdf, 
        x_label="distance to border (mi)", 
        y_label="total value/acre", 
        treatment_label="treatment", time_label="time", 
        cluster_label="sid", 
        covlabels_list=[]
        )
    Ds_Nocovars.Fit()

def _DiDIndepdentPrep_(gdf, drop, col, after, treatment) -> gp.GeoDataFrame:
    changed = gdf.drop([drop], axis=1)
    changed["time"] = int(after)
    changed["treatment"] = int(treatment)
    changed["total value/acre"] = changed[col]
    changed = changed.drop([col], axis=1)

    changed = _RemoveOutliers_(changed)
    return changed

'''
Calc covars to potentially account for covid shocks
Needs og lot geometries
'''
def _CalcDiDCovars_(historics_gdf, footprints_gdf, neighborhoods_gdf) -> gp.GeoDataFrame:
    footprints_gdf["geometry"] = footprints_gdf.geometry.make_valid()
    footprints_gdf = footprints_gdf[["geometry"]]

    intersections_gdf = _MultithreadedOverlay_(historics_gdf, footprints_gdf)
    intersections_gdf = _DropDuplicatesWithSamePoints_(intersections_gdf)
    intersections_gdf["intersection areas"] = intersections_gdf.geometry.area

    agg_func = {
        "intersection areas": "sum",
        "total value/acre (2018)": "first",
        "total value/acre (2022)": "first",
        }
    intersections_gdf = intersections_gdf.groupby("sid", as_index=False).agg(agg_func)
    intersections_gdf = intersections_gdf[["sid", "intersection areas"]]

    historics_gdf = historics_gdf.merge(intersections_gdf, on="sid")

    historics_gdf["building coverage"] = historics_gdf["intersection areas"] / historics_gdf.geometry.area
    historics_gdf = historics_gdf.drop(["intersection areas"], axis=1)

    downtown_list = ["PORTLAND DOWNTOWN", "OLD TOWN", "PEARL DISTRICT", "LLOYD"]
    downtown = neighborhoods_gdf[neighborhoods_gdf["NAME"].isin(downtown_list)]

    downtown_poly = downtown.union_all()
    historics_gdf["dist. to CBD (mi)"] = historics_gdf.distance(downtown_poly.boundary) * 0.00018939
    return historics_gdf

def _MultithreadedOverlay_(df1, df2) -> gp.GeoDataFrame:
    core_count = mp.cpu_count()   
    data_chunks = np.array_split(df1, core_count)
    pool = mp.Pool(core_count)

    processes = [pool.apply_async(gp.overlay, args=(data, df2, "intersection"))
        for data in data_chunks]

    results = [process.get() for process in processes]
    return gp.GeoDataFrame(pd.concat(results), crs = df1.crs)

def _DropDuplicatesWithSamePoints_(gdf) -> gp.GeoDataFrame:
    gdf = gp.GeoDataFrame(gdf)

    gdf["geometry"] = gdf.normalize()
    gdf["wkt"] = gdf.geometry.to_wkt()

    gdf = gdf.drop_duplicates("wkt")
    gdf = gdf.drop(["wkt"], axis=1)
    return gp.GeoDataFrame(gdf)
