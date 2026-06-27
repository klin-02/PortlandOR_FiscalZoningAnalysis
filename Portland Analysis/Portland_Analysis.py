from matplotlib import pyplot as plt
import matplotlib
import geopandas as gp
from shapely.geometry import MultiPolygon
from pandas import concat
import pyproj

def main():
    import StatisticsCalculator as sc

    highways_gdf = _Prep_(r"Resources\highways.geojson", crs=2913)
    redlining_gdf = _Prep_(r"Resources\redlining.geojson", crs=2913)

    lots_gdf = _Prep_(r"Resources\Taxlots_(Public).geojson", crs=2913)
    zoning_gdf = _Prep_(r"Resources\Zoning.zip", crs=2913)

    #set crs since to_crs makes (inf, inf) polygons
    historics_gdf = gp.read_file(r"Resources\2018-2022_PortlandTaxlotAssessments.geojson")
    historics_gdf = historics_gdf.set_crs(epsg=2913, allow_override=True)

    development_2018 = _Prep_(r"Resources\Vacant_and_Developed_Land_2018.geojson", crs=2913)
    development_2022 = _Prep_(r"Resources\Vacant_and_Developed_Land_2022.geojson", crs=2913)
    footprints_gdf = _Prep_(r"Resources\Building_Footprints_-8229304965479720636.zip", crs=2913)
    neighborhoods_gdf = _Prep_(r"Resources\Neighborhoods.geojson", crs=2913)
    
    #lots_gdf = _CleanLotData_(lots_gdf)
    zoning_gdf = _CleanZoningData_(zoning_gdf)
    historics_gdf = _CleanHistoricsData_(historics_gdf, development_2018, development_2022)

    sc.DiffInDiscAnalysis(historics_gdf, footprints_gdf, neighborhoods_gdf, zoning_gdf)
    #sc.GeoRDDAnalysis(highways_gdf, redlining_gdf, lots_gdf, zoning_gdf)

'''
Preprocessing
'''
def _Prep_(path, crs) -> gp.GeoDataFrame:
    gdf = gp.read_file(path)
    gdf = gdf.to_crs(epsg=crs)

    return gdf

'''
Data filtering
'''
def _CleanLotData_(lots_gdf) -> gp.GeoDataFrame:
    #get lots within city limits
    lots_gdf = lots_gdf[lots_gdf["SITECITY"] == "PORTLAND"]

    #keep only residential, commercial, and multifamily land uses, respectively
    prop_codes = [
        "101", '102', '109', '121', '122', '131', '151', '171', '191',
        '201', '202', '211', '212', '221', '222', '231', '271',
        '701', '702', '707', '711', '712', '717', '721', '722', '727', '731', '737']

    lots_gdf = lots_gdf[lots_gdf["PROP_CODE"].isin(prop_codes)]
    
    '''
    #get portland lots real quick (need this data to scrape)
    from shapely.geometry.polygon import Polygon
    from shapely.geometry.multipolygon import MultiPolygon

    lots_gdf = lots_gdf[["PRIMACCNUM", "geometry"]]
    lots_gdf.geometry = [MultiPolygon([f]) if isinstance(f, Polygon)
        else f for f in lots_gdf.geometry]
    lots_gdf.to_file("Output\\Processed_PortlandLots_2026.geojson", driver="GeoJSON")
    '''
    
    lots_gdf = lots_gdf[["ORTAXLOT", "YEARBUILT", "PROP_CODE", "TOTALVAL", "GIS_ACRES", "geometry"]]
    
    #remove unusually small apartment lots
    agg_func = {
        "YEARBUILT": "max",
        "PROP_CODE": "first",
        "TOTALVAL": "sum",
        "GIS_ACRES": "sum"
        }

    lots_gdf = lots_gdf.dissolve(by="ORTAXLOT", aggfunc=agg_func)
    lots_gdf["total value/acre"] = lots_gdf["TOTALVAL"] / lots_gdf["GIS_ACRES"]
    return lots_gdf

def _CleanZoningData_(zoning_gdf) -> gp.GeoDataFrame:
    #get zones within city limits
    zoning_gdf = zoning_gdf[zoning_gdf["CITY"] == "Portland"]

    zoning_gdf = zoning_gdf[["ZONE", "geometry"]]
    return zoning_gdf

def _CleanHistoricsData_(historics_gdf, development_2018, development_2022) -> gp.GeoDataFrame:
    #calc area for later val/acre calculations
    historics_gdf["gis area"] = historics_gdf.geometry.area * 0.00002296
    
    #get vacant lots (remove duplicate points too)
    vacant_2018 = development_2018[development_2018["VAC"] == 1]
    vacant_2022 = development_2022[development_2022["VAC"] == 1]
    vacant_2018 = vacant_2018[["geometry"]]
    vacant_2022 = vacant_2022[["geometry"]]

    #copy state id into new column since dissolve gets rid of the original
    historics_gdf["sid"] = historics_gdf["state id"]

    agg_func = {
        "total value (2018)": "sum",
        "total value (2022)": "sum",
        "gis area": "sum",
        "sid": "first"
        }
    historics_gdf = historics_gdf.dissolve(by="state id", aggfunc = agg_func)

    historics_gdf["total value/acre (2018)"] = historics_gdf["total value (2018)"] / historics_gdf["gis area"]
    historics_gdf["total value/acre (2022)"] = historics_gdf["total value (2022)"] / historics_gdf["gis area"]
    
    #find properties in vacant lots then drop them from the data
    historics_gdf["centroid"] = historics_gdf.centroid
    historics_gdf = historics_gdf.set_geometry("centroid")
    centroids_1 = historics_gdf.sjoin(vacant_2018).drop(["index_right"], axis=1)
    centroids_2 = historics_gdf.sjoin(vacant_2022).drop(["index_right"], axis=1)
    centroids = concat([centroids_1, centroids_2, historics_gdf]).drop_duplicates(keep=False)
    historics_gdf = historics_gdf.set_geometry("geometry")
    historics_gdf = historics_gdf.drop(["centroid"], axis=1)

    historics_gdf = gp.GeoDataFrame(historics_gdf)
    return historics_gdf[["total value/acre (2018)", "total value/acre (2022)", "sid", "geometry"]]
    
if __name__ == "__main__":
    pyproj.network.set_network_enabled(False)
    matplotlib.use("qt5agg",force=True)
    main()
