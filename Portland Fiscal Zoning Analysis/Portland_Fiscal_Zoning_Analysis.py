from matplotlib import pyplot as plt
import geopandas as gp

def main():
    import StatisticsCalculator as sc

    lots_p = r"Taxlots_(Public).geojson"
    zoning_p = r"Zoning.zip"

    lots_gdf = gp.read_file(lots_p)
    zoning_gdf = gp.read_file(zoning_p)

    lots_gdf = lots_gdf.to_crs(epsg=2913)
    zoning_gdf = zoning_gdf.to_crs(2913)

    lots_gdf = CleanUpLotData(lots_gdf)
    zoning_gdf = CleanUpZoningData(zoning_gdf)

    sc.GeoRDDAnalysis(lots_gdf, zoning_gdf)

def CleanUpLotData(lots_gdf) -> gp.GeoDataFrame:
    lots_gdf = gp.GeoDataFrame(lots_gdf)

    #get lots within city limits
    lots_gdf = lots_gdf[lots_gdf["SITECITY"] == "PORTLAND"]

    lots_gdf = lots_gdf[["ORTAXLOT", "YEARBUILT", "PROP_CODE", "TOTALVAL", "GIS_ACRES", "geometry"]]

    #keep only residential, commercial, industrial, and multifamily land uses, respectively
    prop_codes = [
        "101", '102', '109', '121', '131', '151', '171', '191',
        '201', '202', '211', '212', '221', '222', '231', '271',
        '301', '303', '311', '313', '321', '323',
        '701', '702', '707', '711', '712', '717', '721', '722', '727', '731', '737']

    lots_gdf = lots_gdf[lots_gdf["PROP_CODE"].isin(prop_codes)]

    #remove unusually small apartment lots
    agg_func = {
        "YEARBUILT": "first",
        "PROP_CODE": "first",
        "TOTALVAL": "sum",
        "GIS_ACRES": "sum"
        }

    lots_gdf = lots_gdf.dissolve(by="ORTAXLOT", aggfunc=agg_func)
    lots_gdf = lots_gdf.drop(["ORTAXLOT"], axis=1)

    #why not
    lots_gdf.plot()
    plt.show()

    return lots_gdf

def CleanUpZoningData(zoning_gdf) -> gp.GeoDataFrame:
    zoning_gdf = gp.GeoDataFrame(zoning_gdf)

    #get zones within city limits
    zoning_gdf = zoning_gdf[zoning_gdf["CITY"] == "Portland"]

    zoning_gdf = zoning_gdf[["ZONE", "geometry"]]
    return zoning_gdf

if __name__ == "__main__":
    main()