#! /usr/bin/env python3
# use this to get live editing:
# echo tumbler.py |entr ./tumbler.py


import solid as s
import solid.objects as so
import os
import solid.utils as su
from math import pi, sqrt, atan2, asin, tan, cos, sin

depth = 200
thickness = 20
height = 75
width = 240
m3_support_depth = 6

gears = so.import_scad('gears.scad')

screw_clearance = {
        'm4': 4.5,
        'm3': 3.4,
}
screw_head_sink = {
        'm4': {'h': 4, 'diameter': 7.3},
        'm3': {'h': 2.5, 'diameter': 6.2}
}
screw_nut = {
        'm4': {'width': 7.0, 'depth': 3.6},
        'm3': {'width': 5.7, 'depth': 2.9}
}

def hex(width, h, fillet_radius = 0.1):
    """
    width is the distance between opposing flat sides
    """
    r = width/2.0/cos(pi/6.0) # magic so that we have the width b/w flat faces instead of corners
    pole = so.translate((r - fillet_radius, 0, 0))(so.cylinder(r=fillet_radius, h=h))
    body = pole
    for i in range(1,6):
        body += so.rotate((0,0,60 * i))(pole)
    return so.hull()(body)

def chamfer_hull(x=False, y=False, z=False, chamfer=1):
    ps = {}
    if x:
        ps[0] = x if isinstance(x, list) else [1,-1]
    if y:
        ps[1] = y if isinstance(y, list) else [1,-1]
    if z:
        ps[2] = z if isinstance(z, list) else [1,-1]
    def impl(scad):
        body = None
        for p in ps:
            for o in ps[p]:
                a = so.translate(([0]*p + [o * chamfer] + [0]*2)[:3])(scad)
                if body is None:
                    body = a
                else:
                    body += a
        return so.hull()(body)
    return impl


def heat_set_insert(diameter, depth, excess_diameter, excess_depth, taper_angle_degrees = 8, negative_depth=0, negative_diameter=None):
    """
    taper angle is going to specify the deflection off of zero s.t. the diameter is slightly less
    as you move closer to the bottom. The taper angle specifies the slope of the line off of the
    radial axis. The excess parameters are for a smaller hole that collects the melted material, so that it's not the same size as the portion that bonds to the insert.

    negative_depth creates material of exactly diameter but the hole, to create a path to move the insert
    during assembly and provide screwdriver access. If negative_diameter is specified, that's used instead of the insert hole diameter.
    """
    top_radius = diameter / 2.0
    if taper_angle_degrees == 0:
        bottom_radius = diameter / 2.0
    else:
        bottom_radius = diameter/2.0 - tan(taper_angle_degrees * pi / 180) * depth / 2.0
    negative_hole = None
    if negative_depth != 0:
        if negative_diameter is None:
            negative_radius = diameter / 2.0
        else:
            negative_radius = negative_diameter / 2.0
        negative_hole = so.translate((0,0,-negative_depth - 0.01))(so.cylinder(r=negative_radius, h=negative_depth + 0.01))
    insert_hole = so.translate((0,0,-0.01))(so.cylinder(r1=top_radius, r2=bottom_radius, h=depth + 0.01))
    excess_hole = so.translate((0,0,depth - 0.01))(so.cylinder(r=excess_diameter / 2.0, h=excess_depth + 0.01))
    total =  insert_hole + excess_hole
    if negative_hole is not None:
        total += negative_hole
    return total

m3_heatset_insert_hole = heat_set_insert(diameter = 5.3, depth = 6.4, excess_diameter = 3.5, excess_depth = 2.5)
screw_2_56_insert_hole = heat_set_insert(diameter = 3.175, depth = 4.7752, excess_diameter = 2.5, excess_depth = 3, negative_depth = 100, negative_diameter=4)

def sidewall():
    body = chamfer_hull(z=True, y=True)(so.cube((depth, thickness, height)))
    insert = so.rotate((0,90,0))(m3_heatset_insert_hole)
    for i in range(1,4):
        body -= so.translate((0,thickness/2.0,height/4.0*i))(insert)
        body -= so.translate((depth,thickness/2.0,height/4.0*i))(so.rotate((0,0,180))(insert))
    return body

def sidewall_clamp(): # my wood is 19.5mm wide and 38.6mm tall
    body = chamfer_hull(z=True, y=True)(so.cube((20, thickness, height)))
    body += chamfer_hull(z=True, y=True, x=[1])(so.translate((19,0,0))(so.cube((1, thickness, height))) + so.translate((50,-thickness*0.25,0))(so.cube((10, thickness*1.5, 45))))
    wood_cavity = so.translate((20,0,5))(so.cube((100,19.5,38.6)))
    body -= wood_cavity
    insert = so.rotate((0,90,0))(m3_heatset_insert_hole)
    for i in range(1,4):
        body -= so.translate((0,thickness/2.0,height/4.0*i))(insert)
        body -= so.translate((depth,thickness/2.0,height/4.0*i))(so.rotate((0,0,180))(insert))
    nut_recess = so.translate((54,-5,15))(so.rotate((90,30,0))(hex(screw_nut['m3']['width'], screw_nut['m3']['depth'])))
    screw_recess = so.translate((54,22.4+5,15))(so.rotate((90,0,0))(so.cylinder(screw_head_sink['m3']['diameter']/2.0, screw_nut['m3']['depth'])))
    screw_hole = so.translate((54,22.4+10,15))(so.rotate((90,0,0))(so.cylinder(screw_clearance['m3']/2.0, 100)))
    screw_capture = nut_recess + screw_recess + screw_hole
    def add_screw(x,y):
        nonlocal body
        body -= so.translate((-x,0,y))(screw_capture)
    add_screw(0,0)
    add_screw(0,17)
    add_screw(17/2.0,17/2.0)
    return body


