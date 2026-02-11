#!/usr/bin/env python3

from xyzcad import render

from numba import njit
from fuzzyometry import bodies as bd
from fuzzyometry import combinations as cmb




@njit
def f(p):
    x, y, z, par = p

    r_chamfer = 1.

    tol = 0.5
    d_slot = 1.8
    r_corner = 2/2
    

    wo = 71
    lo = 101
    ho = 22
    w_pcb = 47.5
    l_pcb = 80
    y_pcb = -8.5
    x_pcb = -9.5
    ri_pcb = 3
    
    h_slot = 1.6
    z_slot = 11
    w_opn = 35

    w_bat = 60 #+ 2*tol
    l_bat = 15.5 #+ 2*tol
    h_bat = 18 #+ 2*tol

    w_bat_cut = wo - 7
    l_bat_cut = 9
    ri_bat_cut = 3

    x_bat = - 1
    y_bat = - l_bat / 2 + lo / 2 - 1.5
    z_bat = - h_bat / 2 + ho / 2 - 2
    


    w_opn_ant = wo/2 - (w_pcb/2 + x_pcb) - 2 
    l_opn_ant = lo - 10
    y_opn_ant = -1
    z_opn_ant = -2
    ri_opn_ant = 3

    l_opn_top = lo - 30
    h_opn_top = 7
    y_opn_top = -8
    ri_opn_top = 3

    solid = bd.fz_cuboid((x, y, z), (wo, lo, ho), 2)
    pcb_slot = bd.fz_cuboid((x+x_pcb, y+y_pcb, z+ho/2-z_slot), (w_pcb+2*tol, l_pcb+2*tol, h_slot+2*tol), r_chamfer)
    pcb = bd.fz_cuboid((x+x_pcb, y+y_pcb, z), (w_pcb-2*d_slot, l_pcb-2*d_slot, 2*ho), ri_pcb)
    corners = bd.fz_circle((abs(x+x_pcb)-w_pcb/2, abs(y+y_pcb)-l_pcb/2), r_corner)
    opn_pcb = bd.fz_cuboid((x+x_pcb, y-l_pcb/2, z), (w_opn, l_pcb-2*d_slot, 2*ho), r_chamfer)
    bat = bd.fz_cuboid((x+x_bat, y+y_bat, z+z_bat), (w_bat, l_bat, h_bat), r_chamfer)
    bat_cut = bd.fz_cuboid((x+wo/2, y+y_bat, z), (2*w_bat_cut, l_bat_cut, 2*ho), ri_bat_cut)
    opn_ant = bd.fz_cuboid((x+wo-w_opn_ant, y+y_opn_ant, z+z_opn_ant-ho/2), (wo, l_opn_ant, 2*ho), ri_opn_ant)
    opn_top = bd.fz_cuboid((x, y+y_opn_top, z-ho+h_opn_top), (2*wo, l_opn_top, ho), ri_opn_top)




    if cmb.fz_and_chamfer(r_chamfer, solid, -pcb_slot, -pcb, -corners, -opn_pcb, -bat, -opn_ant, -opn_top, -bat_cut) > 0:
        return False

    return True

if __name__ == "__main__":
    render.renderAndSave(f, "build/frame", 0.3)


