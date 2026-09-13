"""Display-only LVLH rotation; physics and sensor coordinates stay untouched."""
import numpy as np

def display_coordinates(xy):
    """Cartesian display coordinates: X=-y, Y=x (positive Y is up)."""
    a=np.asarray(xy,dtype=float)
    if a.ndim==0 or a.shape[-1]!=2 or not np.isfinite(a).all():
        raise ValueError("Expected finite (...,2) LVLH vectors")
    return np.stack([-a[...,1],a[...,0]],axis=-1)

def rerun_coordinates(xy):
    """Rerun Spatial2D canvas has positive Y DOWN; bridge only that canvas."""
    return display_coordinates(xy)*[1,-1]
