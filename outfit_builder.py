bl_info = {
    "name": "Outfit Builder",
    "author": "LazyIcarus",
    "version" : (1, 0),
    "blender": (3, 1, 0),
    "category": "Add Mesh",
    "location": "Object -> Build Outfits"
}
# exports each selected object into its own file
import bpy
import os
import time


class BuildProperties(bpy.types.PropertyGroup):
    remove_shape_after_export: bpy.props.BoolProperty(name="Remove shapes after export", default=False)
    hide_shape_after_export: bpy.props.BoolProperty(name="Hide shapes after export", default=False)
    duplicate_instead_of_copy: bpy.props.BoolProperty(name="Duplicate instead of copy", default=True)
    export: bpy.props.BoolProperty(name="Export", default=True)
    output_dir: bpy.props.StringProperty(name="Output dir", default="", subtype="DIR_PATH")
    
class BuildPanel(bpy.types.Panel):
    bl_label = "Outfit Builder"
    bl_idname = "OB_properties_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Outfit Builder"

    
    def draw(self, context):
        layout = self.layout
        
        # allow modifying the properties on the scene
        build_props = context.scene.outfit_builder
        layout.prop(build_props, "export")
        layout.prop(build_props, "hide_shape_after_export")
        layout.prop(build_props, "remove_shape_after_export")
        layout.prop(build_props, "output_dir")
        
        # button to actually build the outfit
        row = layout.row()
        build = row.operator(BuildOutfit.bl_idname)
        

class BuildOutfit(bpy.types.Operator):
    """
    Given a body and its variants as shape keys, for each selected armor generate
    a variant for each shape key.
    
    Requirements
     base body mesh (e.g. HUM_F) with body variants defined as Shape Keys on them
     armor piece defined to fit the base body mesh
    
    Usage
     shift select body then the armor piece
     press the run script button (right arrow at the top of this bar)
    """
    bl_idname = "object.build_outfit"
    bl_label = "Build Outfits"
    bl_options = {'REGISTER', 'UNDO'}
    

    def execute(self, context):
        build_props = context.scene.outfit_builder
        # defaults to current directory
        basedir = build_props.output_dir or os.path.dirname(bpy.data.filepath)
        
        context.scene.ls_properties.game = 'bg3'
        
        selection = context.selected_objects
        if len(selection) < 2:
            raise Exception("Need to select the body first then at least one armor mesh")
            
        body = selection[0]
        view_layer = context.view_layer

        for armor in selection[1:]:
            print("building ", armor.name)
            
            armor.mesh_data_transfer_object.mesh_source = body
            armor.mesh_data_transfer_object.attributes_to_transfer = 'SHAPE_KEYS'
            armor.mesh_data_transfer_object.mesh_object_space = 'WORLD'
            # need to set the armor as the context for this operation
            view_layer.objects.active = armor
            armor.select_set(True)

            bpy.ops.object.transfer_mesh_data()


            armor_shapes = armor.data.shape_keys.key_blocks
            shape_keys_ind = range(0, len(armor_shapes))

            for ob in context.selected_objects:
                ob.select_set(False)
                
            for i in shape_keys_ind:
                armor.select_set(True)
                view_layer.objects.active = armor

                if build_props.duplicate_instead_of_copy:
                    bpy.ops.object.duplicate(linked=False)
                    armor_shape = context.active_object
                else:
                    armor_shape = armor.copy()
                    armor_shape.data = armor.data.copy()
                    context.collection.objects.link(armor_shape)
                    
                armor_shape.active_shape_key_index = i
                armor_shape.active_shape_key.value = 1
                
                bs_name = armor_shapes[i].name
                print('Shape key ', i, ' ', bs_name)
                name = f"{body.name}_{bpy.path.clean_name(armor.name)}_{bpy.path.clean_name(bs_name)}"
                armor_shape.name = name
                armor_shape.data.name = name
                
                # apply shape key
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                
                fn = os.path.join(basedir, name)
                print(fn)
                
                if build_props.export:
                    bpy.ops.export_scene.dos2de_collada(filepath=fn + ".GR2", check_existing=False, filename_ext=".GR2", use_export_selected=True)
                    self.report({'INFO'}, f"Saving to {fn}")
                    time.sleep(0.4)
                else:
                    self.report({'INFO'}, f"Creating name")

                if build_props.remove_shape_after_export:
                    bpy.ops.object.delete()
                else:
                    if build_props.hide_shape_after_export:
                        armor_shape.hide_viewport = True
                    armor_shape.select_set(False)
            
            self.report({'INFO'}, f"Finished building {armor.name}")
            
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(BuildOutfit.bl_idname)
        
addon_keymaps = []

classes = [BuildOutfit, BuildPanel, BuildProperties]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.Scene.outfit_builder = bpy.props.PointerProperty(type=BuildProperties)
    
    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
    
    kmi = km.keymap_items.new(BuildOutfit.bl_idname, 'B', 'PRESS', ctrl=True, shift=True)
    
    addon_keymaps.append((km, kmi))
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.outfit_builder

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
if __name__ == "__main__":
    register()
