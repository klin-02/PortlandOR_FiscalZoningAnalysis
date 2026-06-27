from BaseDiscontService import BaseDiscontService as bds
from statsmodels.formula.api import ols
from numpy import abs

class DiDService(bds):
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

    def _RunModel_(self, h, title, c=None, rho=None):
        d = self.data[abs(self.data[self.x_label]) <= h]

        formula = f"Q('{self.y_label}')~Q('{self.x_label}')*Q('{self.treatment_label}')*Q('{self.time_label}')"

        for label in self.covlabels_list:
            formula += f"+Q('{label}')*Q('{self.time_label}')"

        result = ols(formula=formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d[self.cluster_label]})
        print(result.summary())
        print(result.pvalues)
