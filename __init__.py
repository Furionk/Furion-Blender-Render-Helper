"""
Furion Render Helper - Frame rendering with multi-channel output

This extension provides tools for batch rendering specific frames with advanced features:
- Batch frame rendering with flexible input (individual frames and ranges)
- Multi-channel render pass output (Combined, Depth, Mist, Normal, etc.)
- Smart keyframe detection across all animated objects
- Customizable filename patterns with date/time and (Channel) tokens
- Persistent output folder and filename pattern preferences
- Real-time progress tracking with cancellation support
"""

bl_info = {
    "name": "Furion Render Helper",
    "author": "Furion Mashiou",
    "version": (1, 4, 2),
    "blender": (4, 0, 0),
    "location": "Properties > Render Properties > Furion Render Helper",
    "description": "Advanced frame rendering with multi-channel output and customizable filename patterns",
    "doc_url": "https://github.com/furion-mashiou/furion-render-helper",
    "tracker_url": "https://github.com/furion-mashiou/furion-render-helper/issues",
    "category": "Render",
}

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Panel, AddonPreferences
import os
import json
import sys

# Global variables to store user preferences
output_folder_path = ""
filename_pattern = "(FileName)_(Camera)_frame_(Frame)"


def get_active_3d_view():
    """Get the currently active 3D viewport space"""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return space
    return None


# Add-on Preferences Class
class FurionRenderHelperPreferences(AddonPreferences):
    """Preferences for Furion Render Helper"""
    bl_idname = __name__
    
    output_path_source: EnumProperty(
        name="Output Path Source",
        description="Choose where to read the output folder path from",
        items=[
            ('USER_PREFS', "User Preferences", "Read from user preferences JSON file (global, persistent across projects)"),
            ('SCENE_PROPS', "Scene Properties", "Read from current scene's custom properties (per-project settings, default)"),
        ],
        default='SCENE_PROPS',
        update=lambda self, context: load_output_folder_from_source(context)
    )
    
    enable_camera_helpers: BoolProperty(
        name="Enable Camera Helper Functions",
        description="Enable additional camera helper functions in context menus",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Output Folder Path Storage:", icon='FOLDER_REDIRECT')
        box.prop(self, "output_path_source", expand=True)
        
        # Information about each option
        layout.separator()
        info_box = layout.box()
        info_box.label(text="ℹ️ Information:", icon='INFO')
        
        col = info_box.column(align=True)
        col.label(text="• User Preferences: Global setting saved in Blender's config folder")
        col.label(text="  Same output folder across all blend files")
        col.label(text="")
        col.label(text="• Scene Properties: Per-project setting stored in blend file")
        col.label(text="  Different output folder for each blend file")
        
        # Camera Helper Functions
        layout.separator()
        camera_box = layout.box()
        camera_box.label(text="Camera Helper Functions:", icon='OUTLINER_OB_CAMERA')
        camera_box.prop(self, "enable_camera_helpers", text="Enable Camera Helpers")
        
        if self.enable_camera_helpers:
            info_col = camera_box.column(align=True)
            info_col.label(text="Adds DOF Distance picker to camera context menu", icon='INFO')
        
        # Show current settings
        layout.separator()
        current_box = layout.box()
        current_box.label(text="Current Settings:", icon='SETTINGS')
        
        global output_folder_path, filename_pattern
        col = current_box.column(align=True)
        if output_folder_path:
            col.label(text=f"Output folder: {output_folder_path}", icon='FOLDER_REDIRECT')
        else:
            col.label(text="Output folder: (Blend file directory)", icon='FOLDER_REDIRECT')
        col.label(text=f"Filename pattern: {filename_pattern}", icon='FILE_TEXT')

# Path to store user preferences
def get_preferences_file():
    """Get the path to the preferences file in Blender's user data folder"""
    user_data_dir = bpy.utils.user_resource('CONFIG')
    return os.path.join(user_data_dir, 'render_specific_frames_prefs.json')


def get_addon_preferences():
    """Get the addon preferences"""
    try:
        return bpy.context.preferences.addons[__name__].preferences
    except:
        return None


def get_output_path_source():
    """Get the current output path source setting"""
    prefs = get_addon_preferences()
    if prefs:
        return prefs.output_path_source
    return 'SCENE_PROPS'  # Default


def load_output_folder_from_scene(scene=None):
    """Load output folder from scene custom properties"""
    global output_folder_path
    
    if scene is None:
        try:
            scene = bpy.context.scene
        except:
            return
    
    if "frh_output_folder" in scene:
        saved_folder = scene["frh_output_folder"]
        if saved_folder and os.path.exists(saved_folder):
            output_folder_path = saved_folder
            print(f"Loaded output folder from scene: {output_folder_path}")
        else:
            output_folder_path = ""
            print("Scene output folder no longer exists or is empty")
    else:
        output_folder_path = ""
        print("No output folder stored in scene properties")


def save_output_folder_to_scene(scene=None):
    """Save output folder to scene custom properties"""
    global output_folder_path
    
    if scene is None:
        try:
            scene = bpy.context.scene
        except:
            return
    
    scene["frh_output_folder"] = output_folder_path
    print(f"Saved output folder to scene: {output_folder_path}")


def load_filename_pattern_from_scene(scene=None):
    """Load filename pattern from scene custom properties"""
    global filename_pattern
    
    if scene is None:
        try:
            scene = bpy.context.scene
        except:
            return
    
    if "frh_filename_pattern" in scene:
        saved_pattern = scene["frh_filename_pattern"]
        if saved_pattern:
            filename_pattern = saved_pattern
            print(f"Loaded filename pattern from scene: {filename_pattern}")
        else:
            filename_pattern = "(FileName)_(Camera)_frame_(Frame)"
    else:
        filename_pattern = "(FileName)_(Camera)_frame_(Frame)"
        print("No filename pattern stored in scene properties")


def save_filename_pattern_to_scene(scene=None):
    """Save filename pattern to scene custom properties"""
    global filename_pattern
    
    if scene is None:
        try:
            scene = bpy.context.scene
        except:
            return
    
    scene["frh_filename_pattern"] = filename_pattern
    print(f"Saved filename pattern to scene: {filename_pattern}")


def load_filename_pattern_from_user_prefs():
    """Load filename pattern from user preferences JSON file"""
    global filename_pattern
    prefs_file = get_preferences_file()
    try:
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                prefs = json.load(f)
                if 'filename_pattern' in prefs:
                    filename_pattern = prefs['filename_pattern']
                    print(f"Loaded filename pattern from user prefs: {filename_pattern}")
                else:
                    filename_pattern = "(FileName)_(Camera)_frame_(Frame)"
        else:
            filename_pattern = "(FileName)_(Camera)_frame_(Frame)"
    except Exception as e:
        print(f"Could not load filename pattern from user preferences: {e}")
        filename_pattern = "(FileName)_(Camera)_frame_(Frame)"


def load_filename_pattern_from_source(context=None):
    """Load filename pattern based on the current source setting"""
    source = get_output_path_source()
    
    if source == 'SCENE_PROPS':
        scene = context.scene if context else bpy.context.scene
        load_filename_pattern_from_scene(scene)
    else:  # USER_PREFS
        load_filename_pattern_from_user_prefs()


def load_output_folder_from_user_prefs():
    """Load output folder from user preferences JSON file"""
    global output_folder_path
    prefs_file = get_preferences_file()
    try:
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                prefs = json.load(f)
                saved_folder = prefs.get('default_output_folder', '')
                if saved_folder and os.path.exists(saved_folder):
                    output_folder_path = saved_folder
                    print(f"Loaded output folder from user preferences: {output_folder_path}")
                else:
                    output_folder_path = ""
                    print("Saved output folder no longer exists, using default")
        else:
            output_folder_path = ""
    except Exception as e:
        print(f"Could not load output folder from user preferences: {e}")
        output_folder_path = ""


def load_output_folder_from_source(context=None):
    """Load output folder and filename pattern based on the current source setting"""
    source = get_output_path_source()
    
    if source == 'SCENE_PROPS':
        scene = context.scene if context else bpy.context.scene
        load_output_folder_from_scene(scene)
        load_filename_pattern_from_scene(scene)
    else:  # USER_PREFS
        load_output_folder_from_user_prefs()
        load_filename_pattern_from_user_prefs()


def load_user_preferences():
    """Load user preferences including output folder and filename pattern"""
    global output_folder_path, filename_pattern
    prefs_file = get_preferences_file()
    try:
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                prefs = json.load(f)
                
                # Load filename pattern (always from user prefs)
                saved_pattern = prefs.get('filename_pattern', '')
                if saved_pattern:
                    filename_pattern = saved_pattern
                    print(f"Loaded filename pattern: {filename_pattern}")
                else:
                    print("Using default filename pattern")
                
                # Load output folder based on source setting
                load_output_folder_from_source()
    except Exception as e:
        print(f"Could not load preferences: {e}")

def load_default_output_folder():
    """Legacy function - now handled by load_user_preferences"""
    load_user_preferences()

def save_user_preferences():
    """Save user preferences including output folder and filename pattern"""
    global output_folder_path, filename_pattern
    prefs_file = get_preferences_file()
    try:
        # Ensure the config directory exists
        os.makedirs(os.path.dirname(prefs_file), exist_ok=True)
        
        # Load existing preferences or create new ones
        prefs = {}
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                prefs = json.load(f)
        
        # Update output folder and filename pattern based on source setting
        source = get_output_path_source()
        if source == 'USER_PREFS':
            # Save both to user preferences JSON
            prefs['default_output_folder'] = output_folder_path
            prefs['filename_pattern'] = filename_pattern
            print(f"Saving to user prefs - folder: {output_folder_path}, pattern: {filename_pattern}")
        else:  # SCENE_PROPS
            # Save to scene custom properties
            save_output_folder_to_scene()
            save_filename_pattern_to_scene()
            print(f"Saving to scene props - folder: {output_folder_path}, pattern: {filename_pattern}")
        
        # Save preferences file
        with open(prefs_file, 'w') as f:
            json.dump(prefs, f, indent=2)
        
        print(f"Saved preferences")
    except Exception as e:
        print(f"Could not save preferences: {e}")

def save_default_output_folder():
    """Legacy function - now handled by save_user_preferences"""
    save_user_preferences()

# Load user preferences on script load
load_user_preferences()


# Handler for when a blend file is loaded
@bpy.app.handlers.persistent
def on_file_load(dummy):
    """Handler called when a blend file is loaded"""
    # Reload output folder and filename pattern based on current source setting
    load_output_folder_from_source()


def validate_channel_pattern(pattern, has_multiple_channels):
    """
    Validate if the filename pattern is compatible with multi-channel rendering
    Returns (is_valid, error_message)
    """
    has_channel_token = "(Channel)" in pattern
    
    if has_multiple_channels and not has_channel_token:
        return False, "Pattern must include (Channel) token when multiple render passes are selected"
    
    return True, ""


def get_selected_channels(scene):
    """Get list of enabled render channels/passes from Blender's view layer settings"""
    channels = []
    
    # Get the first view layer (most common case)
    view_layer = None
    if scene.view_layers:
        view_layer = scene.view_layers[0]
    
    # If no view layer found, return Combined as fallback
    if not view_layer:
        return [('Combined', 'Combined')]
    
    # Always include Combined pass (it's always available)
    channels.append(('Combined', 'Combined'))
    
    # Check which passes are enabled in Blender's view layer settings
    if view_layer.use_pass_z:
        channels.append(('Depth', 'Depth'))
    
    if view_layer.use_pass_mist:
        channels.append(('Mist', 'Mist'))
    
    if view_layer.use_pass_normal:
        channels.append(('Normal', 'Normal'))
    
    if view_layer.use_pass_diffuse_direct:
        channels.append(('DiffuseDir', 'DiffuseDir'))
    
    if view_layer.use_pass_glossy_direct:
        channels.append(('GlossyDir', 'GlossyDir'))
    
    if view_layer.use_pass_emit:
        channels.append(('Emit', 'Emit'))
    
    # Additional common passes
    if view_layer.use_pass_diffuse_color:
        channels.append(('DiffuseCol', 'DiffuseCol'))
    
    if view_layer.use_pass_glossy_color:
        channels.append(('GlossyCol', 'GlossyCol'))
    
    if view_layer.use_pass_transmission_direct:
        channels.append(('TransDir', 'TransDir'))
    
    if view_layer.use_pass_transmission_color:
        channels.append(('TransCol', 'TransCol'))
    
    if view_layer.use_pass_ambient_occlusion:
        channels.append(('AO', 'AO'))
    
    if view_layer.use_pass_shadow:
        channels.append(('Shadow', 'Shadow'))
    
    if hasattr(view_layer, 'use_pass_environment') and view_layer.use_pass_environment:
        channels.append(('Environment', 'Environment'))
    
    return channels


def save_render_pass(scene, channel_name, pass_name, filepath):
    """Save a specific render pass to file by accessing render result data"""
    try:
        # Get the render result image
        render_result = bpy.data.images.get('Render Result')
        if not render_result:
            print(f"⚠️ No render result found for {channel_name}")
            return False
        
        if channel_name == 'Combined':
            # Save the combined result directly
            render_result.save_render(filepath=filepath, scene=scene)
            return True
        
        # For specific passes, access them from the render result's pass data
        try:
            # Map channel names to Blender's internal pass names
            pass_name_mapping = {
                'Depth': 'Z',
                'Mist': 'Mist',
                'Normal': 'Normal',
                'DiffuseDir': 'DiffDir',
                'GlossyDir': 'GlossDir',
                'Emit': 'Emit'
            }
            
            blender_pass_name = pass_name_mapping.get(channel_name, channel_name)
            
            # Try to access the pass data directly from render result
            # Check if the pass exists in render layers
            if hasattr(render_result, 'render_layers') and render_result.render_layers:
                render_layer = render_result.render_layers[0]
                
                # Look for the specific pass
                pass_found = False
                for render_pass in render_layer.passes:
                    if render_pass.name == blender_pass_name or render_pass.name == channel_name:
                        pass_found = True
                        break
                
                if pass_found:
                    # Create a temporary image for the pass
                    temp_image_name = f"TempPass_{channel_name}"
                    
                    # Remove existing temp image if it exists
                    if temp_image_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[temp_image_name])
                    
                    # Create new image with same dimensions as render result
                    temp_image = bpy.data.images.new(
                        name=temp_image_name,
                        width=render_result.size[0],
                        height=render_result.size[1],
                        alpha=True
                    )
                    
                    # Copy the pass data to our temp image
                    # Note: This is a simplified approach - actual pass extraction 
                    # would require proper buffer manipulation
                    temp_image.pixels = render_pass.rect[:]
                    temp_image.filepath_raw = filepath
                    temp_image.file_format = scene.render.image_settings.file_format
                    temp_image.save()
                    
                    # Clean up temp image
                    bpy.data.images.remove(temp_image)
                    
                    print(f"✓ Extracted and saved {channel_name} pass to: {filepath}")
                    return True
            
            # If we couldn't extract the specific pass, fall back to a workaround
            # Use the viewer node approach with minimal setup
            return save_pass_via_viewer(scene, channel_name, blender_pass_name, filepath)
                
        except Exception as pass_error:
            print(f"⚠️ Error extracting {channel_name} pass: {pass_error}")
            # Fall back to combined pass
            render_result.save_render(filepath=filepath, scene=scene)
            print(f"⚠️ Saved combined pass instead of {channel_name}")
            return True
            
    except Exception as e:
        print(f"❌ Error saving {channel_name} pass: {e}")
        return False


