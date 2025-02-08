bl_info = {
    "name": "Animation Library",
    "author": "Your Name",
    "version": (1, 5),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Animation Tab",
    "description": "Animation library with thumbnail preview, blending, keyframe mixing, search, and deletion. Library path is editable per project.",
    "category": "Animation"
}

import bpy
import os
import re
from pathlib import Path
import time
from bpy.props import StringProperty, FloatProperty, BoolProperty, CollectionProperty
from bpy.types import Operator, Panel, PropertyGroup

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def get_library_path():
    """Returns the library path stored in the scene property."""
    return Path(bpy.path.abspath(bpy.context.scene.animation_library_path))

def refresh_ui():
    """Force redraw of all areas (to update the panel UI)."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()

def generate_thumbnail(action_name):
    """
    Render a low-res thumbnail image for the given action name.
    The thumbnail is saved in the library folder as <action_name>.png.
    """
    scene = bpy.context.scene
    render = scene.render

    # Save original render settings
    original_res = (render.resolution_x, render.resolution_y)
    original_engine = render.engine
    original_filepath = render.filepath

    # Set thumbnail render settings
    render.resolution_x, render.resolution_y = 128, 128
    render.engine = 'BLENDER_EEVEE_NEXT'
    thumb_path = get_library_path() / f"{action_name}.png"
    render.filepath = str(thumb_path)

    bpy.ops.render.render(write_still=True)

    # Restore original render settings
    render.resolution_x, render.resolution_y = original_res
    render.engine = original_engine
    render.filepath = original_filepath

    return thumb_path

def paste_action_into_target(source_action, target_action, playhead, blend_strength):
    """
    Paste keyframes from source_action into target_action so that the first keyframe of
    source_action snaps to the timeline playhead. All keyframes are shifted accordingly.
    If a keyframe exists at the target frame, its value is blended using blend_strength.
    """
    first_time = None
    for fcurve in source_action.fcurves:
        for kf in fcurve.keyframe_points:
            if first_time is None or kf.co.x < first_time:
                first_time = kf.co.x
    if first_time is None:
        first_time = 0
    offset = playhead - first_time

    tolerance = 0.01
    for source_fcurve in source_action.fcurves:
        target_fcurve = target_action.fcurves.find(source_fcurve.data_path, index=source_fcurve.array_index)
        if target_fcurve is None:
            target_fcurve = target_action.fcurves.new(data_path=source_fcurve.data_path, index=source_fcurve.array_index)
        for kf in source_fcurve.keyframe_points:
            new_frame = kf.co.x + offset
            source_val = kf.co.y
            found = False
            for target_kf in target_fcurve.keyframe_points:
                if abs(target_kf.co.x - new_frame) < tolerance:
                    blended_val = target_kf.co.y * (1 - blend_strength) + source_val * blend_strength
                    target_kf.co.y = blended_val
                    found = True
                    break
            if not found:
                inserted_kf = target_fcurve.keyframe_points.insert(frame=new_frame, value=source_val * blend_strength, options={'FAST'})
                inserted_kf.interpolation = kf.interpolation
        target_fcurve.update()

def filter_action(original_action):
    """
    Create and return a new action containing either:
      - In Pose Mode: all keyframes (entire channels) for fcurves corresponding to the selected bones.
      - In Object Mode: all keyframes from all channels.
    """
    new_action = bpy.data.actions.new(name=original_action.name + "_filtered")
    mode = bpy.context.mode
    if mode == 'POSE':
        selected_bones = {bone.name for bone in bpy.context.selected_pose_bones}
        for fcurve in original_action.fcurves:
            copy_this = True
            if "pose.bones" in fcurve.data_path:
                m = re.search(r'pose\.bones\["([^"]+)"\]', fcurve.data_path)
                bone_name = m.group(1) if m else ""
                if bone_name not in selected_bones:
                    copy_this = False
            if copy_this:
                new_fcurve = new_action.fcurves.new(data_path=fcurve.data_path, index=fcurve.array_index)
                for kf in fcurve.keyframe_points:
                    new_kf = new_fcurve.keyframe_points.insert(frame=kf.co.x, value=kf.co.y)
                    new_kf.interpolation = kf.interpolation
                new_fcurve.update()
    else:
        # Object mode: copy all fcurves.
        for fcurve in original_action.fcurves:
            new_fcurve = new_action.fcurves.new(data_path=fcurve.data_path, index=fcurve.array_index)
            for kf in fcurve.keyframe_points:
                new_kf = new_fcurve.keyframe_points.insert(frame=kf.co.x, value=kf.co.y)
                new_kf.interpolation = kf.interpolation
            new_fcurve.update()
    return new_action

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
class AnimationEntry(PropertyGroup):
    name: StringProperty()
    filepath: StringProperty()
    is_favorite: BoolProperty(default=False)

# ---------------------------------------------------------------------------
# Dummy Operators for Missing Functions (Preview/Bulk Thumbs)
# ---------------------------------------------------------------------------
class ANIM_OT_PreviewAnimation(Operator):
    bl_idname = "animlib.preview_animation"
    bl_label = "Preview Animation"
    
    def execute(self, context):
        self.report({'INFO'}, "Preview Animation not implemented yet")
        return {'FINISHED'}

class ANIM_OT_BatchThumbnails(Operator):
    bl_idname = "animlib.batch_thumbnails"
    bl_label = "Generate Batch Thumbnails"
    
    def execute(self, context):
        self.report({'INFO'}, "Batch Thumbnails not implemented yet")
        return {'FINISHED'}

# ---------------------------------------------------------------------------
# Delete Operator
# ---------------------------------------------------------------------------
class ANIM_OT_DeleteAnimation(Operator):
    bl_idname = "animlib.delete_animation"
    bl_label = "Delete Animation"

    filepath: StringProperty()
    animation_name: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Warning: You are about to delete '{self.animation_name}' from the computer.")
    
    def execute(self, context):
        try:
            blend_file = Path(self.filepath)
            if blend_file.exists():
                blend_file.unlink()
            preview_file = blend_file.with_suffix('.png')
            if preview_file.exists():
                preview_file.unlink()
            refresh_ui()
            self.report({'INFO'}, f"Deleted animation: {self.animation_name}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error deleting animation: {str(e)}")
            return {'CANCELLED'}

# ---------------------------------------------------------------------------
# UI Panel
# ---------------------------------------------------------------------------
class ANIM_PT_MainPanel(Panel):
    bl_label = "Animation Library"
    bl_idname = "ANIM_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='LIBRARY_DATA_DIRECT')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        library_path = get_library_path()

        # Main Container
        main = layout.box()

        # ░█ LIBRARY MANAGEMENT
        header = main.box()
        row = header.row(align=True)
        row.label(text="Library Management", icon='FILEBROWSER')
        row.operator("animlib.reload_library", text="", icon='FILE_REFRESH')

        # Path Selector
        col = main.column(align=True)
        col.prop(scene, "animation_library_path", text="Folder", icon='FILE_FOLDER')
        col.separator(factor=0.5)

        # ░█ SAVE NEW ANIMATION (Name + Save Button)
        save_box = main.box()
        save_box.label(text="Save New Animation", icon='ADD')
        save_box.prop(scene, "new_animation_name", text="Name")
        save_box.operator("animlib.save_animation", text="Save Animation", icon='DOCUMENTS')

        # ░█ SETTINGS
        settings_box = main.box()
        settings_box.label(text="Settings", icon='PREFERENCES')
        settings_box.prop(scene, "blend_strength", text="Blend Strength", slider=True)

        # ░█ ANIMATION BROWSER (with Search)
        browser = main.box()
        browser.label(text="Animation Browser", icon='ACTION')
        browser.prop(scene, "animation_search_query", text="Search Animations")
        flow = browser.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True)
        if library_path.exists():
            for filepath in sorted(library_path.glob('*.blend')):
                query = scene.animation_search_query.lower().strip()
                if query and query not in filepath.stem.lower():
                    continue

                card = flow.box()
                card.scale_y = 1.2

                # Thumbnail Header
                header = card.box()
                row = header.row(align=True)
                row.label(text=filepath.stem, icon='FILE_BLEND')
                row.prop(scene, "is_favorite", text="", icon_only=True,
                         icon='SOLO_ON' if scene.is_favorite else 'SOLO_OFF')

                # Thumbnail Body
                thumb_path = filepath.with_suffix('.png')
                if thumb_path.exists():
                    img = bpy.data.images.get(thumb_path.name) or bpy.data.images.load(str(thumb_path), check_existing=True)
                    img.reload()
                    row.template_preview(img, show_buttons=False)
                else:
                    row.label(text="No Preview", icon='ERROR')

                # Context Menu: Apply and Delete (as Icons in the same row)
                row = card.row(align=True)
                op_apply = row.operator("animlib.apply_animation", text="", icon='IMPORT')
                op_apply.filepath = str(filepath)
                op_apply.animation_name = filepath.stem
                op_delete = row.operator("animlib.delete_animation", text="", icon='TRASH')
                op_delete.filepath = str(filepath)
                op_delete.animation_name = filepath.stem
        else:
            browser.label(text="No animations found", icon='INFO')

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------
class ANIM_OT_SaveAnimation(Operator):
    bl_idname = "animlib.save_animation"
    bl_label = "Overwrite existing animation?"
    
    def invoke(self, context, event):
        name = context.scene.new_animation_name.strip()
        if name:
            library_path = get_library_path()
            anim_file = library_path / f"{name}.blend"
            if anim_file.exists():
                return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Overwrite existing animation?")
    
    def execute(self, context):
        try:
            # Force update: set frame and update view layer.
            scene = context.scene
            scene.frame_set(scene.frame_current)
            bpy.context.view_layer.update()

            obj = context.active_object
            if not obj or not obj.animation_data or not obj.animation_data.action:
                self.report({'ERROR'}, "No active animation to save")
                return {'CANCELLED'}
            name = context.scene.new_animation_name.strip()
            if not name:
                self.report({'ERROR'}, "Please provide a name for the animation")
                return {'CANCELLED'}
            library_path = get_library_path()
            library_path.mkdir(parents=True, exist_ok=True)
            anim_file = library_path / f"{name}.blend"

            # Purge any cached action with the same name.
            existing_action = bpy.data.actions.get(name)
            if existing_action is not None:
                bpy.data.actions.remove(existing_action, do_unlink=True)

            # Get evaluated (current) animation.
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            if not eval_obj.animation_data:
                self.report({'ERROR'}, "Evaluated animation data missing")
                return {'CANCELLED'}
            original_action = eval_obj.animation_data.action

            # Filter the action based on selection:
            # In Pose mode, export only selected bones; otherwise, export entire action.
            mode = bpy.context.mode
            if mode == 'POSE':
                selected_bones = {bone.name for bone in bpy.context.selected_pose_bones}
                if selected_bones:
                    filtered_action = filter_action(original_action)
                    export_msg = "Exported animation for selected bones."
                else:
                    filtered_action = original_action.copy()
                    export_msg = "Exported animation for all bones of the active object."
            else:
                filtered_action = original_action.copy()
                export_msg = "Exported animation for all bones of the selected object."

            filtered_action.name = name

            bpy.data.libraries.write(
                str(anim_file),
                {filtered_action},
                fake_user=True
            )
            generate_thumbnail(name)
            context.scene.new_animation_name = ""
            refresh_ui()
            self.report({'INFO'}, f"{export_msg} Saved to {anim_file}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error saving animation: {str(e)}")
            return {'CANCELLED'}

class ANIM_OT_ApplyAnimation(Operator):
    bl_idname = "animlib.apply_animation"
    bl_label = "Apply Animation"
    
    filepath: StringProperty()
    animation_name: StringProperty()
    
    def execute(self, context):
        try:
            with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
                data_to.actions = [name for name in data_from.actions]
            loaded_action = None
            for act in bpy.data.actions:
                if act.name.startswith(self.animation_name):
                    loaded_action = act
                    break
            if not loaded_action:
                self.report({'ERROR'}, "Could not find animation in the appended file")
                return {'CANCELLED'}
            obj = context.active_object
            if not obj:
                self.report({'ERROR'}, "No active object")
                return {'CANCELLED'}
            if not obj.animation_data:
                obj.animation_data_create()
            playhead = context.scene.frame_current
            blend_strength = context.scene.blend_strength
            if not obj.animation_data.action:
                obj.animation_data.action = loaded_action
            else:
                target_action = obj.animation_data.action
                paste_action_into_target(loaded_action, target_action, playhead, blend_strength)
            self.report({'INFO'}, f"Applied animation: {loaded_action.name} at playhead {playhead} with blend {round(blend_strength, 2)}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error applying animation: {str(e)}")
            return {'CANCELLED'}

class ANIM_OT_ReloadLibrary(Operator):
    bl_idname = "animlib.reload_library"
    bl_label = "Reload Library"
    
    def execute(self, context):
        refresh_ui()
        self.report({'INFO'}, "Library reloaded")
        return {'FINISHED'}

# ---------------------------------------------------------------------------
# New Properties (Project-Specific)
# ---------------------------------------------------------------------------
bpy.types.Scene.new_animation_name = StringProperty(
    name="Animation Name",
    description="Enter a name for the animation"
)
bpy.types.Scene.blend_strength = FloatProperty(
    name="Blend Strength",
    description="Set the blend strength when applying an animation (0.0 = none, 1.0 = full)",
    default=1.0,
    min=0.0,
    max=1.0
)
bpy.types.Scene.animation_library_path = StringProperty(
    name="Library Path",
    subtype='DIR_PATH',
    description="Folder where animations will be saved",
    default="//AnimationLibrary/"
)
bpy.types.Scene.animation_search_query = StringProperty(
    name="Search Animations",
    description="Search animations by name",
    default=""
)
bpy.types.Scene.is_favorite = BoolProperty(
    name="Favorite",
    description="Mark as favorite animation",
    default=False
)
bpy.types.Scene.ui_scale = FloatProperty(
    name="UI Scale",
    description="Adjust the interface scale",
    default=1.0,
    min=0.8,
    max=1.5,
    step=0.1
)

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
classes = (
    AnimationEntry,
    ANIM_PT_MainPanel,
    ANIM_OT_SaveAnimation,
    ANIM_OT_ApplyAnimation,
    ANIM_OT_ReloadLibrary,
    ANIM_OT_DeleteAnimation,
    ANIM_OT_PreviewAnimation,
    ANIM_OT_BatchThumbnails
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.new_animation_name
    del bpy.types.Scene.blend_strength
    del bpy.types.Scene.animation_library_path
    del bpy.types.Scene.animation_search_query
    del bpy.types.Scene.is_favorite
    del bpy.types.Scene.ui_scale

if __name__ == "__main__":
    register()
