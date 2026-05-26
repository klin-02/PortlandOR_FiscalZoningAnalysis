from matplotlib import pyplot as plt
import matplotlib
import geopandas as gp

def main():
    import StatisticsCalculator as sc

    highways_gdf = __Prep__(r"Resources\highways.geojson", 2913)
    redlining_gdf = __Prep__(r"Resources\redlining.geojson", 2913)
    lots_gdf = __Prep__(r"Resources\Taxlots_(Public).geojson", 2913)
    zoning_gdf = __Prep__(r"Resources\Zoning.zip", 2913)

    lots_gdf = __CleanLotData__(lots_gdf)
    zoning_gdf = __CleanZoningData__(zoning_gdf)

    sc.GeoRDDAnalysis(highways_gdf, redlining_gdf, lots_gdf, zoning_gdf)

'''
Preprocessing
'''
def __Prep__(path, crs) -> gp.GeoDataFrame:
    gdf = gp.read_file(path)
    gdf = gdf.to_crs(epsg=crs)

    return gdf

'''
Data filtering
'''
def __CleanLotData__(lots_gdf) -> gp.GeoDataFrame:
    lots_gdf = gp.GeoDataFrame(lots_gdf)

    #get lots within city limits
    lots_gdf = lots_gdf[lots_gdf["SITECITY"] == "PORTLAND"]

    lots_gdf = lots_gdf[["ORTAXLOT", "YEARBUILT", "PROP_CODE", "TOTALVAL", "GIS_ACRES", "geometry"]]

    #keep only residential, commercial, and multifamily land uses, respectively
    prop_codes = [
        "101", '102', '109', '121', '122', '131', '151', '171', '191',
        '201', '202', '211', '212', '221', '222', '231', '271',
        '701', '702', '707', '711', '712', '717', '721', '722', '727', '731', '737']

    lots_gdf = lots_gdf[lots_gdf["PROP_CODE"].isin(prop_codes)]

    #remove unusually small apartment lots
    agg_func = {
        "YEARBUILT": "max",
        "PROP_CODE": "first",
        "TOTALVAL": "sum",
        "GIS_ACRES": "sum"
        }

    lots_gdf = lots_gdf.dissolve(by="ORTAXLOT", aggfunc=agg_func)
    return lots_gdf

def __CleanZoningData__(zoning_gdf) -> gp.GeoDataFrame:
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    #get zones within city limits
    zoning_gdf = zoning_gdf[zoning_gdf["CITY"] == "Portland"]

    zoning_gdf = zoning_gdf[["ZONE", "geometry"]]
    return zoning_gdf

if __name__ == "__main__":
    matplotlib.use("qt5agg",force=True)
    main()