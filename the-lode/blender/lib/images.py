import struct,zlib
import numpy as np
def png(path,image):
    data=np.ascontiguousarray(np.rint(np.clip(image,0,1)*255).astype('uint8'))
    h,w=data.shape[:2];channels=1 if data.ndim==2 else data.shape[2]
    def chunk(typ,b):return struct.pack('>I',len(b))+typ+b+struct.pack('>I',zlib.crc32(typ+b)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in data[::-1])
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,{1:0,3:2,4:6}[channels],0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
