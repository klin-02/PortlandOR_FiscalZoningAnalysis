from BaseService import BaseService as bs
from statsmodels.formula.api import ols
from numpy import abs
from pandas import concat

class DiDService(bs):
    def __init__(self, data, x_label, y_label, treatment_label, time_label, cluster_label, covlabels_list):
        super.__init__(data, x_label, y_label)
        self.treatment_label = treatment_label
        self.time_label = time_label
        self.cluster_label = cluster_label
        self.covlabels_list = covlabels_list

    def Fit(self):
        self.data = self.data.drop(["index_right", "geometry"], axis=1)

        #take MSE-optimal bandwidth of data
        #make sure to cluster to avoid artificially-low standard errors from 'double-counted' data
        bws = self._GetBandwidths_(c=0, cluster_id=self.cluster_label)
        h_left = bws["h (left)"].iloc[0].astype(float)

        self._RunModel_(h_left, title=f"Diff-in-disc of {self.x_label} and {self.y_label}")

        #sensitivity test bandwidths at 50%, 75%, 125%, and 150%
        self._BandwidthSensitivity_(h=h_left, multiplier=0.5)
        self._BandwidthSensitivity_(h=h_left, multiplier=0.75)
        self._BandwidthSensitivity_(h=h_left, multiplier=1.25)
        self._BandwidthSensitivity_(h=h_left, multiplier=1.5)

        #test false cutoffs within control & treatment at 30% of the bandwidth
        self._FalseCutoff_(h=h_left, multiplier=0.3)
        self._FalseCutoff_(h=h_left, multiplier=-0.3)

        #test sensitivity to observations near the cutoff removing 25% and 50% of the optimal bw
        self._CloseObservations_(h=h_left, removal_percentage=0.25)
        self._CloseObservations_(h=h_left, removal_percentage=0.5)

    def _BandwidthSensitivity_(self, multiplier, h, rho=None):
        self._RunModel_(h=(h * multiplier), title=f"Diff-in-disc of {self.x_label} and {self.y_label} at {multiplier} of bw")

    def _FalseCutoff_(self, h, multiplier):
        c = h * multiplier
        
        original_data = self.data

        treatment = self.data[self.data[self.x_label] > c]
        control = self.data[self.data[self.x_label] < c]

        treatment[self.treatment_label] = 1
        control[self.treatment_label] = 0

        self.data = concat([control, treatment])

        bws = self._GetBandwidths_(c, self.cluster_label)
        h_left = bws["h (left)"].iloc[0].astype(float)

        self._RunModel_(h_left, title=f"Diff-in-disc of {self.x_label} and {self.y_label} w/false cutoff at {c}")
        self.data = original_data

    def _CloseObservations_(self, h, removal_percentage):
        original_data = self.data
        
        super()._CloseObservations_(h, removal_percentage)

        bws = self._GetBandwidths_(c=0, cluster_id=self.cluster_label)
        h_left = bws["h (left)"].iloc[0].astype(float)

        self._RunModel_(h_left, title=f"Diff-in-disc of {self.x_label} and {self.y_label} w/percent removed {removal_percentage}")
        self.data = original_data

    def _RunModel_(self, h, title, c=None, rho=None):
        d = self.data[abs(self.data[self.x_label]) <= h]

        formula = f"Q('{self.y_label}')~Q('{self.x_label}')*Q('{self.treatment_label}')*Q('{self.time_label}')"

        for label in self.covlabels_list:
            formula += f"+Q('{label}')*Q('{self.time_label}')"

        result = ols(formula=formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[self.cluster_label]})
        print(result.summary())
        print(result.pvalues)