def save_pass_via_viewer(scene, channel_name, blender_pass_name, filepath):
    """Alternative method to save pass using viewer node approach"""
    try:
        # This is a simplified fallback - for now just save combined
        # In a full implementation, this would set up compositor nodes temporarily
        render_result = bpy.data.images.get('Render Result')
        if render_result:
            render_result.save_render(filepath=filepath, scene=scene)
            print(f"⚠️ {channel_name} pass saved as combined (proper pass extraction not yet implemented)")
            return True
        return False
    except Exception as e:
        print(f"❌ Error in viewer fallback for {channel_name}: {e}")
        return False


def setup_compositor_for_pass(scene, channel_name, pass_name):
    """Set up compositor to output specific render pass"""
    # Store original state
    original_state = {
        'use_nodes': scene.use_nodes,
        'created_nodes': []  # Track ONLY the nodes we create
    }
    
    if channel_name == 'Combined':
        # No compositor setup needed for combined pass
        return original_state
    
    try:
        # Enable compositor (but don't touch existing nodes)
        scene.use_nodes = True
        
        # Create render layers input node with unique name
        render_layers_node = scene.node_tree.nodes.new('CompositorNodeRLayers')
        render_layers_node.name = 'FRH_TempRenderLayers'
        render_layers_node.location = (-300, 0)
        original_state['created_nodes'].append(render_layers_node.name)
        
        # Create composite output node with unique name
        composite_node = scene.node_tree.nodes.new('CompositorNodeComposite')
        composite_node.name = 'FRH_TempComposite'
        composite_node.location = (0, 0)
        original_state['created_nodes'].append(composite_node.name)
        
        # Map channel names to socket names in Blender's compositor
        socket_mapping = {
            'Depth': 'Depth',
            'Mist': 'Mist',
            'Normal': 'Normal',
            'DiffuseDir': 'DiffDir',
            'GlossyDir': 'GlossDir',
            'Emit': 'Emit',
            'DiffuseCol': 'DiffCol',
            'GlossyCol': 'GlossCol',
            'TransDir': 'TransDir',
            'TransCol': 'TransCol',
            'AO': 'AO',
            'Shadow': 'Shadow',
            'Environment': 'Env'
        }
        
        socket_name = socket_mapping.get(channel_name, channel_name)
        
        # Find and connect the appropriate output
        output_socket = None
        for output in render_layers_node.outputs:
            if output.name == socket_name:
                output_socket = output
                break
        
        if output_socket:
            # Connect the specific pass to composite output
            scene.node_tree.links.new(output_socket, composite_node.inputs['Image'])
            print(f"✓ Set up compositor for {channel_name} pass")
        else:
            # Fallback to combined if pass not found
            scene.node_tree.links.new(render_layers_node.outputs['Image'], composite_node.inputs['Image'])
            print(f"⚠️ Pass {channel_name} not found, using combined")
        
    except Exception as e:
        print(f"⚠️ Error setting up compositor for {channel_name}: {e}")
    
    return original_state


def restore_compositor_state(scene, original_state):
    """Restore original compositor state - only remove nodes we created"""
    try:
        if not original_state:
            return
        
        # Remove ONLY the nodes we created (identified by name)
        if scene.node_tree and original_state.get('created_nodes'):
            nodes_to_remove = []
            for node_name in original_state['created_nodes']:
                node = scene.node_tree.nodes.get(node_name)
                if node:
                    nodes_to_remove.append(node)
            
            # Remove our temporary nodes
            for node in nodes_to_remove:
                scene.node_tree.nodes.remove(node)
            
            if nodes_to_remove:
                print(f"✓ Removed {len(nodes_to_remove)} temporary compositor nodes")
        
        # Restore original use_nodes state
        scene.use_nodes = original_state['use_nodes']
            
    except Exception as e:
        print(f"⚠️ Error restoring compositor state: {e}")


def save_render_result(scene, filepath):
    """Save the current render result to file"""
    try:
        render_result = bpy.data.images.get('Render Result')
        if render_result:
            render_result.save_render(filepath=filepath, scene=scene)
            return True
        return False
    except Exception as e:
        print(f"❌ Error saving render result: {e}")
        return False


def generate_filename_from_pattern(pattern, blend_name, camera_name, frame_num, start_time=None, end_time=None, channel_name=None, view_layer_name=None, batch_start_time=None, render_duration_seconds=None):
    """
    Generate filename from pattern with token replacement
    
    Available tokens:
    (FileName) - Blender file name without .blend extension
    (Camera) - Current scene camera name
    (ViewLayer) - Current view layer name
    (Frame) - Frame number with zero-padding (0001, 0002, etc.)
    (Channel) - Render pass/channel name (Combined, Depth, Mist, Normal, etc.)
                Required when multiple render passes are enabled to avoid overwriting
    (Start:format) - Render start date/time with custom format
    (End:format) - Render end date/time with custom format
    (BatchStart:format) - Batch render start date/time with custom format
    (RenderDurationSeconds) - Render duration in seconds for single frame
    
    Format examples:
    yyyyMMdd = 20251018
    yyyyMMddHHmmss = 20251018172118
    yyyy-MM-dd = 2025-10-18
    yyyyMMdd_HH:mm:ss = 20251018_17:21:18
    """
    import re
    from datetime import datetime
    
    result = pattern
    
    # Replace basic tokens
    result = result.replace("(Camera)", camera_name or "NoCamera")
    result = result.replace("(Frame)", f"{frame_num:04d}")
    result = result.replace("(FileName)", blend_name or "untitled")
    result = result.replace("(ViewLayer)", view_layer_name or "ViewLayer")
    
    # Only replace (Channel) token if it exists in the pattern
    if "(Channel)" in result:
        result = result.replace("(Channel)", channel_name or "Combined")
    
    # Replace render duration token
    if "(RenderDurationSeconds)" in result:
        if render_duration_seconds is not None:
            result = result.replace("(RenderDurationSeconds)", f"{render_duration_seconds:.2f}")
        else:
            result = result.replace("(RenderDurationSeconds)", "0.00")
    
    # Replace datetime tokens with regex to handle custom formats
    def replace_datetime_token(match):
        token_type = match.group(1)  # "Start", "End", or "BatchStart"
        datetime_format = match.group(2)  # Custom format string
        
        # Select the appropriate datetime
        if token_type == "Start" and start_time:
            dt = start_time
        elif token_type == "End" and end_time:
            dt = end_time
        elif token_type == "BatchStart" and batch_start_time:
            dt = batch_start_time
        else:
            # Use current time as fallback
            dt = datetime.now()
        
        # Convert custom format to Python strftime format
        py_format = datetime_format
        # Replace common patterns
        py_format = py_format.replace("yyyy", "%Y")
        py_format = py_format.replace("MM", "%m") 
        py_format = py_format.replace("dd", "%d")
        py_format = py_format.replace("HH", "%H")
        py_format = py_format.replace("mm", "%M")
        py_format = py_format.replace("ss", "%S")
        
        try:
            return dt.strftime(py_format)
        except Exception as e:
            print(f"Warning: Invalid datetime format '{datetime_format}': {e}")
            return dt.strftime("%Y%m%d_%H%M%S")  # Fallback format
    
    # Replace Start, End, and BatchStart tokens with format
    result = re.sub(r'\((Start|End|BatchStart):([^)]+)\)', replace_datetime_token, result)
    
    # Clean up any remaining tokens or invalid characters for filenames
    # Remove invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        result = result.replace(char, '_')
    
    return result


