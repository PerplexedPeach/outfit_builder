bl_info = {
    "name"    : "Outfit Builder",
    "author"  : "LazyIcarus",
    "version" : (1, 4),
    "blender" : (3, 1, 0),
    "category": "Add Mesh",
    "location": "Object -> Build Outfits"
}
# exports each selected object into its own file
import bpy
import os
import uuid
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from copy import deepcopy


class BuildProperties(bpy.types.PropertyGroup):
    remove_shape_after_export: bpy.props.BoolProperty(name="Remove shapes after export", default=False)
    hide_shape_after_export: bpy.props.BoolProperty(name="Hide shapes after export", default=False)
    duplicate_instead_of_copy: bpy.props.BoolProperty(name="Duplicate instead of copy", default=True)
    export: bpy.props.BoolProperty(name="Export", default=True)
    output_dir: bpy.props.StringProperty(name="Output dir", default="", subtype="DIR_PATH")
    body: bpy.props.PointerProperty(name="Body Mesh", type=bpy.types.Object)
    # for auto building the LSX (XML format) file describing the exported meshes
    lsx: bpy.props.StringProperty(name="LSX in", default="", subtype="FILE_PATH")
    # for multi-object GR2 export (with different Export order)
    combine_export: bpy.props.BoolProperty(name="Combine before export", default=False)


class BuildPanel(bpy.types.Panel):
    bl_label = "Outfit Builder"
    bl_idname = "OBJECT_PT_properties_panel"
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
        layout.prop(build_props, "combine_export")
        layout.prop(build_props, "body")
        layout.prop(build_props, "output_dir")

        # button to actually build the outfit
        row = layout.row()
        build = row.operator(BuildOutfit.bl_idname)

        # # add subpanel for building LSX
        # layout.label(text="LSX Builder")


class BuildVisualBankPanel(bpy.types.Panel):
    bl_label = "VisualBank (LSX) Builder"
    bl_idname = "OBJECT_PT_visual_bank_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Outfit Builder"

    def draw(self, context):
        layout = self.layout

        # allow modifying the properties on the scene
        build_props = context.scene.outfit_builder
        layout.prop(build_props, "lsx")

        # button to actually build the outfit
        row = layout.row()
        build = row.operator(BuildVisualBank.bl_idname)


def get_body_and_armors_from_context(context, require_armor=True):
    build_props = context.scene.outfit_builder

    body = build_props.body
    print("selected body prop", build_props.body)

    selection = context.selected_objects
    # either body is given explicitly, or we use the first in the selection
    if body is not None:
        armors = selection
    else:
        if len(selection) > 0:
            body = selection[0]
        armors = selection[1:]

    print("selection", selection)
    if body is None:
        raise Exception("No body (object with shape keys) is specified")
    if require_armor and len(armors) == 0:
        raise Exception("No armor meshes are selected")

    return body, armors


def find_parent(root, element):
    for parent in root.iter():
        for child in parent:
            if child is element:
                return parent
    return None


def pretty_print_node(node_of_interest):
    raw_str = ET.tostring(node_of_interest, 'utf-8')
    reparsed = parseString(raw_str)
    pretty_str = reparsed.toprettyxml(indent="\t")
    pretty_str = '\n'.join([line for line in pretty_str.split('\n') if line.strip()])
    print(pretty_str)


