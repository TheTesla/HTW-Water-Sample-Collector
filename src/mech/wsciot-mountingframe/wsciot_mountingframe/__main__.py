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
    ho = 22
    w_pcb = 47.5
    l_pcb = 80
    y_pcb = -10
    x_pcb = -9
    
    h_slot = 1.6
    z_slot = 8
    w_opn = 35

    w_bat = 65 + tol
    l_bat = 18 + tol
    h_bat = 18 + tol

    x_bat = 0
    y_bat = - l_bat / 2 + lo / 2 - 2
    z_bat = - h_bat / 2 + ho / 2 - 2
    
    w_opn_bat = wo/2 - (w_pcb/2 + x_pcb) - 2 
    l_opn_bat = lo - 10

    l_opn_top = lo - 15
    h_opn_top = 10

    solid = bd.fz_cuboid((x, y, z), (wo, lo, ho), 2)
    pcb_slot = bd.fz_cuboid((x+x_pcb, y+y_pcb, z+ho/2-z_slot), (w_pcb+tol, l_pcb+tol, h_slot+tol), r_chamfer)
    pcb = bd.fz_cuboid((x+x_pcb, y+y_pcb, z), (w_pcb-2*d_slot, l_pcb-2*d_slot, 2*ho), r_chamfer)
    corners = bd.fz_circle((abs(x+x_pcb)-w_pcb/2, abs(y+y_pcb)-l_pcb/2), r_corner)
    opn_pcb = bd.fz_cuboid((x+x_pcb, y-l_pcb/2, z), (w_opn, l_pcb-2*d_slot, 2*ho), r_chamfer)
    bat = bd.fz_cuboid((x+x_bat, y+y_bat, z+z_bat), (w_bat, l_bat, h_bat), r_chamfer)
    opn_bat = bd.fz_cuboid((x+wo-w_opn_bat, y, z), (wo, l_opn_bat, 2*ho), r_chamfer)
    opn_top = bd.fz_cuboid((x, y, z-ho+h_opn_top), (2*wo, l_opn_top, ho), r_chamfer)




    if cmb.fz_and_chamfer(r_chamfer, solid, -pcb_slot, -pcb, -corners, -opn_pcb, -bat, -opn_bat, -opn_top) > 0:
        return False

    return True

if __name__ == "__main__":
    render.renderAndSave(f, "build/frame.stl", 0.3)