class RENDER_OT_set_output_folder(Operator):
    """Set output folder for rendering specific frames"""
    bl_idname = "render.set_output_folder"
    bl_label = "Set Output Folder"
    bl_description = "Choose the folder where rendered frames will be saved"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Property to store output folder path
    folder_path: StringProperty(
        name="Output Folder",
        description="Choose the folder where rendered frames will be saved",
        default="",
        subtype='DIR_PATH'
    )
    
    def execute(self, context):
        global output_folder_path
        if self.folder_path.strip():
            output_folder_path = bpy.path.abspath(self.folder_path.strip())
            # Ensure the folder exists
            try:
                os.makedirs(output_folder_path, exist_ok=True)
                # Save as default preference
                save_default_output_folder()
                self.report({'INFO'}, f"Output folder set to: {output_folder_path}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to create/access folder: {str(e)}")
                return {'CANCELLED'}
        else:
            # Clear the output folder (use default)
            output_folder_path = ""
            # Save empty preference
            save_default_output_folder()
            self.report({'INFO'}, "Output folder cleared (will use blend file directory)")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        global output_folder_path
        self.folder_path = output_folder_path
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_path")
        layout.separator()
        
        # Show information about storage location
        source = get_output_path_source()
        info_box = layout.box()
        if source == 'SCENE_PROPS':
            info_box.label(text="Storage: Scene Properties (per-project)", icon='SCENE_DATA')
            info_box.label(text="This folder will be saved in the blend file")
        else:  # USER_PREFS
            info_box.label(text="Storage: User Preferences (global)", icon='PREFERENCES')
            info_box.label(text="This folder will be saved as your default")
        
        layout.separator()
        layout.label(text="Leave empty to use blend file directory")
        layout.label(text="Change storage location in Add-on Preferences", icon='INFO')


class RENDER_OT_set_filename_pattern(Operator):
    """Set filename pattern for rendered frames"""
    bl_idname = "render.set_filename_pattern"
    bl_label = "Set Filename Pattern"
    bl_description = "Customize the filename pattern for rendered frames using tokens"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Property to store filename pattern
    pattern: StringProperty(
        name="Filename Pattern",
        description="Filename pattern using tokens like (FileName), (Camera), (ViewLayer), (Frame), (Channel), (Start:yyyyMMdd), (End:HHmmss)",
        default="(FileName)_(Camera)_frame_(Frame)",
        maxlen=200
    )
    
    def execute(self, context):
        global filename_pattern
        if self.pattern.strip():
            filename_pattern = self.pattern.strip()
            # Save as default preference
            save_user_preferences()
            self.report({'INFO'}, f"Filename pattern set to: {filename_pattern}")
        else:
            # Reset to default
            filename_pattern = "(FileName)_(Camera)_frame_(Frame)"
            save_user_preferences()
            self.report({'INFO'}, "Filename pattern reset to default")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        global filename_pattern
        self.pattern = filename_pattern
        return context.window_manager.invoke_props_dialog(self, width=500)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pattern")
        layout.separator()
        
        # Show information about storage location
        source = get_output_path_source()
        info_box = layout.box()
        if source == 'SCENE_PROPS':
            info_box.label(text="Storage: Scene Properties (per-project)", icon='SCENE_DATA')
            info_box.label(text="This pattern will be saved in the blend file")
        else:  # USER_PREFS
            info_box.label(text="Storage: User Preferences (global)", icon='PREFERENCES')
            info_box.label(text="This pattern will be saved as your default")
        
        layout.separator()
        layout.label(text="Change storage location in Add-on Preferences", icon='INFO')
        
        layout.separator()
        
        # Help section
        help_box = layout.box()
        help_box.label(text="Available Tokens:", icon='INFO')
        help_box.label(text="(FileName) - Blend file name without extension")
        help_box.label(text="(Camera) - Current scene camera name")
        help_box.label(text="(ViewLayer) - Current view layer name")
        help_box.label(text="(Frame) - Frame number with padding (0001)")
        help_box.label(text="(Channel) - Render pass name (Combined, Depth, etc.)")
        help_box.label(text="             Required for multi-pass rendering")
        help_box.label(text="(Start:format) - Render start date/time")
        help_box.label(text="(End:format) - Render end date/time")
        help_box.label(text="(BatchStart:format) - Batch render start date/time")
        help_box.label(text="(RenderDurationSeconds) - Render duration in seconds")
        
        layout.separator()
        format_box = layout.box()
        format_box.label(text="Date/Time Format Examples:", icon='TIME')
        format_box.label(text="yyyyMMdd → 20251028")
        format_box.label(text="yyyyMMddHHmmss → 20251028172118")  
        format_box.label(text="yyyy-MM-dd → 2025-10-28")
        format_box.label(text="yyyyMMdd_HH:mm:ss → 20251028_17:21:18")
        
        layout.separator()
        example_box = layout.box()
        example_box.label(text="Pattern Examples:", icon='FILE_TEXT')
        example_box.label(text="(FileName)_(Camera)_(Frame)_(Start:yyyyMM)")
        example_box.label(text="→ blenderfile_maincamera_0001_202510")
        example_box.label(text="(FileName)_(Frame)_(End:yyyyMMddHHmmss)")
        example_box.label(text="→ blenderfile_0001_20251018172118")


