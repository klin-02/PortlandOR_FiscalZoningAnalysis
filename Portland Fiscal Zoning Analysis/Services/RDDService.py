import rdrobust as rr
import rddensity as rd
import pandas as pd
import seaborn as sb
from matplotlib import pyplot as plt

def Fit(data, x_label, y_label):
    data = pd.DataFrame(data)
    x_label = str(x_label)
    y_label = str(y_label)

    '''
    Conditions for inference
    '''
    #check trends & patterns w/quartile-spaced bins (Discontinuity condition)
    result = rr.rdplot(y=data[y_label], x=data[x_label], binselect="qs", y_label=y_label, x_label=x_label, nbins=30) 

    #check if counts are similar near the cusp (Randomness condition)

    ax = sb.histplot(data=data[data[x_label] < 0][x_label], bins=15, color="lightblue")
    sb.histplot(data=data[data[x_label] > 0][x_label], bins=15, ax=ax, color="red")

    plt.xlabel(x_label)
    plt.ylabel("n of observations")
    plt.axvline(0, color="black")
    plt.grid()
    plt.show()
