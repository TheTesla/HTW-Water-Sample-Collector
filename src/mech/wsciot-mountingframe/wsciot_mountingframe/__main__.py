#!/usr/bin/env python3

from xyzcad import render

from numba import njit
from fuzzyometry import bodies as bd
from fuzzyometry import combinations as cmb

@njit
def f(p):
    x, y, z, par = p



    a = bd.fz_cuboid((x, y, z), (70,50,5), 2)
    if cmb.fz_and_chamfer(2, a) > 0:
        return False

    return True

if __name__ == "__main__":
    render.renderAndSave(f, "build/frame.stl", 0.3)