class RENDER_OT_specific_frames(Operator):
    """Furion Render Helper based on user input"""
    bl_idname = "render.specific_frames"
    bl_label = "Furion Render Helper"
    bl_description = "Furion Render Helper entered by user (comma separated)"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Internal properties for modal operation
    _timer = None
    _frame_numbers = []
    _current_frame_index = 0
    _original_frame = 0
    _original_filepath = ""
    _original_format = ""
    _format_switched = False
    _output_folder = ""
    _blend_filename = ""
    _last_saved_path = ""
    _original_use_persistent_data = False
    _render_start_time = None
    _frame_start_time = None
    _batch_start_time = None  # Time when batch rendering starts
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # Check if we're done rendering all frames and channels
            if self._current_frame_index >= len(self._frame_numbers):
                return self.finish_rendering(context)
            
            # Check if we're done with all channels for current frame
            if self._current_channel_index >= len(self._selected_channels):
                # Move to next frame
                self._current_frame_index += 1
                self._current_channel_index = 0
                # Update UI
                for area in context.screen.areas:
                    area.tag_redraw()
                return {'PASS_THROUGH'}
            
            # Get current frame and channel
            frame_num = self._frame_numbers[self._current_frame_index]
            channel_name, pass_name = self._selected_channels[self._current_channel_index]
            scene = context.scene
            render = scene.render
            
            # Set current frame
            scene.frame_set(frame_num)
            
            # Get camera name for filename
            camera_name = "NoCamera"
            if scene.camera:
                camera_name = scene.camera.name
            
            # Get view layer name
            view_layer_name = scene.view_layers[0].name if scene.view_layers else "ViewLayer"
            
            # Record frame start time for filename patterns
            from datetime import datetime
            self._frame_start_time = datetime.now()
            
            # Generate filename using custom pattern with channel
            global filename_pattern
            # Only use channel name if pattern contains (Channel) token or multiple channels selected
            if "(Channel)" in filename_pattern or len(self._selected_channels) > 1:
                filename = generate_filename_from_pattern(
                    filename_pattern,
                    self._blend_filename,
                    camera_name,
                    frame_num,
                    start_time=self._render_start_time,
                    end_time=None,  # End time not available yet during rendering
                    channel_name=channel_name,
                    view_layer_name=view_layer_name,
                    batch_start_time=self._batch_start_time,
                    render_duration_seconds=None  # Will be calculated after render
                )
            else:
                filename = generate_filename_from_pattern(
                    filename_pattern,
                    self._blend_filename,
                    camera_name,
                    frame_num,
                    start_time=self._render_start_time,
                    end_time=None,  # End time not available yet during rendering
                    channel_name=None,
                    view_layer_name=view_layer_name,
                    batch_start_time=self._batch_start_time,
                    render_duration_seconds=None  # Will be calculated after render
                )
            
            # Get file extension from render settings
            file_format = render.image_settings.file_format.lower()
            if file_format == 'png':
                extension = '.png'
            elif file_format == 'jpeg':
                extension = '.jpg'
            elif file_format == 'tiff':
                extension = '.tif'
            elif file_format == 'exr':
                extension = '.exr'
            else:
                extension = '.png'  # default
            
            # Set full output path
            full_output_path = os.path.join(self._output_folder, filename + extension)
            filepath_without_ext = os.path.join(self._output_folder, filename)
            render.use_file_extension = True
            render.filepath = filepath_without_ext
            self._last_saved_path = full_output_path
            
            # Calculate total progress (frames * channels)
            total_renders = len(self._frame_numbers) * len(self._selected_channels)
            current_render = (self._current_frame_index * len(self._selected_channels)) + self._current_channel_index + 1
            progress_percent = (current_render / total_renders) * 100
            progress_bar = "█" * int(progress_percent / 5) + "░" * (20 - int(progress_percent / 5))
            
            print("=" * 60)
            print(f"RENDERING PROGRESS: [{progress_bar}] {progress_percent:.1f}%")
            print(f"Frame {self._current_frame_index + 1} of {len(self._frame_numbers)}")
            print(f"Channel {self._current_channel_index + 1} of {len(self._selected_channels)} ({channel_name})")
            print(f"Current Frame Number: {frame_num}")
            print(f"Output File: {filename}{extension}")
            print(f"Full Path: {full_output_path}")
            print(f"Render Format: {render.image_settings.file_format}")
            print(f"Resolution: {render.resolution_x}x{render.resolution_y}")
            print("=" * 60)
            
            # Update progress in UI
            progress_msg = f"Rendering frame {frame_num} - {channel_name} ({current_render}/{total_renders}) -> {filename}{extension}"
            self.report({'INFO'}, progress_msg)
            
            # Set up compositor for this specific pass if needed
            original_compositor_state = setup_compositor_for_pass(scene, channel_name, pass_name)
            
            # Render the frame
            print(f"Starting render of frame {frame_num} - {channel_name}...")
            from datetime import datetime
            render_start = datetime.now()
            bpy.ops.render.render(write_still=True)
            render_end = datetime.now()
            render_duration = (render_end - render_start).total_seconds()
            
            # If filename pattern contains (RenderDurationSeconds), regenerate filename with actual duration
            if "(RenderDurationSeconds)" in filename_pattern:
                # Regenerate filename with render duration
                if "(Channel)" in filename_pattern or len(self._selected_channels) > 1:
                    filename = generate_filename_from_pattern(
                        filename_pattern,
                        self._blend_filename,
                        camera_name,
                        frame_num,
                        start_time=self._render_start_time,
                        end_time=render_end,
                        channel_name=channel_name,
                        view_layer_name=view_layer_name,
                        batch_start_time=self._batch_start_time,
                        render_duration_seconds=render_duration
                    )
                else:
                    filename = generate_filename_from_pattern(
                        filename_pattern,
                        self._blend_filename,
                        camera_name,
                        frame_num,
                        start_time=self._render_start_time,
                        end_time=render_end,
                        channel_name=None,
                        view_layer_name=view_layer_name,
                        batch_start_time=self._batch_start_time,
                        render_duration_seconds=render_duration
                    )
                
                # Update paths with new filename
                full_output_path = os.path.join(self._output_folder, filename + extension)
                self._last_saved_path = full_output_path
                
                print(f"✓ Render duration: {render_duration:.2f} seconds")
            
            # Check if the file was created - check multiple possible paths
            file_created = False
            actual_path = None
            
            # Check multiple possible file paths
            possible_paths = [
                full_output_path,  # Expected path
                filepath_without_ext + extension,  # Path without explicit extension
                filepath_without_ext + f"_{frame_num:04d}{extension}",  # With frame number
                filepath_without_ext + f"{frame_num:04d}{extension}",  # Frame without underscore
                full_output_path.replace(extension, f"_{frame_num:04d}{extension}"),  # Expected path with frame
                full_output_path.replace(extension, f"{frame_num:04d}{extension}")  # Without underscore
            ]
            
            # Also check uppercase extension variants
            if extension.lower() != extension:
                possible_paths.extend([
                    p.replace(extension, extension.upper()) for p in possible_paths[:6]
                ])
            
            for check_path in possible_paths:
                if os.path.exists(check_path):
                    file_created = True
                    actual_path = check_path
                    print(f"✓ Frame {frame_num} - {channel_name} rendered successfully at: {actual_path}")
                    break
            
            if not file_created:
                print(f"WARNING: Expected file not found. Checked paths:")
                for check_path in possible_paths:
                    print(f"  - {check_path}")
                
                # Try to save manually if automatic save failed
                success = save_render_result(scene, full_output_path)
                if success and os.path.exists(full_output_path):
                    file_created = True
                    actual_path = full_output_path
                    print(f"✓ Frame {frame_num} - {channel_name} manually saved to: {actual_path}")
                else:
                    print(f"❌ Failed to save frame {frame_num} - {channel_name}")
            
            
            # Restore compositor state
            restore_compositor_state(scene, original_compositor_state)
            
            # Move to next channel
            self._current_channel_index += 1
            
            # Update UI
            for area in context.screen.areas:
                area.tag_redraw()
        
        elif event.type == 'ESC':
            return self.cancel_rendering(context)
        
        return {'PASS_THROUGH'}
    
    def finish_rendering(self, context):
        # Console completion message
        channel_names = [ch[0] for ch in self._selected_channels]
        total_renders = len(self._frame_numbers) * len(self._selected_channels)
        print("\n" + "=" * 60)
        print("🎉 RENDERING COMPLETED SUCCESSFULLY! 🎉")
        print(f"✓ Total frames rendered: {len(self._frame_numbers)}")
        print(f"✓ Render channels: {channel_names}")
        print(f"✓ Total renders: {total_renders}")
        print(f"✓ Output folder: {self._output_folder}")
        print(f"✓ Frame numbers: {self._frame_numbers}")
        print("=" * 60 + "\n")
        
        # Restore original frame and filepath
        scene = context.scene
        scene.frame_set(self._original_frame)
        scene.render.filepath = self._original_filepath
        if self._format_switched and self._original_format:
            try:
                scene.render.image_settings.file_format = self._original_format
            except Exception:
                pass
        
        # Restore original persistent data setting
        scene.render.use_persistent_data = self._original_use_persistent_data
        print(f"✓ Restored persistent data setting to: {self._original_use_persistent_data}")
        
        # Remove timer
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        total_renders = len(self._frame_numbers) * len(self._selected_channels)
        self.report({'INFO'}, f"Successfully rendered {len(self._frame_numbers)} frames with {len(self._selected_channels)} channels ({total_renders} total renders)")
        return {'FINISHED'}
    
    def cancel_rendering(self, context):
        # Console cancellation message
        completed_renders = (self._current_frame_index * len(self._selected_channels)) + self._current_channel_index
        total_renders = len(self._frame_numbers) * len(self._selected_channels)
        print("\n" + "=" * 60)
        print("⚠️  RENDERING CANCELLED BY USER ⚠️")
        print(f"✓ Renders completed: {completed_renders}/{total_renders}")
        print(f"✓ Frames completed: {self._current_frame_index}/{len(self._frame_numbers)}")
        print(f"✓ Output folder: {self._output_folder}")
        print("=" * 60 + "\n")
        
        # Restore original frame and filepath
        scene = context.scene
        scene.frame_set(self._original_frame)
        scene.render.filepath = self._original_filepath
        if self._format_switched and self._original_format:
            try:
                scene.render.image_settings.file_format = self._original_format
            except Exception:
                pass
        
        # Restore original persistent data setting
        scene.render.use_persistent_data = self._original_use_persistent_data
        print(f"✓ Restored persistent data setting to: {self._original_use_persistent_data}")
        
        # Remove timer
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        
        completed_renders = (self._current_frame_index * len(self._selected_channels)) + self._current_channel_index
        total_renders = len(self._frame_numbers) * len(self._selected_channels)
        self.report({'WARNING'}, f"Rendering cancelled. Completed {completed_renders}/{total_renders} renders ({self._current_frame_index}/{len(self._frame_numbers)} frames)")
        return {'CANCELLED'}
    
    def execute(self, context):
        global output_folder_path
        # Parse the frame list
        try:
            frame_string = context.scene.frh_frame_list.strip()
            if not frame_string:
                self.report({'ERROR'}, "Please enter frame numbers")
                return {'CANCELLED'}
            
            # Split by comma and convert to integers or ranges
            frame_numbers = []
            for frame_str in frame_string.split(','):
                frame_str = frame_str.strip()
                if frame_str:
                    try:
                        # Check if it's a range (contains hyphen)
                        if '-' in frame_str:
                            # Handle range like "1-5" or "10-20"
                            range_parts = frame_str.split('-')
                            if len(range_parts) == 2:
                                start_frame = int(range_parts[0].strip())
                                end_frame = int(range_parts[1].strip())
                                if start_frame <= end_frame:
                                    # Add all frames in range (inclusive)
                                    frame_numbers.extend(range(start_frame, end_frame + 1))
                                else:
                                    self.report({'ERROR'}, f"Invalid range: {frame_str} (start must be <= end)")
                                    return {'CANCELLED'}
                            else:
                                self.report({'ERROR'}, f"Invalid range format: {frame_str}")
                                return {'CANCELLED'}
                        else:
                            # Single frame number
                            frame_num = int(frame_str)
                            frame_numbers.append(frame_num)
                    except ValueError:
                        self.report({'ERROR'}, f"Invalid frame number or range: {frame_str}")
                        return {'CANCELLED'}
            
            if not frame_numbers:
                self.report({'ERROR'}, "No valid frame numbers found")
                return {'CANCELLED'}
            
            # Remove duplicates and sort
            frame_numbers = sorted(list(set(frame_numbers)))
            
            # Get selected render channels from Blender's view layer
            scene = context.scene
            selected_channels = get_selected_channels(scene)
            
            # Note: Combined is always included by default in get_selected_channels()

            # Show info if multiple channels but no (Channel) token
            global filename_pattern
            if len(selected_channels) > 1 and "(Channel)" not in filename_pattern:
                self.report({'INFO'}, f"💡 Tip: Add (Channel) token to filename pattern for multi-pass rendering. {len(selected_channels)} passes will use the same filename.")
            
            # Store frame numbers and channels for modal operation
            self._frame_numbers = frame_numbers
            self._selected_channels = selected_channels
            self._current_frame_index = 0
            self._current_channel_index = 0
            
            # Get current scene
            scene = context.scene
            
            # Store original frame and filepath
            self._original_frame = scene.frame_current
            self._original_filepath = scene.render.filepath
            self._original_format = scene.render.image_settings.file_format
            self._format_switched = False
            
            # Store original persistent data setting and enable it for batch rendering
            self._original_use_persistent_data = scene.render.use_persistent_data
            scene.render.use_persistent_data = True
            print(f"✓ Enabled persistent data for batch rendering (was: {self._original_use_persistent_data})")

            # If current file format is a video/unsupported for still files, switch to PNG temporarily
            disallowed_formats = {"FFMPEG", "AVI_JPEG", "AVI_RAW", "FRAMESERVER"}
            if self._original_format in disallowed_formats:
                try:
                    scene.render.image_settings.file_format = 'PNG'
                    self._format_switched = True
                    print(f"ℹ️ Switched render format from {self._original_format} to PNG for still rendering")
                except Exception as e:
                    self.report({'WARNING'}, f"Could not switch format from {self._original_format}; output may not save correctly: {e}")
            
            # Get the blend file name (without extension)
            blend_filepath = bpy.data.filepath
            if blend_filepath:
                self._blend_filename = os.path.splitext(os.path.basename(blend_filepath))[0]
            else:
                self._blend_filename = "untitled"
            
            # Set up output folder
            if output_folder_path.strip():
                self._output_folder = output_folder_path
                # Ensure the folder exists
                os.makedirs(self._output_folder, exist_ok=True)
            else:
                # Use default blend file directory or current directory
                if blend_filepath:
                    self._output_folder = os.path.dirname(bpy.path.abspath(blend_filepath))
                else:
                    self._output_folder = os.getcwd()
            
            total_renders = len(frame_numbers) * len(selected_channels)
            channel_names = [ch[0] for ch in selected_channels]
            self.report({'INFO'}, f"Starting render of {len(frame_numbers)} frames with {len(selected_channels)} channels ({total_renders} total renders)")
            self.report({'INFO'}, f"Channels: {', '.join(channel_names)}")
            self.report({'INFO'}, f"Frames: {frame_numbers}")
            self.report({'INFO'}, f"Output folder: {self._output_folder}")
            self.report({'INFO'}, "Press ESC to cancel rendering")
            
            # Console startup message
            total_renders = len(frame_numbers) * len(selected_channels)
            channel_names = [ch[0] for ch in selected_channels]
            print("\n" + "=" * 60)
            print("🚀 STARTING BATCH RENDER PROCESS 🚀")
            print(f"📁 Output folder: {self._output_folder}")
            print(f"🎬 Blend file: {self._blend_filename}")
            print(f"🎯 Total frames to render: {len(frame_numbers)}")
            print(f"🎭 Render channels: {channel_names}")
            print(f"📊 Total renders: {total_renders} ({len(frame_numbers)} frames × {len(selected_channels)} channels)")
            print(f"📋 Frame list: {frame_numbers}")
            print(f"🖼️  Format: {context.scene.render.image_settings.file_format}")
            print(f"📐 Resolution: {context.scene.render.resolution_x}x{context.scene.render.resolution_y}")
            print(f"💾 Persistent data: ON (was {self._original_use_persistent_data})")
            print("💡 Press ESC to cancel rendering at any time")
            print("=" * 60 + "\n")
            
            # Record render start time for filename patterns
            from datetime import datetime
            self._render_start_time = datetime.now()
            self._batch_start_time = self._render_start_time  # Batch start is same as first render start
            
            # Start modal operation with timer
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.1, window=context.window)
            wm.modal_handler_add(self)
            
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error during rendering: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # Show dialog box for user input
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        global output_folder_path
        layout = self.layout
        
        # Show current output folder
        box = layout.box()
        if output_folder_path:
            box.label(text=f"Output Folder: {output_folder_path}", icon='FOLDER_REDIRECT')
        else:
            box.label(text="Output Folder: (Blend file directory)", icon='FOLDER_REDIRECT')
        
        layout.separator()
        
        # Frame numbers input section with suggestion button
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(context.scene, "frh_frame_list", text="Frame Numbers")
        
        # Suggest Keyframes button - pass current frame_list to the operator
        suggest_op = row.operator("render.suggest_keyframes", text="", icon='KEYFRAME_HLT')
        suggest_op.current_frames = context.scene.frh_frame_list
        
        col.label(text="Enter frame numbers separated by commas")
        col.label(text="Examples: 1,5,10,25 or 1-5,10-15,30")
        
        # Add keyframe suggestion info
        layout.separator()
        info_box = layout.box()
        info_box.label(text="💡 Click the keyframe icon to auto-populate frames with keyframes", icon='INFO')
        
        layout.separator()
        layout.label(text="Note: Press ESC during rendering to cancel", icon='INFO')


