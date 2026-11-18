import numpy as np
from lib.images import png
from lib.nz import smooth
def build(out,log):
    out=out/'tex';out.mkdir(parents=True,exist_ok=True);N=1024
    ry,rx=np.mgrid[:N,:N].astype('float32')/N;rng=np.random.default_rng(714)
    def value(nx,ny):
        v=rng.random((ny,nx),dtype='float32');fx=rx*nx;fy=ry*ny;ix=fx.astype('int32');iy=fy.astype('int32');u=smooth(fx-ix);t=smooth(fy-iy)
        return ((1-t)*((1-u)*v[iy%ny,ix%nx]+u*v[iy%ny,(ix+1)%nx])+t*((1-u)*v[(iy+1)%ny,ix%nx]+u*v[(iy+1)%ny,(ix+1)%nx])).astype('float32')
    def fract(n,m=None):
        m=m or n
        return np.clip(.5+(.57*(value(n,m)-.5)+.27*(value(n*2,m*2)-.5)+.16*(value(n*5,m*5)-.5))*1.57,0,1)
    def cells(n):
        ox=rng.uniform(.12,.88,(n,n));oy=rng.uniform(.12,.88,(n,n));ident=rng.random((n,n))
        a=rx*n;b=ry*n;ix=a.astype('int32');iy=b.astype('int32')
        d0=np.full(a.shape,8,'float32');d1=d0.copy();ids=d0.copy()
        for y in (-1,0,1):
            for x in (-1,0,1):
                j=(iy+y)%n;i=(ix+x)%n;d=((ix+x+ox[j,i]-a)**2+(iy+y+oy[j,i]-b)**2).astype('float32');win=d<d0
                d1=np.where(win,d0,np.minimum(d1,d));d0=np.minimum(d0,d);ids=np.where(win,ident[j,i],ids)
        return np.clip((np.sqrt(d1)-np.sqrt(d0))*2.7,0,1),ids
    a=fract(5);cell,ids=cells(19);grain=rng.random((N,N),dtype='float32');ridge=1-abs(fract(7)*2-1)
    streak=fract(52,3);png(out/'noise_a.png',np.stack([a,cell,grain],-1));png(out/'noise_b.png',np.stack([ridge**2,streak,ids],-1))
    for name,h,amplitude in [('rock_n',.50*fract(12)+.27*cell+.16*fract(53)+.07*grain,11.),('metal_n',.65*streak+.33*fract(24)+.02*grain,3.),('conc_n',.38*fract(28)+.35*fract(71)+.27*grain,2.8)]:
        dx=(np.roll(h,1,1)-np.roll(h,-1,1))*amplitude;dy=(np.roll(h,1,0)-np.roll(h,-1,0))*amplitude
        n=np.stack((dx,dy,np.ones_like(dx)),-1);n/=np.linalg.norm(n,axis=2)[:,:,None];png(out/(name+'.png'),n*.5+.5)
    log('Five tileable 1024² numpy textures.')
