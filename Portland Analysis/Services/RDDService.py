from BaseService import BaseService as bs
import rdrobust as rr
import rddensity as rd
import pandas as pd
from rdrobust.funs import rdplot_output
from matplotlib import pyplot as plt
from pandas import concat

class RDDService(bs):
    def __init__(self, data, x_label, y_label):
        super.__init__(data, x_label, y_label)

    def Fit(self):
        '''
        Conditions for inference
        '''
        #check trends & patterns w/quartile-spaced bins, equal spaced bins, and those w/mv to view variance (Variance & Discontinuity condition)
        self._CheckBins_("qs")
        self._CheckBins_("es")
        self._CheckBins_("qsmv")
        self._CheckBins_("esmv")

        #randomness & anti-manipulation condition
        #self._TestDensity_()

        bws = self._GetBandwidths_(c=0)

        #since bandwidths are symmetric (same on right and left), just get left bandwidth
        h_left = bws["h (left)"].iloc[0].astype(float)
        b_left = bws["b (left)"].iloc[0].astype(float)

        #rho remains constant since for a single dataset, h/b -> rho for the set [0, infinity]
        #see Bonander et al. (2023)
        rho = h_left / b_left

        self._RunModel_(c=0, h=h_left, rho=rho, title=f"zoning law & {self.y_label}")

        #sensitivity test bandwidths at 50%, 75%, 125%, and 150%
        self._BandwidthSensitivity_(h=h_left, rho=rho, multiplier=0.5)
        self._BandwidthSensitivity_(h=h_left, rho=rho, multiplier=0.75)
        self._BandwidthSensitivity_(h=h_left, rho=rho, multiplier=1.25)
        self._BandwidthSensitivity_(h=h_left, rho=rho, multiplier=1.5)

        #test false cutoffs within control & treatment at 30% of the bandwidth
        self._FalseCutoff_(h=h_left, multiplier=0.3)
        self._FalseCutoff_(h=h_left, multiplier=-0.3)

        #test sensitivity to observations near the cutoff removing 25% and 50% of the MSE-optimal bw
        self._CloseObservations_(h=h_left, removal_percentage=0.25)
        self._CloseObservations_(h=h_left, removal_percentage=0.5)

    input("Press any key to cont...")

    def _CheckBins_(self, bin_type):
        result = rr.rdplot(
            y=self.data[self.y_label].to_numpy().astype(float), 
            x=self.data[self.x_label].to_numpy().astype(float), 
            binselect=bin_type, 
            y_label=self.y_label, 
            x_label=self.x_label, 
            title=bin_type
            )
        print(result)

        result.rdplot.show()

    '''
    def _TestDensity_(self):
        result = rd.rddensity(self.data[self.x_label])
        print(result)
        print(result._repr_())

        plot = rd.rdplotdensity(result, self.data[self.x_label], xlabel=self.x_label, ylabel="no. of observations", title="density test")
        plot.show()
    '''

    '''
    Post-rdd sensitivity tests for validity
    Check if units of the optimal rdd test are manipulating the results
    '''
    def _BandwidthSensitivity_(self, h, rho, multiplier):
        self._RunModel_(c=0, h=(h * multiplier), rho=rho, title=f"zoning law & {self.y_label} at {multiplier} of bw")

    def _FalseCutoff_(self, h, multiplier):
        c = h * multiplier

        #recalc new bandwidth
        self._RunModel_(c=c, h=None, rho=None, title=f"zoning law & {self.y_label} w/false cutoff at {c}")

    def _CloseObservations_(self, h, removal_percentage):
        original_data = self.data
        
        super()._CloseObservations_(h, removal_percentage)

        #recalc new bandwidth
        self._RunModel_(c=0, h=None, rho=None, title=f"zoning law & {self.y_label} w/percent removed {removal_percentage}")
        self.data = original_data

    def _RunModel_(self, c, h, rho, title):
        result = rr.rdrobust(
            y=self.data[self.y_label].to_numpy().astype(float), 
            h=h, 
            rho=rho, 
            x=self.data[self.x_label].to_numpy().astype(float), 
            c=c, 
            kernel="tri"
            )
        print(result)

        plot = rr.plot_rdrobust(
            result, 
            y=self.data[self.y_label].to_numpy().astype(float), 
            x=self.data[self.x_label].to_numpy().astype(float), 
            y_label=self.y_label, 
            x_label=self.x_label, 
            title=title
            )
        #breakpoint this guy bc rdrobust has a brain anerysum if you don't
        plot.show()