class RENDER_OT_current_frame(Operator):
    """Render the current frame to the configured output folder"""
    bl_idname = "render.current_frame"
    bl_label = "Render Current Frame"
    bl_description = "Render only the current frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global output_folder_path, filename_pattern
        try:
            scene = context.scene
            render = scene.render

            # Get selected render channels from Blender's view layer
            selected_channels = get_selected_channels(scene)
            
            # Note: Combined is always included by default in get_selected_channels()

            # Show info if multiple channels but no (Channel) token
            if len(selected_channels) > 1 and "(Channel)" not in filename_pattern:
                self.report({'INFO'}, f"💡 Tip: Add (Channel) token to filename pattern for multi-pass rendering. {len(selected_channels)} passes will use the same filename.")

            # Store original settings to restore after rendering
            original_filepath = render.filepath
            original_format = render.image_settings.file_format
            format_switched = False

            # Determine output folder
            blend_filepath = bpy.data.filepath
            if output_folder_path.strip():
                output_folder = bpy.path.abspath(output_folder_path.strip())
                os.makedirs(output_folder, exist_ok=True)
            else:
                if blend_filepath:
                    output_folder = os.path.dirname(bpy.path.abspath(blend_filepath))
                else:
                    output_folder = os.getcwd()

            # Determine blend name and frame
            if blend_filepath:
                blend_name = os.path.splitext(os.path.basename(blend_filepath))[0]
            else:
                blend_name = "untitled"
            frame_num = scene.frame_current

            # File extension from render format
            # Ensure an image-capable format
            disallowed_formats = {"FFMPEG", "AVI_JPEG", "AVI_RAW", "FRAMESERVER"}
            if original_format in disallowed_formats:
                try:
                    render.image_settings.file_format = 'PNG'
                    format_switched = True
                    print(f"ℹ️ Switched render format from {original_format} to PNG for still rendering")
                except Exception as e:
                    self.report({'WARNING'}, f"Could not switch format from {original_format}; output may not save correctly: {e}")

            fmt = render.image_settings.file_format.lower()
            if fmt == 'png':
                extension = '.png'
            elif fmt == 'jpeg':
                extension = '.jpg'
            elif fmt == 'tiff':
                extension = '.tif'
            elif fmt == 'exr':
                extension = '.exr'
            else:
                extension = '.png'

            # Get camera name
            camera_name = "NoCamera"
            if scene.camera:
                camera_name = scene.camera.name

            # Get view layer name
            view_layer_name = scene.view_layers[0].name if scene.view_layers else "ViewLayer"

            # Console info
            print("\n" + "=" * 60)
            print("🎯 RENDER CURRENT FRAME")
            print(f"📁 Output folder: {output_folder}")
            print(f"🎬 Blend file: {blend_name}")
            print(f"📷 Camera: {camera_name}")
            print(f"🧭 Frame: {frame_num}")
            print(f"🖼️  Format: {render.image_settings.file_format}")
            print(f"🎭 Channels: {[ch[0] for ch in selected_channels]}")
            print("=" * 60 + "\n")

            # Render and save each channel
            from datetime import datetime
            batch_start_time = datetime.now()  # For current frame, batch start is when user clicks render
            saved_paths = []

            for channel_name, pass_name in selected_channels:
                # Record start time for this render
                render_start = datetime.now()
                
                # Generate filename for this channel - only use channel name if pattern contains (Channel) token
                if "(Channel)" in filename_pattern or len(selected_channels) > 1:
                    # Use channel name in filename
                    filename = generate_filename_from_pattern(
                        filename_pattern,
                        blend_name,
                        camera_name,
                        frame_num,
                        start_time=render_start,
                        end_time=None,  # Will be updated after render if needed
                        channel_name=channel_name,
                        view_layer_name=view_layer_name,
                        batch_start_time=batch_start_time,
                        render_duration_seconds=None  # Will be calculated after render
                    )
                else:
                    # Don't use channel name - for single Combined pass without (Channel) token
                    filename = generate_filename_from_pattern(
                        filename_pattern,
                        blend_name,
                        camera_name,
                        frame_num,
                        start_time=render_start,
                        end_time=None,  # Will be updated after render if needed
                        channel_name=None,  # This will default to "Combined" but won't be used
                        view_layer_name=view_layer_name,
                        batch_start_time=batch_start_time,
                        render_duration_seconds=None  # Will be calculated after render
                    )
                
                full_output_path = os.path.join(output_folder, filename + extension)

                # Set up compositor for this specific pass
                original_compositor_state = setup_compositor_for_pass(scene, channel_name, pass_name)
                
                # Set filepath WITHOUT extension (Blender will add it)
                filepath_without_ext = os.path.join(output_folder, filename)
                render.filepath = filepath_without_ext
                render.use_file_extension = True
                
                # Render and measure duration
                render_actual_start = datetime.now()
                bpy.ops.render.render(write_still=True)
                render_end = datetime.now()
                render_duration = (render_end - render_actual_start).total_seconds()
                
                # If filename pattern contains (RenderDurationSeconds), regenerate filename with actual duration
                if "(RenderDurationSeconds)" in filename_pattern:
                    # Regenerate filename with render duration
                    if "(Channel)" in filename_pattern or len(selected_channels) > 1:
                        filename = generate_filename_from_pattern(
                            filename_pattern,
                            blend_name,
                            camera_name,
                            frame_num,
                            start_time=render_start,
                            end_time=render_end,
                            channel_name=channel_name,
                            view_layer_name=view_layer_name,
                            batch_start_time=batch_start_time,
                            render_duration_seconds=render_duration
                        )
                    else:
                        filename = generate_filename_from_pattern(
                            filename_pattern,
                            blend_name,
                            camera_name,
                            frame_num,
                            start_time=render_start,
                            end_time=render_end,
                            channel_name=None,
                            view_layer_name=view_layer_name,
                            batch_start_time=batch_start_time,
                            render_duration_seconds=render_duration
                        )
                    
                    # Update paths with new filename
                    full_output_path = os.path.join(output_folder, filename + extension)
                    print(f"✓ Render duration: {render_duration:.2f} seconds")

                # Blender automatically saves the file, check multiple possible paths
                possible_paths = [
                    full_output_path,  # Our expected path
                    filepath_without_ext + extension,  # Path without extension + extension
                    filepath_without_ext + extension.upper(),  # Uppercase extension
                ]
                
                # Add frame number variations (Blender might add frame numbers)
                for base_path in [full_output_path, filepath_without_ext + extension]:
                    possible_paths.append(base_path.replace(extension, f"_{frame_num:04d}{extension}"))
                    possible_paths.append(base_path.replace(extension, f"{frame_num:04d}{extension}"))
                
                file_found = False
                actual_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        file_found = True
                        actual_path = path
                        saved_paths.append(path)
                        print(f"✓ Saved {channel_name} to: {path}")
                        break
                
                if not file_found:
                    # Last resort - try manual save
                    success = save_render_result(scene, full_output_path)
                    if success and os.path.exists(full_output_path):
                        saved_paths.append(full_output_path)
                        print(f"✓ Manually saved {channel_name} to: {full_output_path}")
                    else:
                        print(f"❌ Failed to save {channel_name}")
                        print(f"   Expected at: {full_output_path}")
                        print(f"   Tried paths: {possible_paths}")
                
                # Restore compositor state
                restore_compositor_state(scene, original_compositor_state)

            # Restore original filepath and format
            render.filepath = original_filepath
            if format_switched:
                try:
                    render.image_settings.file_format = original_format
                except Exception:
                    pass

            if saved_paths:
                self.report({'INFO'}, f"Saved {len(saved_paths)} channel(s) for current frame")
                return {'FINISHED'}
            else:   
                self.report({'WARNING'}, "Render completed but could not confirm output files")
                return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error rendering current frame: {str(e)}")
            return {'CANCELLED'}


