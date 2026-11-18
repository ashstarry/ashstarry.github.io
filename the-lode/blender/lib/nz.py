"""Repeatable vectorised value noise. Array axes are north and east."""
import numpy as np

def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)
def lattice(x,y,seed=0):
    with np.errstate(over='ignore'):
        h=x.astype('uint32')*np.uint32(2246822519)+y.astype('uint32')*np.uint32(3266489917)+np.uint32(seed*8191)
        h^=h>>13; h*=np.uint32(2246822519);h^=h>>16
    return (h.astype('float32')/4294967296.)
def noise(x,y,period=1.,seed=0):
    a=x/period; b=y/period
    ix=np.floor(a).astype('int32');iy=np.floor(b).astype('int32')
    u=smooth(a-ix).astype('float32');v=smooth(b-iy).astype('float32')
    n00=lattice(ix,iy,seed);n10=lattice(ix+1,iy,seed);n01=lattice(ix,iy+1,seed);n11=lattice(ix+1,iy+1,seed)
    l=n00+(n10-n00)*u;r=n01+(n11-n01)*u
    return l+(r-l)*v
