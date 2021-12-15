"""
blender --background blend/render_normalization_template.blend --python obj_render_background_blend.py -- -in {path_to_dir}

for quick start,we recommend that
blender --background blend/render_normalization_template.blend --python obj_render_background_blend.py -- -in {path_to_dir} --multiview
blender --background blend/render_normalization_square_hit_ground.blend --python obj_render_background_blend.py -- -in D:\your_folder -m NULL
if you want to define the render effects, you can use .blend file to solve all rendering and geometry postprocessing problems
tips for .blend config:First open render_normalization_template.blend by blender, and setup
    'Camera', 'Camera.001', 'Camera.002', 'Camera.003': we create the optimal view based on normalized chairs in shapenet dataset(bionic chair should also meets this points, or it will failed in functionality)
    light,
    mesh modifier: NEED TO CHANGE PYHTON SCRIPT ACCORDING TO .blender FILE, because if you delete geometry,the modifier will disappear
    render background,we use "courtyard.exr" file to provide complex light field environment for better visual effect
    shade material(bpy.data.materials["PreparedMaterial"])
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.append('..')
from util.argparse4blender import ArgumentParserForBlender


def scale_to_unit_sphere(obj):
    """
    normalize input mesh to [-1,1]^3 and (0,0,0) as centroid
    obj:bpy.context.object and also be bpy.data.mesh
    """
    # find max x,y,z and scale factor
    coords = obj.bound_box[:]
    rotated = zip(*coords[::-1])
    all_axis = []
    push_axis = []
    for (axis, _list) in zip('xyz', rotated):
        distance = max(_list) - min(_list)
        all_axis.append(distance)
        adjuster_distance = min(_list) + (distance / 2)
        push_axis.append(adjuster_distance * -1)
    print(all_axis)
    long_side = max(all_axis)
    scale = Vector((long_side, 0, 0)).length / 2.0
    bm = bmesh.from_edit_mesh(obj.data)
    for vertex in bm.verts:
        # center
        vertex.co.x += push_axis[0]
        vertex.co.y += push_axis[1]
        vertex.co.z += push_axis[2]
        # rescale to -1, 1 boundary
        vertex.co = vertex.co / scale
        # enable obj to stand above plane in (0,1,0) ps:y axis adown in blender
        # quantize
        # vertex.co.x = round(vertex.co.x, 1)
        # vertex.co.y = round(vertex.co.y, 1)
        # vertex.co.z = round(vertex.co.z, 1)
    bmesh.update_edit_mesh(obj.data)
    #enable obj to stand above plane, strange that bm axis is not the same as blender
    vertexz_list = [item.co.z for item in bm.verts]
    min_z = min(vertexz_list)
    for vertex in bm.verts:
        vertex.co.z = vertex.co.z - (min_z + 1)# plane is at z=-1
    bmesh.update_edit_mesh(obj.data)


def setup_camera(scene, c):
    pi = math.pi
    scene.camera.rotation_euler[0] = c[0] * (pi / 180.0)
    scene.camera.rotation_euler[1] = c[1] * (pi / 180.0)
    scene.camera.rotation_euler[2] = c[2] * (pi / 180.0)
    scene.camera.location.x = c[3]
    scene.camera.location.y = c[4]
    scene.camera.location.z = c[5]
    return


def find_import_mesh():
    pass


def obj_render(path_to_obj_dir, args):
    """
    create new rendered image based on camera_config
    :param blender_path: location of blender.exe
    :param path_to_obj_dir:Adjust this for where you have the OBJ files.
    :param camera_config:like list([159.723, 52.5244, 209.492, 144.764, 32.6978, -0.692726])
    """
    global scene, cam
    selected_object_name = None
    #clear
    for name, _ in bpy.data.objects.items():
        if name not in ['Camera', 'Light', 'Camera.001', 'Camera.002', 'Camera.003', 'Plane']:
            selected_object_name = name
            print('delete', selected_object_name)
            bpy.data.objects[str(selected_object_name)].select_set(True)
            bpy.ops.object.delete()
    if args.transparent_background:
        try:
            print("delete plane")
            bpy.data.objects['Plane'].select_set(True)
            bpy.ops.object.delete()
        except Exception as e:
            print(e)

    print(bpy.data.objects.items())

    file_list = sorted(os.listdir(path_to_obj_dir))
    obj_list = [item for item in file_list if item[-3:] in ['obj']]
    for item in obj_list:
        obj_basename = os.path.splitext(item)[0]
        if args.skip:
            check_path = os.path.join(path_to_obj_dir, obj_basename + ".png")
            if os.path.exists(check_path):
                print("skip path{}".format(check_path))
                continue
        path_to_file = os.path.join(path_to_obj_dir, item)
        bpy.ops.import_scene.obj(filepath=path_to_file)
        for name, _ in bpy.data.objects.items():
            if name not in ['Camera', 'Light', 'Camera.001', 'Camera.002', 'Camera.003', 'Plane']:
                selected_object_name = name
                print('select', selected_object_name)
                break
            else:
                selected_object_name = name
        # geometry postprocessing
        # bpy.data.objects[str(selected_object_name)].rotation_euler[0] = 3.14159#only in linux because of strange direction bias
        bpy.data.objects[str(selected_object_name)].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[str(selected_object_name)]
        bpy.ops.object.editmode_toggle()
        scale_to_unit_sphere(bpy.data.objects[str(selected_object_name)])
        bpy.ops.object.editmode_toggle()
        bpy.data.objects[str(selected_object_name)].modifiers.new(
            "Decimate", type="Decimate".upper())
        bpy.data.objects[str(selected_object_name)].modifiers.new(
            "Smooth", type="Smooth".upper())
        bpy.data.objects[str(selected_object_name)].modifiers["Decimate"].ratio = 0.6
        bpy.data.objects[str(selected_object_name)].modifiers["Smooth"].factor = 2.0
        bpy.data.objects[str(selected_object_name)].modifiers["Smooth"].iterations = 2
        # print(bpy.data.materials.values()) #debug for material disapper problem
        # print(bpy.data.objects.values())
        bpy.ops.object.shade_smooth()
        if args.material != "NULL":
            bpy.data.objects[str(selected_object_name)].active_material = bpy.data.materials[args.material]
        # render
        bpy.data.scenes['Scene'].render.resolution_x = args.resolution_x
        bpy.data.scenes['Scene'].render.resolution_y = args.resolution_y
        bpy.data.scenes['Scene'].render.film_transparent = args.transparent_background
        if args.slow:
            bpy.data.scenes['Scene'].render.engine ='CYCLES'
        else:
            bpy.data.scenes['Scene'].render.engine ='BLENDER_EEVEE'

        if args.multiview:
            for cam_select_name in ['Camera', 'Camera.001', 'Camera.002', 'Camera.003']:
                bpy.context.scene.camera = bpy.data.objects[str(cam_select_name)]
                if cam_select_name != 'Camera':
                    output_name = '{0}_view{1}.png'.format(obj_basename, cam_select_name.split('.')[-1])
                else:
                    output_name = obj_basename[0] + ".png"
                path_to_file2 = os.path.join(path_to_obj_dir, output_name)
                bpy.data.scenes['Scene'].render.filepath = path_to_file2

                bpy.ops.render.render(write_still=True)
                print(path_to_file2)
        else:
            cam_select_name = 'Camera'
            bpy.context.scene.camera = bpy.data.objects[str(cam_select_name)]
            output_name = obj_basename + ".png"
            path_to_file2 = os.path.join(path_to_obj_dir, output_name)
            bpy.data.scenes['Scene'].render.filepath = path_to_file2
            bpy.ops.render.render(write_still=True)

        bpy.context.scene.camera = bpy.data.objects['Camera']
        bpy.ops.object.delete()


if __name__ == '__main__':
    parser = ArgumentParserForBlender()
    parser.add_argument("-in", "--dir",
                        type=str, required=True,
                        help="Directory containing obj file")
    parser.add_argument("-sk", "--skip", action='store_false',
                        help="skip exist png file [default:true]")
    parser.add_argument("-sl", "--slow", action='store_true',
                        help="render engine selection: True for cycles, False for eevee [default:False]")
    parser.add_argument("-mv", "--multiview", action='store_true',
                        help="render view selection: True for 4view(4 camera is defined in .blend file), False for the first camera [default:False]")
    parser.add_argument("-tb", "--transparent_background", action='store_true',
                        help="whether to show background including shadow, background plane: True for transparent_background png export, False for all export [default:False]")
    parser.add_argument("-rx", "--resolution_x", type=int, default=480,
                        help="output images resolution of x[default:480]")
    parser.add_argument("-ry", "--resolution_y", type=int, default=480,
                        help="output images resolution of y[default:480]")
    materials_list = ["NULL",'LayeredGlass','PreparedMaterial','1970_tiles', 'Anodized', 'Basic Glass', 'Blaster Bolt (Blue)', 'Brushed Metal', 'Ceramic Polished', 'Chocolate Swirl', 'Composite Rubber', 'denmin_fabric', 'Fresnel', 'High Gloss Plastic', 'Jewelry', 'LayeredGlass', 'Lemon', 'Metallic Paint Clean', 'Molten', 'plywood', 'Material','Wire Musgrave', 'wood boards', 'WoodP']
    parser.add_argument("-m", "--material", type=str, default="Material",help="material used in blender[default:PreparedMaterial]")
    args = parser.parse_args()
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--path_to_obj_dir", type=str, default='/data/project/base/tf210/lty/deep3dbionic_v2/results/top10000',help="root directory to store results in")
    # args = parser.parse_args()

    # put the location to the folder where the objs are located here
    # path_to_obj_dir = os.path.join('D:\\', 'linux_project\DeepBionic\deep3dbionic_v2\\results\\render')
    # path_to_obj_dir = os.path.join('D:\\', 'linux_project\DeepBionic\implicit-decoder\IMGAN\\result\\batch_interp_likepre_add_5designed')
    # path_to_obj_dir = os.path.join('D:\\', 'linux_project\DeepBionic\deep3dbionic_v2\samples')
    # path_to_obj_dir = os.path.join('D:\\', 'linux_project\DeepBionic\deep3dbionic_v2\\result\interpolation_test')
    # path_to_obj_dir = '/workspace/3DDeepBionic/deepbionic/deep3dbionic/code/result/Reconstruction_64'
    # path_to_obj_dir = args.path_to_obj_dir
    # path_to_obj_dir ='/data/project/base/tf210/lty/deep3dbionic_v2/results/top10000' #in linux server

    # camera_config = list([159.723, 52.5244, 209.492, 144.764, 32.6978, -0.692726]) #dae 2020
    # camera_config = list([523.499, -26.3813, -0.913274, 105.962, -78.2096, -103.943])  # top10000 2021

    path_to_obj_dir = args.dir
    obj_render(path_to_obj_dir, args)

    # path_to_file="D:\linux_project\DeepBionic\deep3dbionic_v2\\results\\render\\analyze_objfunc_skiprank_0.obj"
    # path_to_file2="D:\linux_project\DeepBionic\deep3dbionic_v2\\results\\render\\testing.png"
    # #for

# path_to_obj_dir='D:\linux_project\DeepBionic\deep3dbionic_v2\\result\ORIGIN_64'
# global scene, cam
# selected_object_name = None
# for name, _ in bpy.data.objects.items():
#     if name not in ['Camera', 'Light', 'Camera.001', 'Camera.002', 'Camera.003', 'Plane']:
#         selected_object_name = name
#         print('delete', selected_object_name)
#         bpy.data.objects[str(selected_object_name)].select_set(True)
#         bpy.ops.object.delete()
#         break
#     else:
#         selected_object_name = name
#
# file_list = sorted(os.listdir(path_to_obj_dir))
# obj_list = [item for item in file_list if item[-3:] in ['obj']]
# for item in obj_list:
#     path_to_file = os.path.join(path_to_obj_dir, item)
#     bpy.ops.import_scene.obj(filepath=path_to_file)
#     obj_basename = os.path.splitext(item)
#     for name, _ in bpy.data.objects.items():
#         if name not in ['Camera', 'Light', 'Camera.001', 'Camera.002', 'Camera.003', 'Plane']:
#             selected_object_name = name
#             print('select', selected_object_name)
#             break
#         else:
#             selected_object_name = name
#
#     bpy.data.objects[str(selected_object_name)].select_set(True)
#     bpy.context.view_layer.objects.active = bpy.data.objects[str(selected_object_name)]
#     bpy.ops.object.editmode_toggle()
#     scale_to_unit_sphere(bpy.data.objects[str(selected_object_name)])
#     bpy.ops.object.editmode_toggle()
#     bpy.ops.object.shade_smooth()
#     bpy.data.objects[str(selected_object_name)].modifiers.new(
#         "Decimate", type="Decimate".upper())
#     bpy.data.objects[str(selected_object_name)].modifiers.new(
#         "Smooth", type="Smooth".upper())
#     bpy.data.objects[str(selected_object_name)].modifiers["Decimate"].ratio = 0.2
#     bpy.data.objects[str(selected_object_name)].modifiers["Smooth"].factor = 2.0
#     bpy.data.objects[str(selected_object_name)].modifiers["Smooth"].iterations = 2
#     print(bpy.data.materials.values())
#     print(bpy.data.objects.values())
#     bpy.data.objects[str(selected_object_name)].active_material = bpy.data.materials["PreparedMaterial"]
#     for cam_select_name in ['Camera', 'Camera.001', 'Camera.002', 'Camera.003']:
#         bpy.context.scene.camera = bpy.data.objects[str(cam_select_name)]
#         if cam_select_name != 'Camera':
#             output_name = '{0}_view{1}.png'.format(obj_basename[0], cam_select_name.split('.')[-1])
#         else:
#             output_name = obj_basename[0] + ".png"
#         path_to_file2 = os.path.join(path_to_obj_dir, output_name)
#         bpy.data.scenes['Scene'].render.filepath = path_to_file2
#         bpy.ops.render.render(write_still=True)
#         print(path_to_file2)
#
#     bpy.context.scene.camera = bpy.data.objects['Camera']
#     bpy.ops.object.delete()


# #debug scale_to_unit_sphere
# obj=bpy.data.objects[str(selected_object_name)]
# # find max x,y,z and scale factor
# coords = obj.bound_box[:]
# rotated = zip(*coords[::-1])
# all_axis = []
# push_axis = []
# for (axis, _list) in zip('xyz', rotated):
#     distance = max(_list) - min(_list)
#     all_axis.append(distance)
#     adjuster_distance = min(_list) + (distance / 2)
#     push_axis.append(adjuster_distance * -1)
# print(all_axis)
# long_side = max(all_axis)
# scale = Vector((long_side, 0, 0)).length / 2.0
# bm = bmesh.from_edit_mesh(obj.data)
# for vertex in bm.verts:
#     # center
#     vertex.co.x += push_axis[0]
#     vertex.co.y += push_axis[1]+10
#     vertex.co.z += push_axis[2]
#     # rescale to -1, 1 boundary
#     vertex.co = vertex.co / scale
#     # enable obj to stand above plane in (0,1,0) ps:y axis adown in blender
# bmesh.update_edit_mesh(obj.data)
# #enable obj to stand above plane, strange that bm axis is not the same as blender
# vertexz_list = [item.co.z for item in bm.verts]
# min_z = min(vertexz_list)
# for vertex in bm.verts:
#     vertex.co.z = vertex.co.z - (min_z + 1)# plane is at z=-1
# bmesh.update_edit_mesh(obj.data)