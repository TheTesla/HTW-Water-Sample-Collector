#!/usr/bin/env python3

from xyzcad import render

from numba import njit
from fuzzyometry import bodies as bd
from fuzzyometry import combinations as cmb
import pathlib




@njit
def f(p):
    x, y, z, par = p

    tol = 0.2

    wo = 9.5
    lo = 25 # 20
    ho = 13

    wr = 3.3 + tol # 2.8 + tol
    lr = 17.3 + tol + 2 # 14.3 + tol +2
    hr = 4.2 + 2.9 + tol #3.2 + 2.9 + tol
    zr = -1

    r_shaft = 3.65
    h_shaft = 1.9
    ds_shaft = 3
    l_shaft = 15
    r_hole = 4.5/2 + tol

    r_chamfer = 1.
    ri_chamfer = 0.1    

    case = bd.fz_cuboid((x, y, z), (wo, lo, ho), r_chamfer)    
    shaft = cmb.fz_and_chamfer(r_chamfer, bd.fz_sphere((x, (y+ds_shaft/2)%ds_shaft -ds_shaft/2, z-h_shaft), r_shaft), -y, y-lo/2-l_shaft)
    solid = cmb.fz_or_chamfer(r_chamfer, case, shaft)


    cbl_hole = bd.fz_circle((x, z-h_shaft), r_hole)
    reed_notch = bd.fz_cuboid((x, y+lo/2-lr/2, z-zr), (wr, lr, hr), ri_chamfer) 


    if cmb.fz_and_chamfer(r_chamfer, solid, -cbl_hole, -reed_notch) > 0:
        return False

    return True

if __name__ == "__main__":
    pathlib.Path("../../../gen/mech/wsciot-reedcase/").mkdir(parents=True, exist_ok=True)
    render.renderAndSave(f, "../../../gen/mech/wsciot-reedcase/reedcase", 0.1)