def servo_mount():
    body = so.translate((0, -19.9/2, 0))(so.cube((thickness+2.0, 19.9, 40.5)))
    body = so.minkowski()(body, so.cube((0.5,0.5,0.5)))
    insert = so.rotate((0,90,0))(m3_heatset_insert_hole)
    for x in [-5, 5]:
        for y in [48.7/2.0, -48.7/2.0]:
            body += so.translate((0, x, y+40.5/2))(insert)
    # tips span 55.35, body spans 40.4
    # holes are 1cm apart by 48.7mm apart
    # shaft is in the middle about 9.37mm off of the bottom

    # also don't forget the cable route
    body += so.translate((thickness/2.0+1,0,-0.5))(so.cube((thickness+2,7,1), center=True))
    body += so.translate((thickness/2.0+1+5.5,0,-2))(so.cube((12,7,4), center=True))
    return body

def basewall(passive=False):
    body = chamfer_hull(z=True, y=True, x=[-1])(so.cube((thickness, width, height)))
    m3_hole = so.translate((thickness + 1.0 ,0,0))(so.rotate((0,-90,0))(so.cylinder(r=screw_clearance['m3']/2.0, h=m3_support_depth) + so.translate((0,0,m3_support_depth))(so.cylinder(r=screw_head_sink['m3']['diameter']/2.0, h=thickness+2.0-m3_support_depth))))
    for i in range(1,4):
        body -= so.translate((0,thickness/2.0,height/4.0*i))(m3_hole)
        body -= so.translate((0,width-thickness/2.0,height/4.0*i))(m3_hole)
    shaft_hole = so.cylinder(r=39.0/2+0.05, h=10) + so.cylinder(r=15.2/2+0.3, h=thickness+2)
    for i in [0,90,180,270]:
        shaft_hole += so.rotate((0,0,i))(so.translate((19.5,0,0))(so.cylinder(r=2, h=thickness+2)))
    shaft_hole = so.rotate((0,-90,0))(shaft_hole)
    servo_offset = 75
    servo_vertical_offset = 8
    servo_shaft_offset = 9.7
    gear_spacing = 50
    gear_angle = 0.75
    for offset in [servo_offset - gear_spacing * cos(gear_angle), 110, 155, 200]:
        body -= so.translate((thickness + 1, offset, servo_vertical_offset + servo_shaft_offset + gear_spacing * sin(gear_angle)))(shaft_hole)
    if not passive:
        body -= so.translate((-1, servo_offset, servo_vertical_offset))(servo_mount())
    if passive:
        body = so.mirror((1,0,0))(body)
    return body

# rods are 15.2mm diameter
big_hex_nut = hex(23.6, 9.7)

def roller():
    radius = 31.75/2
    ring = so.rotate_extrude(360)(so.translate((radius + 3.175/2,0))(so.circle(d=3.175)))
    return so.mirror((0,0,1))(so.cylinder(r=radius+3.175/2-0.8, h=13) - big_hex_nut - so.translate((0,0,6.5))(ring) - so.cylinder(r=15.2/2 + 0.1, h=13))

# space gears at the modul/2 * (tooth_number_1 + tooth_number_2)
# meshes when modules are the same and helix angles opposite
# these gears get a spacing of 40mm
def servo_gear():
    gear = gears.herringbone_gear(modul=1.0, tooth_number=25, width=11, bore=8, helix_angle=35)
    insert_hole = so.mirror((0,0,1))(so.translate((15/2.0, 0, -11))(screw_2_56_insert_hole))
    for a in [0,90,180,270]:
        gear -= so.rotate((0,0,a))(insert_hole)
    return gear

def shaft_gear():
    return gears.herringbone_gear(modul=1.0, tooth_number=75, width=11, bore=15.2, helix_angle=-35) + so.cylinder(h=10, r=15) - so.translate((0,0,11-9.68))(big_hex_nut) - so.cylinder(r=15.2/2.0,h=11)

scad = roller()
scad = big_hex_nut
scad = shaft_gear()
scad = servo_gear()
scad = servo_mount()
scad = basewall()
scad = basewall(passive=True)
scad = sidewall()
scad = sidewall_clamp()

SEGMENTS = 48
s.scad_render_to_file(scad, 'parts.scad', file_header=f'$fn = {SEGMENTS};')

# 4x rollers
# 2x sidewalls
# 4x bearings as configured, and then subtract the hex nut from the inner part in slicer for mating mount
# 2x basewall (just don't use one motor mount lol)

def render_stl(scad, stl):
    s.scad_render_to_file(scad, 'tmp.scad', file_header=f'$fn = {SEGMENTS};')
    print(f'rendering {stl}...', end='', flush=True)
    os.system(f'openscad -q -o {stl} tmp.scad')
    print(f'complete!')


if True:
    render_stl(sidewall_clamp(), '4x_sidewall_clamp.stl')
    render_stl(basewall(passive=True), '1x_basewall_passive.stl')
    #render_stl(roller(), '4x_roller.stl')
    #render_stl(big_hex_nut, 'COMBINE_WITH_BEARING_big_hex_nut.stl')
    #render_stl(sidewall(), '2x_sidewall.stl')
    #render_stl(basewall(), '1x_basewall.stl')
    #render_stl(shaft_gear(), '1x_shaft_gear.stl')
    #render_stl(servo_gear(), '1x_servo_gear.stl')
print('done')