def replace_node_attributes(shape, node, name, full_name):
    bs_name = shape.name
    print('Shape key ', bs_name)
    new_name = f"{name}_{bpy.path.clean_name(bs_name)}"
    print(f"New name: {new_name}")

    new_node = deepcopy(node)
    new_node.text = f" {new_name}\n\t\t\t\t\t"

    name_attribute = new_node.find('.//attribute[@id="Name"]')
    name_attribute.set('value', new_name)

    # Generate a new UUID and set it as 'ID' attribute
    new_id = str(uuid.uuid4())
    id_node = new_node.find('.//attribute[@id="ID"]')
    id_node.set('value', new_id)

    # get SourceFile and Template, and replace their full_name with name
    source_file_attribute = new_node.find('.//attribute[@id="SourceFile"]')
    source_file = source_file_attribute.get('value')
    source_file = source_file.replace(full_name, new_name)
    source_file_attribute.set('value', source_file)

    template_attribute = new_node.find('.//attribute[@id="Template"]')
    template = template_attribute.get('value')
    template = template.replace(full_name, new_name)
    template_attribute.set('value', template)

    # then do the same for .//children/node[@id="Objects"]/attribute[@id="ObjectID"] (find all)
    object_id_attributes = new_node.findall('.//children/node[@id="Objects"]/attribute[@id="ObjectID"]')
    for object_id_attribute in object_id_attributes:
        object_id = object_id_attribute.get('value')
        object_id = object_id.replace(full_name, new_name)
        object_id_attribute.set('value', object_id)

    return new_node


def replace_node_with_shapes(root, shapes, node):
    name_attribute = node.find('.//attribute[@id="Name"]')
    # Expects 2 conventions - either it finishes with Basis, or we assume it's the name without _Basis
    full_name = name_attribute.get('value')
    name = full_name.rstrip('_Basis')
    print(f"Name: {name}")

    # replace the old node with our new copies
    parent = find_parent(root, node)
    # Get the index of the old node in its parent
    index = list(parent).index(node)
    new_nodes = []

    # skip basis
    for i in range(1, len(shapes)):
        new_nodes.append(replace_node_attributes(shapes[i], node, name, full_name))

    parent.remove(node)
    for new_node in new_nodes:
        parent.insert(index, new_node)
        index += 1


class BuildVisualBank(bpy.types.Operator):
    """
    Given a LSX file of VisualBank information for the basis mesh, generate
    LSX VisualBank entries for each variant for each selected armor
    """
    bl_idname = "object.build_visual_bank"
    bl_label = "Build Visual Bank"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        build_props = context.scene.outfit_builder
        # defaults to current directory
        base_lsx = build_props.lsx
        if not os.path.exists(base_lsx):
            raise RuntimeError(f"LSX file {base_lsx} does not exist")
        if not base_lsx.endswith("lsf.lsx"):
            raise RuntimeError(f"LSX file {base_lsx} does not end with lsf.lsx")

        print("Parsing LSX file", base_lsx)
        tree = ET.parse(base_lsx)
        # navigate under region id="VisualBank" node id="VisualBank"
        root = tree.getroot()
        print(root)

        body, _ = get_body_and_armors_from_context(context, require_armor=False)

        shapes = body.data.shape_keys.key_blocks

        # expect the first shape key to be called Basis
        if shapes[0].name != "Basis":
            raise RuntimeError(f"Expect the first shape key to be called Basis, but instead got {shapes[0].name}")

        # Specify the path to the 'node' of interest
        path = './/region[@id="VisualBank"]/node[@id="VisualBank"]/children/node[@id="Resource"]'

        # Find the 'node' of interest
        nodes_to_replace = root.findall(path)

        # Check if the 'node' was found
        if nodes_to_replace is None or nodes_to_replace == []:
            raise RuntimeError(f"VisualBank nodes were not found in {base_lsx}")

        for node in nodes_to_replace:
            replace_node_with_shapes(root, shapes, node)

        # save to the base_lsx but with _generated attached at the end of its filename
        tree.write(base_lsx.replace(".lsf.lsx", "_generated.lsf.lsx"), encoding='utf-8', xml_declaration=True)

        return {'FINISHED'}


def do_transfer_shapes(body, armor, view_layer):
    armor.mesh_data_transfer_object.mesh_source = body
    armor.mesh_data_transfer_object.attributes_to_transfer = 'SHAPE_KEYS'
    armor.mesh_data_transfer_object.mesh_object_space = 'WORLD'
    # need to set the armor as the context for this operation
    view_layer.objects.active = armor
    armor.select_set(True)

    bpy.ops.object.transfer_mesh_data()