class RENDER_OT_browse_output_folder(Operator):
    """Open the output folder in file explorer"""
    bl_idname = "render.browse_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the configured output folder in your file explorer"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global output_folder_path
        try:
            blend_filepath = bpy.data.filepath
            
            # Determine output folder
            if output_folder_path.strip():
                folder_to_open = bpy.path.abspath(output_folder_path.strip())
            else:
                if blend_filepath:
                    folder_to_open = os.path.dirname(bpy.path.abspath(blend_filepath))
                else:
                    folder_to_open = os.getcwd()

            # Check if folder exists
            if not os.path.exists(folder_to_open):
                self.report({'ERROR'}, f"Output folder does not exist: {folder_to_open}")
                return {'CANCELLED'}

            # Open the folder using platform-specific method
            import subprocess
            import platform

            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(folder_to_open)
                elif system == "Darwin":  # macOS
                    subprocess.Popen(["open", folder_to_open])
                else:  # Linux and others
                    subprocess.Popen(["xdg-open", folder_to_open])
                
                self.report({'INFO'}, f"Opened folder: {folder_to_open}")
                return {'FINISHED'}
            
            except Exception as e:
                self.report({'ERROR'}, f"Could not open folder: {e}")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error opening output folder: {str(e)}")
            return {'CANCELLED'}


class RENDER_OT_open_output_folder(Operator):
    """Open the rendered image file for the current frame"""
    bl_idname = "render.open_output_folder"
    bl_label = "Open Rendered Frame Result"
    bl_description = "Open the rendered image file for the current frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global output_folder_path
        try:
            scene = context.scene
            blend_filepath = bpy.data.filepath
            
            # Determine output folder
            if output_folder_path.strip():
                folder_to_open = bpy.path.abspath(output_folder_path.strip())
            else:
                if blend_filepath:
                    folder_to_open = os.path.dirname(bpy.path.abspath(blend_filepath))
                else:
                    folder_to_open = os.getcwd()

            # Check if folder exists
            if not os.path.exists(folder_to_open):
                self.report({'ERROR'}, f"Output folder does not exist: {folder_to_open}")
                return {'CANCELLED'}

            # Get current frame file info for better user feedback
            if blend_filepath:
                blend_name = os.path.splitext(os.path.basename(blend_filepath))[0]
            else:
                blend_name = "untitled"
            
            frame_num = scene.frame_current
            camera_name = "NoCamera"
            if scene.camera:
                camera_name = scene.camera.name

            # Get view layer name
            view_layer_name = scene.view_layers[0].name if scene.view_layers else "ViewLayer"

            # Determine file extension from render settings
            fmt = scene.render.image_settings.file_format.lower()
            if fmt == 'png':
                extension = '.png'
            elif fmt == 'jpeg':
                extension = '.jpg'
            elif fmt == 'tiff':
                extension = '.tif'
            elif fmt == 'exr':
                extension = '.exr'
            else:
                extension = '.png'

            # Generate expected filename using the current pattern
            from datetime import datetime
            global filename_pattern
            expected_filename_base = generate_filename_from_pattern(
                filename_pattern,
                blend_name,
                camera_name,
                frame_num,
                start_time=datetime.now(),  # We don't know the exact render time, use current
                end_time=datetime.now(),
                view_layer_name=view_layer_name
            )
            expected_filename = expected_filename_base + extension
            expected_filepath = os.path.join(folder_to_open, expected_filename)

            # Console info
            print("\n" + "=" * 60)
            print("�️  OPENING RENDERED FRAME RESULT")
            print(f"Current timeline frame: {frame_num}")
            print(f"Looking for file: {expected_filename}")
            print(f"Full path: {expected_filepath}")
            
            # Check if the rendered file exists
            if not os.path.exists(expected_filepath):
                # Try alternative extensions/formats that might exist
                alternative_files = []
                base_name = expected_filename_base  # Use the pattern-generated base name
                common_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.bmp']
                
                for ext in common_extensions:
                    alt_path = os.path.join(folder_to_open, base_name + ext)
                    if os.path.exists(alt_path):
                        alternative_files.append(alt_path)
                
                if alternative_files:
                    expected_filepath = alternative_files[0]  # Use the first found file
                    expected_filename = os.path.basename(expected_filepath)
                    print(f"✓ Found alternative: {expected_filename}")
                else:
                    print(f"❌ File not found: {expected_filename}")
                    print("=" * 60 + "\n")
                    self.report({'ERROR'}, f"Rendered frame not found: {expected_filename}. Please render frame {frame_num} first.")
                    return {'CANCELLED'}
            else:
                print(f"✓ File exists: {expected_filename}")
            
            print("=" * 60 + "\n")

            # Open the specific image file using platform-specific method
            import subprocess
            import platform

            system = platform.system()
            try:
                if system == "Windows":
                    # Use the default program to open the image file
                    subprocess.run(['start', '', expected_filepath], shell=True, check=True)
                elif system == "Darwin":  # macOS
                    subprocess.run(['open', expected_filepath], check=True)
                elif system == "Linux":
                    subprocess.run(['xdg-open', expected_filepath], check=True)
                else:
                    self.report({'ERROR'}, f"Unsupported operating system: {system}")
                    return {'CANCELLED'}

                # Success message
                self.report({'INFO'}, f"Opened rendered frame: {expected_filename}")
                return {'FINISHED'}

            except subprocess.CalledProcessError as e:
                self.report({'ERROR'}, f"Failed to open image file: {e}")
                return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Error opening image file: {e}")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error opening rendered frame result: {str(e)}")
            return {'CANCELLED'}


class RENDER_OT_set_viewport_focal_length(Operator):
    """Change the 3D viewport focal length"""
    bl_idname = "render.set_viewport_focal_length"
    bl_label = "Set Viewport Focal Length"
    bl_description = "Change the focal length of the 3D viewport"
    bl_options = {'REGISTER', 'UNDO'}
    
    focal_length: EnumProperty(
        name="Focal Length",
        description="Select viewport focal length in mm",
        items=[
            ('12', "12mm", "Ultra wide angle"),
            ('16', "16mm", "Wide angle"),
            ('24', "24mm", "Wide angle"),
            ('28', "28mm", "Wide angle"),
            ('35', "35mm", "Standard wide"),
            ('50', "50mm", "Standard"),
            ('70', "70mm", "Portrait"),
            ('85', "85mm", "Portrait"),
            ('135', "135mm", "Telephoto"),
            ('200', "200mm", "Telephoto"),
        ],
        default='50'
    )
    
    def execute(self, context):
        space = get_active_3d_view()
        if space:
            focal_value = float(self.focal_length)
            space.lens = focal_value
            self.report({'INFO'}, f"Viewport focal length set to {focal_value}mm")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No 3D viewport found")
            return {'CANCELLED'}


class CAMERA_OT_dof_distance_pick(Operator):
    """Pick DOF focus distance using eyedropper"""
    bl_idname = "camera.dof_distance_pick"
    bl_label = "DOF Distance (Pick) New"
    bl_description = "Pick focus distance from 3D viewport using eyedropper"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    _camera = None
    _initial_distance = None
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # Check if the DOF distance has changed
            if self._camera and self._camera.data.dof.focus_distance != self._initial_distance:
                # Distance was changed by eyedropper, check if we should keyframe
                if context.scene.frh_camera_keyframe:
                    # Add keyframe on dof.focus_distance
                    self._camera.data.dof.keyframe_insert(data_path="focus_distance")
                    self.report({'INFO'}, f"DOF distance set and keyframed at frame {context.scene.frame_current}")
                else:
                    self.report({'INFO'}, f"DOF distance set to {self._camera.data.dof.focus_distance:.2f}")
                
                # Clean up and finish
                self.cancel(context)
                return {'FINISHED'}
        
        # Check if eyedropper was cancelled
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
    
    def execute(self, context):
        # Get active camera
        camera = context.scene.camera
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera in scene")
            return {'CANCELLED'}
        
        # Store camera and initial distance
        self._camera = camera
        self._initial_distance = camera.data.dof.focus_distance
        
        # Add timer for modal operation
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        # Invoke the depth eyedropper
        bpy.ops.ui.eyedropper_depth('INVOKE_DEFAULT')
        
        return {'RUNNING_MODAL'}


