#!/usr/bin/env python3

from xyzcad import render

from numba import njit
from fuzzyometry import bodies as bd
from fuzzyometry import combinations as cmb




@njit
def f(p):
    x, y, z, par = p

    r_chamfer = 1

    tol = 0.5
    d_slot = 1.8
    r_corner = 2/2
    r_bat_rnd = 15/2

    wo = 71
    lo = 101
    ho = 22
    w_pcb = 47.5
    l_pcb = 80
    y_pcb = -8.5
    x_pcb = -9.5
    
    h_slot = 1.6
    z_slot = 8
    w_opn = 35

    w_bat = 57 #+ 2*tol
    l_bat = 16 #+ 2*tol
    h_bat = 17 #+ 2*tol

    x_bat = -3
    y_bat = - l_bat / 2 + lo / 2 - 1
    z_bat = - h_bat / 2 + ho / 2 - 2
    
    w_opn_bat = wo/2 - (w_pcb/2 + x_pcb) - 2 
    l_opn_bat = lo - 10
    y_opn_bat = -1

    l_opn_top = lo - 20
    h_opn_top = 10

    solid = bd.fz_cuboid((x, y, z), (wo, lo, ho), 2)
    pcb_slot = bd.fz_cuboid((x+x_pcb, y+y_pcb, z+ho/2-z_slot), (w_pcb+2*tol, l_pcb+2*tol, h_slot+2*tol), r_chamfer)
    pcb = bd.fz_cuboid((x+x_pcb, y+y_pcb, z), (w_pcb-2*d_slot, l_pcb-2*d_slot, 2*ho), r_chamfer)
    corners = bd.fz_circle((abs(x+x_pcb)-w_pcb/2, abs(y+y_pcb)-l_pcb/2), r_corner)
    opn_pcb = bd.fz_cuboid((x+x_pcb, y-l_pcb/2, z), (w_opn, l_pcb-2*d_slot, 2*ho), r_chamfer)
    bat = bd.fz_cuboid((x+x_bat, y+y_bat, z+z_bat), (w_bat, l_bat, h_bat), r_chamfer)
    opn_bat = bd.fz_cuboid((x+wo-w_opn_bat, y+y_opn_bat, z), (wo, l_opn_bat, 2*ho), r_chamfer)
    opn_top = bd.fz_cuboid((x, y, z-ho+h_opn_top), (2*wo, l_opn_top, ho), r_chamfer)
    bat_rnd = bd.fz_circle((x, y+lo/2), r_bat_rnd)




    if cmb.fz_and_chamfer(r_chamfer, solid, -pcb_slot, -pcb, -corners, -opn_pcb, -bat, -opn_bat, -opn_top, -bat_rnd) > 0:
        return False

    return True

if __name__ == "__main__":
    render.renderAndSave(f, "build/frame.stl", 0.3)


