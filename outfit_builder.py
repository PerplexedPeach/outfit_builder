bl_info = {
    "name": "Outfit Builder",
    "blender": (3, 1, 0),
    "category": "Object",
}
# exports each selected object into its own file
import bpy
import os



# TODO get filepath as an option
# export to blend file location

class BuildOutfit(bpy.types.Operator):
    """
    Given a body and its variants as shape keys, for each selected armor generate
    a variant for each blend shape.
    
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
    
    remove_shape_after_export: bpy.props.BoolProperty(name="Remove shapes after export", default=False)
    duplicate_instead_of_copy: bpy.props.BoolProperty(name="Duplicate instead of copy", default=True)
    
    def execute(self, context):
        basedir = os.path.dirname(bpy.data.filepath)
        
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

        #    bpy.ops.object.select_all(action='DESELECT')

            armor_shapes = armor.data.shape_keys.key_blocks
            shape_keys_ind = range(1, len(armor_shapes))

            for ob in context.selected_objects:
                ob.select_set(False)
                
            for i in shape_keys_ind:
                armor.select_set(True)
                view_layer.objects.active = armor

                if self.duplicate_instead_of_copy:
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
                
                # apply shape key
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                
                fn = os.path.join(basedir, name)
                # TODO export to file
                # bpy.ops.io_pdx_mesh.export_mesh(filepath=(fn + f'_{bs_name}' + ".mesh"), chk_skel=False, chk_mesh_blendshape=True, chk_locs=False, chk_selected=True)

                
                if self.remove_shape_after_export:
                    bpy.ops.object.delete()
                else:
                    armor_shape.select_set(False)
            
            self.report({'INFO'}, f"Finished building {armor.name}")
            
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(BuildOutfit.bl_idname)
        
def register():
    bpy.utils.register_class(BuildOutfit)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(BuildOutfit)
    
if __name__ == "__main__":
    register()