class CAMERA_OT_focal_length_adjust(Operator):
    """Adjust camera focal length with mouse"""
    bl_idname = "camera.focal_length_adjust"
    bl_label = "Camera Focal Length"
    bl_description = "Adjust camera focal length interactively with mouse (photographer.focal)"
    bl_options = {'REGISTER', 'UNDO'}
    
    _initial_mouse_x = None
    _initial_focal = None
    _camera = None
    
    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            # Calculate the delta from initial mouse position
            delta = (event.mouse_x - self._initial_mouse_x) * 0.1
            
            # Update focal length
            new_focal = max(1.0, self._initial_focal + delta)
            
            # Update photographer.focal property
            if hasattr(self._camera.data, 'photographer') and hasattr(self._camera.data.photographer, 'focal'):
                self._camera.data.photographer.focal = new_focal
            else:
                # Fallback to data.lens if photographer addon not available
                self._camera.data.lens = new_focal
            
            # Update header text
            context.area.header_text_set(f"Camera Focal Length: {new_focal:.1f}mm")
            
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Confirm and finish
            context.area.header_text_set(None)
            
            # Add keyframe if toggle is on
            if context.scene.frh_camera_keyframe:
                if hasattr(self._camera.data, 'photographer') and hasattr(self._camera.data.photographer, 'focal'):
                    self._camera.data.photographer.keyframe_insert(data_path="focal")
                else:
                    self._camera.data.keyframe_insert(data_path="lens")
            
            return {'FINISHED'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel and restore original value
            if hasattr(self._camera.data, 'photographer') and hasattr(self._camera.data.photographer, 'focal'):
                self._camera.data.photographer.focal = self._initial_focal
            else:
                self._camera.data.lens = self._initial_focal
            
            context.area.header_text_set(None)
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        # Get active camera
        camera = context.scene.camera
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera in scene")
            return {'CANCELLED'}
        
        self._camera = camera
        self._initial_mouse_x = event.mouse_x
        
        # Get initial focal length from photographer.focal or data.lens
        if hasattr(camera.data, 'photographer') and hasattr(camera.data.photographer, 'focal'):
            self._initial_focal = camera.data.photographer.focal
        else:
            self._initial_focal = camera.data.lens
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        
        # Set initial header text
        context.area.header_text_set(f"Camera Focal Length: {self._initial_focal:.1f}mm")
        
        return {'RUNNING_MODAL'}


class VIEW3D_MT_camera_dof_menu(bpy.types.Menu):
    """Camera DOF helper menu"""
    bl_label = "DOF Distance"
    bl_idname = "VIEW3D_MT_camera_dof_menu"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("camera.dof_distance_pick", icon='EYEDROPPER')


def camera_context_menu_draw(self, context):
    """Draw function to add to camera context menu"""
    prefs = get_addon_preferences()
    if prefs and prefs.enable_camera_helpers:
        layout = self.layout
        layout.separator()
        layout.operator("camera.focal_length_adjust", icon='OUTLINER_OB_CAMERA')
        layout.operator("camera.dof_distance_pick", icon='EYEDROPPER')


def viewport_header_draw(self, context):
    """Draw function to add to 3D viewport header"""
    prefs = get_addon_preferences()
    if prefs and prefs.enable_camera_helpers:
        # Only show if there's an active camera
        if context.scene.camera and context.scene.camera.type == 'CAMERA':
            layout = self.layout
            layout.separator()
            layout.operator("camera.focal_length_adjust", text="", icon='OUTLINER_OB_CAMERA')
            layout.prop(context.scene, "frh_camera_keyframe", text="", icon='DECORATE_KEYFRAME', toggle=True)
            layout.operator("camera.dof_distance_pick", text="", icon='EYEDROPPER')


class RENDER_OT_suggest_keyframes(Operator):
    """Scan the dope sheet and suggest frames with keyframes"""
    bl_idname = "render.suggest_keyframes"
    bl_label = "Suggest Keyframes"
    bl_description = "Scan objects' keyframes and populate the frame numbers field"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Property to receive current frame list from the render operator
    current_frames: StringProperty(
        name="Current Frames",
        description="Current frame list to respect min/max values",
        default=""
    )
    
    # Property to control whether to scan only selected objects
    selected_only: BoolProperty(
        name="Selected Objects Only",
        description="Scan keyframes from selected objects only (faster and more accurate)",
        default=False
    )
    
    def execute(self, context):
        scene = context.scene
        
        # Parse current_frames to get min and max values
        frame_range_min = None
        frame_range_max = None
        
        if self.current_frames.strip():
            try:
                frame_numbers = []
                frame_string = self.current_frames.strip()
                
                # Parse the frame list (same logic as the render operator)
                for frame_str in frame_string.split(','):
                    frame_str = frame_str.strip()
                    if frame_str:
                        try:
                            # Check if it's a range (contains hyphen)
                            if '-' in frame_str:
                                # Handle range like "1-5" or "10-20"
                                range_parts = frame_str.split('-')
                                if len(range_parts) == 2:
                                    start_frame = int(range_parts[0].strip())
                                    end_frame = int(range_parts[1].strip())
                                    if start_frame <= end_frame:
                                        frame_numbers.extend(range(start_frame, end_frame + 1))
                            else:
                                # Single frame number
                                frame_num = int(frame_str)
                                frame_numbers.append(frame_num)
                        except ValueError:
                            pass  # Skip invalid entries
                
                if frame_numbers:
                    frame_range_min = min(frame_numbers)
                    frame_range_max = max(frame_numbers)
                    print(f"Using existing frame range: {frame_range_min} - {frame_range_max}")
            except Exception as e:
                print(f"Could not parse current frames: {e}")
                # Continue without range limitation
        
        # Store original frame to restore later
        original_frame = scene.frame_current
        
        try:
            keyframes = set()
            
            # Helper function to iterate FCurves from action with slot support (Blender 5.0)
            def iter_slot_fcurves(action, slot):
                """Yield all FCurves in this action that belong to the given slot."""
                if not action:
                    return

                # Layered actions path (5.0+)
                if hasattr(action, "layers"):
                    for layer in action.layers:
                        for strip in layer.strips:
                            # Only keyframe strips store fcurves
                            if strip.type != 'KEYFRAME':
                                continue

                            # If slot is provided, get channelbag for this slot
                            if slot:
                                try:
                                    cb = strip.channelbag(slot, ensure=False)
                                    if cb:
                                        for fc in cb.fcurves:
                                            yield fc
                                except Exception:
                                    # Fallback: iterate all channelbags on the strip and match by slot
                                    for bag in strip.channelbags:
                                        if bag.slot == slot:
                                            for fc in bag.fcurves:
                                                yield fc
                            else:
                                # No slot provided, iterate all channelbags
                                for bag in strip.channelbags:
                                    for fc in bag.fcurves:
                                        yield fc

                # Legacy fallback (Blender 4.x and earlier)
                else:
                    fcurves = getattr(action, "fcurves", [])
                    for fc in fcurves:
                        yield fc

            # Helper function to get keyframes from action (Blender 4.x and 5.0)
            def get_keyframes_from_action(action, obj=None):
                """Extract keyframe frame numbers from an action, handling both Blender 4.x and 5.0"""
                frames = set()
                
                # Try Blender 4.x style first - direct fcurves access
                if hasattr(action, 'fcurves') and not callable(action.fcurves):
                    try:
                        fcurve_count = len(action.fcurves)
                        if fcurve_count > 0:
                            print(f"    Found {fcurve_count} fcurves (Blender 4.x style)")
                            for fcurve in action.fcurves:
                                for keyframe_point in fcurve.keyframe_points:
                                    try:
                                        # Try co.x first (newer style)
                                        frame = round(keyframe_point.co.x)
                                    except AttributeError:
                                        # Fall back to co[0] (older style)
                                        frame = int(keyframe_point.co[0])
                                    frames.add(frame)
                            if frames:
                                print(f"    Extracted {len(frames)} unique keyframes from fcurves")
                                return frames
                    except Exception as e:
                        print(f"    Failed to access fcurves directly: {e}")
                
                # Try Blender 5.0 layered animation system with slots
                if hasattr(action, "layers"):
                    print(f"    Detected Blender 5.0 layered animation system")
                    
                    # Get the slot for this object if available (Blender 5.0)
                    slot = None
                    if obj and hasattr(obj, 'animation_data'):
                        slot = getattr(obj.animation_data, "action_slot", None)
                    
                    # Use the slot-aware iterator to get fcurves
                    try:
                        fcurve_count = 0
                        for fcurve in iter_slot_fcurves(action, slot):
                            fcurve_count += 1
                            for keyframe_point in fcurve.keyframe_points:
                                try:
                                    frame = round(keyframe_point.co.x)
                                except AttributeError:
                                    frame = int(keyframe_point.co[0])
                                frames.add(frame)
                        
                        if fcurve_count > 0:
                            print(f"    Found {fcurve_count} fcurves with {len(frames)} unique keyframes")
                            return frames
                    except Exception as e:
                        print(f"    Error accessing fcurves via slots: {e}")
                
                return frames
            
            # Collect keyframes from all objects in the scene
            def collect_keyframes_from_object(obj):
                """Recursively collect all keyframes from an object's animation data"""
                frames = set()
                
                # Check if object has animation data
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action
                    print(f"  Checking object '{obj.name}' with action '{action.name}'")
                    obj_frames = get_keyframes_from_action(action, obj)
                    frames.update(obj_frames)
                
                # Check object data animation (e.g., shape keys, mesh animation)
                if hasattr(obj, 'data') and obj.data and hasattr(obj.data, 'animation_data') and obj.data.animation_data:
                    if obj.data.animation_data.action:
                        action = obj.data.animation_data.action
                        print(f"  Checking object data '{obj.name}.data' with action '{action.name}'")
                        obj_frames = get_keyframes_from_action(action, obj.data)
                        frames.update(obj_frames)
                
                # Check material animation
                if hasattr(obj, 'material_slots'):
                    for mat_slot in obj.material_slots:
                        if mat_slot.material and mat_slot.material.animation_data:
                            if mat_slot.material.animation_data.action:
                                action = mat_slot.material.animation_data.action
                                print(f"  Checking material '{mat_slot.material.name}' with action '{action.name}'")
                                mat_frames = get_keyframes_from_action(action, mat_slot.material)
                                frames.update(mat_frames)
                
                return frames
            
            # Collect keyframes from objects
            object_keyframes = {}
            
            # Determine which objects to scan
            if self.selected_only:
                objects_to_scan = [obj for obj in context.selected_objects]
                if not objects_to_scan:
                    self.report({'WARNING'}, "No objects selected. Please select objects or uncheck 'Selected Objects Only'.")
                    return {'CANCELLED'}
                print(f"Scanning {len(objects_to_scan)} selected objects for keyframes...")
            else:
                objects_to_scan = scene.objects
                print(f"Scanning all {len(objects_to_scan)} objects in scene for keyframes...")
            
            for obj in objects_to_scan:
                obj_frames = collect_keyframes_from_object(obj)
                if obj_frames:
                    object_keyframes[obj.name] = sorted(list(obj_frames))
                    keyframes.update(obj_frames)
            
            # Also check scene animation data (world, scene properties, etc.)
            if scene.animation_data and scene.animation_data.action:
                action = scene.animation_data.action
                print(f"  Checking scene animation with action '{action.name}'")
                scene_frames = get_keyframes_from_action(action, scene)
                keyframes.update(scene_frames)
            
            # Check world animation
            if scene.world and scene.world.animation_data and scene.world.animation_data.action:
                action = scene.world.animation_data.action
                print(f"  Checking world animation with action '{action.name}'")
                world_frames = get_keyframes_from_action(action, scene.world)
                keyframes.update(world_frames)
            
            # Filter keyframes based on existing frame range or scene frame range
            if frame_range_min is not None and frame_range_max is not None:
                # Use the min/max from existing frame list
                frame_start = frame_range_min
                frame_end = frame_range_max
                filter_source = "existing frame list"
            else:
                # Use scene frame range as fallback
                frame_start = scene.frame_start
                frame_end = scene.frame_end
                filter_source = "scene frame range"
            
            filtered_keyframes = {frame for frame in keyframes if frame_start <= frame <= frame_end}
            
            # Debug output
            print(f"=== Keyframe Collection Debug Info ===")
            print(f"Filter source: {filter_source}")
            print(f"Filter range: {frame_start} - {frame_end}")
            print(f"Scene frame range: {scene.frame_start} - {scene.frame_end}")
            print(f"Objects with keyframes: {len(object_keyframes)}")
            for obj_name, frames in object_keyframes.items():
                print(f"  {obj_name}: {frames}")
            print(f"Total unique keyframes found: {len(keyframes)}")
            print(f"All keyframes: {sorted(list(keyframes))}")
            print(f"Filtered keyframes: {sorted(list(filtered_keyframes))}")
            
            if filtered_keyframes:
                # Sort keyframes and create comma-separated string
                sorted_keyframes = sorted(list(filtered_keyframes))
                keyframe_string = ','.join(map(str, sorted_keyframes))
                
                # Store keyframes directly in the scene property
                scene.frh_frame_list = keyframe_string
                
                range_info = f" (limited to range {frame_start}-{frame_end})" if filter_source == "existing frame list" else ""
                source_info = "selected objects" if self.selected_only else f"{len(object_keyframes)} objects"
                self.report({'INFO'}, f"Found {len(sorted_keyframes)} keyframes from {source_info}{range_info}: {keyframe_string[:80]}{'...' if len(keyframe_string) > 80 else ''}")
                
                return {'FINISHED'}
            else:
                range_info = f" in range {frame_start}-{frame_end}" if filter_source == "existing frame list" else ""
                source_info = "selected objects" if self.selected_only else "scene"
                self.report({'WARNING'}, f"No keyframes found in {source_info}{range_info}")
                return {'CANCELLED'}
        
        finally:
            # Restore original frame
            scene.frame_set(original_frame)
    
    def invoke(self, context, event):
        # Check if holding Shift key - if so, show options dialog
        if event.shift:
            return context.window_manager.invoke_props_dialog(self, width=400)
        else:
            # Quick execution without dialog
            return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Keyframe Detection Options:", icon='SETTINGS')
        layout.separator()
        
        layout.prop(self, "selected_only")
        
        layout.separator()
        box = layout.box()
        box.label(text="Quick Access:", icon='INFO')
        box.label(text="• Click icon = Scan all objects")
        box.label(text="• Shift+Click = Show this dialog")
        
        if self.selected_only:
            layout.separator()
            selected_count = len(context.selected_objects)
            if selected_count > 0:
                layout.label(text=f"Will scan {selected_count} selected object(s)", icon='CHECKMARK')
            else:
                layout.label(text="⚠ No objects selected!", icon='ERROR')


class RENDER_PT_specific_frames_panel(Panel):
    """Panel for rendering specific frames"""
    bl_label = "Furion Render Helper"
    bl_idname = "RENDER_PT_specific_frames"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):    
        global output_folder_path
        layout = self.layout

        # Output folder section
        col = layout.column(align=True)
        col.label(text="Output Folder Settings:")

        # Show storage source info
        source = get_output_path_source()
        source_box = col.box()
        if source == 'SCENE_PROPS':
            source_box.label(text="Storage: Scene Properties (per-project)", icon='SCENE_DATA')
        else:
            source_box.label(text="Storage: User Preferences (global)", icon='PREFERENCES')

        if output_folder_path:
            col.label(text=f"Current: {os.path.basename(output_folder_path)}", icon='FOLDER_REDIRECT')
            col.label(text=f"Path: {output_folder_path}")
        else:
            col.label(text="Current: (Blend file directory)", icon='FOLDER_REDIRECT')
            col.label(text="(No default folder set)", icon='INFO')

        # Buttons for setting and opening output folder
        row = col.row(align=True)
        row.operator("render.set_output_folder", text="Set Output Folder", icon='FILE_FOLDER')
        row.operator("render.browse_output_folder", text="Open Folder", icon='FOLDER_REDIRECT')

        # Filename pattern section
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Filename Pattern Settings:")
        
        global filename_pattern
        if filename_pattern:
            # Show current pattern with truncation if too long
            display_pattern = filename_pattern if len(filename_pattern) <= 35 else filename_pattern[:32] + "..."
            col.label(text=f"Current: {display_pattern}", icon='FILE_TEXT')
            
            # Show a preview of what the filename would look like
            try:
                # Generate preview filename
                blend_name = "MyProject" if not bpy.data.filepath else os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                camera_name = context.scene.camera.name if context.scene.camera else "Camera"
                view_layer_name = context.scene.view_layers[0].name if context.scene.view_layers else "ViewLayer"
                frame_num = context.scene.frame_current
                from datetime import datetime
                
                # Show preview with different channels if multiple selected
                selected_channels = get_selected_channels(context.scene)
                if len(selected_channels) > 1:
                    # Show preview for first channel
                    channel_name = selected_channels[0][0]
                    preview_filename = generate_filename_from_pattern(
                        filename_pattern,
                        blend_name,
                        camera_name,
                        frame_num,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        channel_name=channel_name,
                        view_layer_name=view_layer_name
                    )
                    col.label(text=f"Preview: {preview_filename}.png", icon='PREVIEW_RANGE')
                    col.label(text=f"(+ {len(selected_channels)-1} more channels)", icon='INFO')
                else:
                    # Single channel or default
                    channel_name = selected_channels[0][0] if selected_channels else "Combined"
                    preview_filename = generate_filename_from_pattern(
                        filename_pattern,
                        blend_name,
                        camera_name,
                        frame_num,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        channel_name=channel_name,
                        view_layer_name=view_layer_name
                    )
                    col.label(text=f"Preview: {preview_filename}.png", icon='PREVIEW_RANGE')
            except Exception:
                col.label(text="Preview: (Pattern error)", icon='ERROR')
        else:
            col.label(text="Current: (Default pattern)", icon='FILE_TEXT')
        
        col.operator("render.set_filename_pattern", text="Customize Filename Pattern", icon='PROPERTIES')

        # Render Channels section - Show enabled passes from Blender's view layer
        layout.separator()
        scene = context.scene
        selected_channels = get_selected_channels(scene)
        num_selected = len(selected_channels)
        
        # Compact channel info
        row = layout.row(align=True)
        row.label(text=f"Output Channels: {num_selected}", icon='RENDERLAYERS')
        if num_selected <= 10:
            channel_names = [ch[0] for ch in selected_channels]
            row.label(text=f"({', '.join(channel_names)})")
        
        # Warning for multi-channel without (Channel) token
        if num_selected > 1 and "(Channel)" not in filename_pattern:
            row = layout.row()
            row.alert = True
            row.label(text="Add (Channel) token to pattern for multi-pass, only the first pass will be handled now", icon='ERROR')

        # Rendering section
        layout.separator()
        layout.label(text="Render Frames:")
        layout.operator("render.specific_frames", text="Render Specific Frames", icon='RENDER_STILL')
        layout.operator("render.current_frame", text="Render Current Frame", icon='RENDER_STILL')
        layout.operator("render.open_output_folder", text="Open Rendered Frame Result", icon='IMAGE_DATA')

        # Viewport Settings section
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Viewport Settings:", icon='VIEW3D')
        
        # Get current viewport focal length
        current_space = get_active_3d_view()
        if current_space:
            current_lens = current_space.lens
            col.label(text=f"Current Focal Length: {current_lens:.1f}mm", icon='CAMERA_DATA')
        
        # Dropdown menu for focal length
        col.operator_menu_enum("render.set_viewport_focal_length", "focal_length", text="Set Viewport Focal Length", icon='OUTLINER_OB_CAMERA')

        # Tips section with toggle button
        layout.separator()
        row = layout.row()
        
        # Toggle button for tips visibility
        icon = 'TRIA_DOWN' if context.scene.frh_show_tips else 'TRIA_RIGHT'
        row.prop(context.scene, "frh_show_tips", text="Tips", icon=icon, toggle=True)
        
        # Show tips only if enabled
        if context.scene.frh_show_tips:
            # Header/info
            box = layout.box()
            box.label(text="Furion Render Helper", icon='RENDER_ANIMATION')
            box.label(text="Step 1: Set output folder and filename pattern (optional)")
            box.label(text="Step 2: Choose frames to render")
            
            layout.separator()
            tips = layout.column(align=True)
            tips.label(text="• Default folder and filename pattern are saved in preferences")
            tips.label(text="• Filename tokens: (FileName), (Camera), (Frame), (Channel)")
            tips.label(text="• Date/time tokens: (Start:yyyyMMdd), (End:HHmmss)")
            tips.label(text="• (Channel) token required when multiple passes selected")
            tips.label(text="• Enter frames separated by commas")
            tips.label(text="• Single frames: 1,5,10,25,50")
            tips.label(text="• Ranges: 1-5,10-15,30 (inclusive)")
            tips.label(text="• Mixed: 1,5-10,15,20-25")
            tips.label(text="• Duplicates will be removed")


