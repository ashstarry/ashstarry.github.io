import numpy as np
from pathlib import Path
from .layout import WX0,WX1,WY0,WY1
ASSETS=Path(__file__).resolve().parents[2]/'web/assets'
class Ground:
    grid=None
    def z(self,x,y):
        if self.grid is None:
            self.grid=np.fromfile(ASSETS/'height.bin',dtype='<f4').reshape(1024,1024)
        fx=(x-WX0)/(WX1-WX0)*1023;fy=(y-WY0)/(WY1-WY0)*1023
        if not (0<=fx<1023 and 0<=fy<1023):return -9999.
        a=int(fx);b=int(fy);q=self.grid[b:b+2,a:a+2]
        w=np.array([[(1-fx+a)*(1-fy+b),(fx-a)*(1-fy+b)],[(1-fx+a)*(fy-b),(fx-a)*(fy-b)]])
        w*=q>-9000
        return float((q*w).sum()/w.sum()) if w.sum()>.01 else -9999.
G=Ground()
