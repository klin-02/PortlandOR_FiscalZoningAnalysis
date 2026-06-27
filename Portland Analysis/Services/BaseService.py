from abc import ABC, abstractmethod
import rdrobust as rr
from pandas import concat

class BaseService(ABC):
    def __init__(self, data, x_label, y_label):
        self.data = data,
        self.x_label = x_label,
        self.y_label = y_label

    @abstractmethod
    def Fit(self):
        raise NotImplementedError
    
    def _GetBandwidths_(self, c, cluster_id=None) -> float:
        result = rr.rdbwselect(y=self.data[self.y_label].to_numpy().astype(float), x=self.data[self.x_label].to_numpy().astype(float), c=c, kernel="tri", cluster=cluster_id)
        print(result)
        return result.bws

    @abstractmethod
    def _BandwidthSensitivity_(self, multiplier, h, rho):
        raise NotImplementedError

    @abstractmethod
    def _FalseCutoff_(self, h, multiplier):
        raise NotImplementedError

    @abstractmethod
    def _CloseObservations_(self, h, removal_percentage):
        removal_percentage = abs(removal_percentage)
        removal_bw = h * removal_percentage

        df1 = self.data[self.data[self.x_label] > removal_bw]
        df2 = self.data[self.data[self.x_label] < removal_bw * -1]
        self.data = concat([df1, df2])

    @abstractmethod
    def _RunModel_(self, c, h, rho, title):
        raise NotImplementedError