def register():
    bpy.utils.register_class(FurionRenderHelperPreferences)
    bpy.utils.register_class(RENDER_OT_set_output_folder)
    bpy.utils.register_class(RENDER_OT_browse_output_folder)
    bpy.utils.register_class(RENDER_OT_set_filename_pattern)
    bpy.utils.register_class(RENDER_OT_specific_frames)
    bpy.utils.register_class(RENDER_OT_current_frame)
    bpy.utils.register_class(RENDER_OT_open_output_folder)
    bpy.utils.register_class(RENDER_OT_set_viewport_focal_length)
    bpy.utils.register_class(CAMERA_OT_focal_length_adjust)
    bpy.utils.register_class(CAMERA_OT_dof_distance_pick)
    bpy.utils.register_class(VIEW3D_MT_camera_dof_menu)
    bpy.utils.register_class(RENDER_OT_suggest_keyframes)
    bpy.utils.register_class(RENDER_PT_specific_frames_panel)
    
    # Add camera context menu item
    bpy.types.VIEW3D_MT_object_context_menu.append(camera_context_menu_draw)
    
    # Add viewport header button
    bpy.types.VIEW3D_HT_header.append(viewport_header_draw)
    
    # Register scene properties
    bpy.types.Scene.frh_show_tips = BoolProperty(
        name="Show Tips",
        description="Toggle visibility of tips section",
        default=False
    )
    
    bpy.types.Scene.frh_frame_list = StringProperty(
        name="Frame Numbers",
        description="Enter frame numbers separated by commas (e.g., 1,5,10,25) or ranges (e.g., 1-5,10-15)",
        default=""
    )
    
    bpy.types.Scene.frh_camera_keyframe = BoolProperty(
        name="Add Camera Keyframe",
        description="Automatically add keyframe when picking DOF distance",
        default=False
    )
    
    # Add handler to reload output folder when file is loaded
    bpy.app.handlers.load_post.append(on_file_load)
    
    # Load saved preferences
    load_user_preferences()


def unregister():
    # Remove viewport header button
    bpy.types.VIEW3D_HT_header.remove(viewport_header_draw)
    
    # Remove camera context menu item
    bpy.types.VIEW3D_MT_object_context_menu.remove(camera_context_menu_draw)
    
    # Remove handler
    if on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load)
    
    # Unregister scene properties
    del bpy.types.Scene.frh_show_tips
    del bpy.types.Scene.frh_frame_list
    del bpy.types.Scene.frh_camera_keyframe
    
    bpy.utils.unregister_class(FurionRenderHelperPreferences)
    bpy.utils.unregister_class(RENDER_OT_set_output_folder)
    bpy.utils.unregister_class(RENDER_OT_browse_output_folder)
    bpy.utils.unregister_class(RENDER_OT_set_filename_pattern)
    bpy.utils.unregister_class(RENDER_OT_specific_frames)
    bpy.utils.unregister_class(RENDER_OT_current_frame)
    bpy.utils.unregister_class(RENDER_OT_open_output_folder)
    bpy.utils.unregister_class(RENDER_OT_set_viewport_focal_length)
    bpy.utils.unregister_class(CAMERA_OT_focal_length_adjust)
    bpy.utils.unregister_class(CAMERA_OT_dof_distance_pick)
    bpy.utils.unregister_class(VIEW3D_MT_camera_dof_menu)
    bpy.utils.unregister_class(RENDER_OT_suggest_keyframes)
    bpy.utils.unregister_class(RENDER_PT_specific_frames_panel)


if __name__ == "__main__":
    register()


