import rdrobust as rr
import rddensity as rd
import pandas as pd
from rdrobust.funs import rdplot_output
import seaborn as sb
from matplotlib import pyplot as plt

def Fit(data, x_label, y_label):
    data = pd.DataFrame(data)
    x_label = str(x_label)
    y_label = str(y_label)

    '''
    Conditions for inference
    '''
    #check trends & patterns w/quartile-spaced bins, equal spaced bins, and those w/mv to view variance (Variance & Discontinuity condition)
    __CheckBins__("qs", data, x_label, y_label)
    __CheckBins__("es", data, x_label, y_label)
    __CheckBins__("qsmv", data, x_label, y_label)
    __CheckBins__("esmv", data, x_label, y_label)

    #randomness & anti-manipulation condition
    __TestDensity__(data, x_label)

    __RunModel__(data, c=0, x_label=x_label, y_label=y_label, title=f"zoning law & {y_label}")

    input("Press any key to cont...")

def __CheckBins__(bin_type, data, x_label, y_label):
    result = rr.rdplot(y=data[y_label].to_numpy().astype(float), x=data[x_label].to_numpy().astype(float), binselect=bin_type, y_label=y_label, x_label=x_label, title=bin_type)
    print(result)

    result.rdplot.show()

def __TestDensity__(data, x_label):
    result = rd.rddensity(data[x_label])
    print(result)
    print(result.__repr__())

    '''
    plot = rd.rdplotdensity(result, data[x_label], xlabel=x_label, ylabel="no. of observations", title="density test")
    plot.show()
    '''

def __RunModel__(data, c, x_label, y_label, title):
    result = rr.rdrobust(y=data[y_label].to_numpy().astype(float), x=data[x_label].to_numpy().astype(float), c=c, kernel="tri")
    print(result)

    #get bandwidth for sensitivity testing
    print(result.bws)

    plot = rr.plot_rdrobust(result, y=data[y_label].to_numpy().astype(float), x=data[x_label].to_numpy().astype(float), y_label=y_label, x_label=x_label, title=title)
    plot.show()