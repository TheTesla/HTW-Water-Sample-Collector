#!/usr/bin/env python3

from xyzcad import render

from numba import njit
from fuzzyometry import bodies as bd
from fuzzyometry import combinations as cmb




@njit
def f(p):
    x, y, z, par = p

    r_chamfer = 1

    tol = 0.2
    d_slot = 1.8
    r_corner = 2/2

    wo = 70
    lo = 104
    ho = 25
    w_pcb = 47.5
    l_pcb = 80
    y_pcb = -10
    x_pcb = -9
    
    h_slot = 1.6
    z_slot = 8
    w_opn = 35

    w_bat = 60
    l_bat = 18
    h_bat = 18

    x_bat = 0
    y_bat = - l_bat / 2 + lo / 2 - 2
    z_bat = - h_bat / 2 + ho / 2 - 2
    

    solid = bd.fz_cuboid((x, y, z), (wo, lo, ho), 2)
    pcb_slot = bd.fz_cuboid((x+x_pcb, y+y_pcb, z+ho/2-z_slot), (w_pcb+tol, l_pcb+tol, h_slot+tol), r_chamfer)
    pcb = bd.fz_cuboid((x+x_pcb, y+y_pcb, z), (w_pcb-2*d_slot, l_pcb-2*d_slot, 2*ho), r_chamfer)
    corners = bd.fz_circle((abs(x+x_pcb)-w_pcb/2, abs(y+y_pcb)-l_pcb/2), r_corner)
    opn = bd.fz_cuboid((x+x_pcb, y+l_pcb/2, z), (w_opn, l_pcb-2*d_slot, 2*ho), r_chamfer)
    bat = bd.fz_cuboid((x+x_bat, y+y_bat, z+z_bat), (w_bat, l_bat, h_bat), r_chamfer)



    if cmb.fz_and_chamfer(r_chamfer, solid, -pcb_slot, -pcb, -corners, -opn, -bat) > 0:
        return False

    return True

if __name__ == "__main__":
    render.renderAndSave(f, "build/frame.stl", 0.3)


