"""Conservative occupancy checks for stationary non-protected capture poses."""
import math
from pathlib import Path


def validate_capture_pose(world, x, y, yaw):
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,y,yaw)):
        raise ValueError('capture pose must be finite')
    raw=(Path(world)/'map.pgm').read_bytes()
    magic,dimensions,maximum,pixels=raw.split(b'\n',3)
    if magic != b'P5' or maximum != b'255':
        raise ValueError('expected generated v1 occupancy image')
    width,height=map(int,dimensions.split())
    if len(pixels) != width*height:
        raise ValueError('invalid map image length')
    col=int(math.floor((x+1.)/.05))
    row=height-1-int(math.floor((y+5.)/.05))
    if not (6 <= col < width-6 and 6 <= row < height-6):
        raise ValueError('capture footprint outside map')
    if any(pixels[r*width+c] < 200 for r in range(row-6,row+7) for c in range(col-6,col+7)):
        raise ValueError('capture pose fails conservative 0.30m footprint check')
    return dict(x=float(x),y=float(y),yaw=float(yaw))