def common_prefix(strs):
    if not strs:
        return ""

    shortest = min(strs, key=len)

    for i, char in enumerate(shortest):
        for other in strs:
            if other[i] != char:
                return shortest[:i]
    return shortest

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

        body, armors = get_body_and_armors_from_context(context)
        shapes = body.data.shape_keys.key_blocks

        view_layer = context.view_layer

        for armor in armors:
            print("building ", armor.name)
            do_transfer_shapes(body, armor, view_layer)

        for i in range(len(shapes)):
            for ob in context.selected_objects:
                ob.select_set(False)

            if build_props.combine_export:
                self.do_export_combine(context, build_props, body, basedir, armors, shapes, i, view_layer)
            else:
                self.do_export_separate(context, build_props, body, basedir, armors, shapes, i, view_layer)

        return {'FINISHED'}

    def do_export_combine(self, context, build_props, body, basedir, armors, shapes, i, view_layer):
        for armor in armors:
            armor.select_set(True)
            view_layer.objects.active = armor

        bpy.ops.object.duplicate(linked=False)

        bs_name = shapes[i].name
        print('Shape key ', i, ' ', bs_name)

        new_armors = context.selected_objects
        # deselect everything then select one at a time
        for armor in new_armors:
            armor.select_set(False)
        
        names = []
        for armor in new_armors:
            armor.select_set(True)
            view_layer.objects.active = armor
            armor.active_shape_key_index = i
            armor.active_shape_key.value = 1

            armor_name = bpy.path.clean_name(armor.name)
            # use _ to indicate FS and other variants - this way they can have the same name apart from prefix
            armor_name = armor_name.rstrip("_001").strip("_")
            name = f"{body.name}_{armor_name}_{bpy.path.clean_name(bs_name)}"
            armor.name = name
            armor.data.name = name
            names.append(name)

            # apply shape key
            bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                
            armor.select_set(False)
        
        print(names)
        # use some heuristics for determining export file name
        # first find what the common prefix is
        fn = os.path.join(basedir, f"{common_prefix(names)}_{bpy.path.clean_name(bs_name)}")
        print(fn)

        # select everything again
        for armor in new_armors:
            armor.select_set(True)
        if build_props.export:
            bpy.ops.export_scene.dos2de_collada(filepath=fn + ".GR2", check_existing=False, filename_ext=".GR2",
                                                use_export_selected=True)
            self.report({'INFO'}, f"Saving to {fn}")
        else:
            self.report({'INFO'}, f"Just creating the variants")

        if build_props.remove_shape_after_export:
            bpy.ops.object.delete()
        else:
            for armor in new_armors:
                if build_props.hide_shape_after_export:
                    armor.hide_viewport = True
                armor.select_set(False)



    def do_export_separate(self, context, build_props, body, basedir, armors, shapes, i, view_layer):
        for armor in armors:
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

            bs_name = shapes[i].name
            print('Shape key ', i, ' ', bs_name)
            armor_name = bpy.path.clean_name(armor.name)
            # use _ to indicate FS and other variants - this way they can have the same name apart from prefix
            armor_name = armor_name.strip("_")
            name = f"{body.name}_{armor_name}_{bpy.path.clean_name(bs_name)}"
            armor_shape.name = name
            armor_shape.data.name = name

            # apply shape key
            bpy.ops.object.shape_key_remove(all=True, apply_mix=True)

            fn = os.path.join(basedir, name)
            print(fn)

            if build_props.export:
                bpy.ops.export_scene.dos2de_collada(filepath=fn + ".GR2", check_existing=False, filename_ext=".GR2",
                                                    use_export_selected=True)
                self.report({'INFO'}, f"Saving to {fn}")
            else:
                self.report({'INFO'}, f"Creating {name}")

            if build_props.remove_shape_after_export:
                bpy.ops.object.delete()
            else:
                if build_props.hide_shape_after_export:
                    armor_shape.hide_viewport = True
                armor_shape.select_set(False)


def menu_func(self, context):
    self.layout.operator(BuildOutfit.bl_idname)


addon_keymaps = []

classes = [BuildOutfit, BuildPanel, BuildProperties, BuildVisualBank, BuildVisualBankPanel]


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
