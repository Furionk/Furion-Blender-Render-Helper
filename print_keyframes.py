import bpy

def iter_slot_fcurves(action, slot):
    """Yield all FCurves in this action that belong to the given slot."""
    if not action or not slot:
        return

    # Layered actions path (5.0+)
    if getattr(action, "layers", None):
        for layer in action.layers:
            for strip in layer.strips:
                # Only keyframe strips store fcurves
                if strip.type != 'KEYFRAME':
                    continue

                # Preferred lookup: get channelbag for this slot on this strip
                cb = strip.channelbag(slot, ensure=False)
                if cb:
                    for fc in cb.fcurves:
                        yield fc
                else:
                    # Fallback: iterate all channelbags on the strip and match by slot
                    for bag in strip.channelbags:
                        if bag.slot == slot:
                            for fc in bag.fcurves:
                                yield fc

    # Legacy fallback (first slot only)
    else:
        for fc in getattr(action, "fcurves", []):
            yield fc

def unique_keyframe_frames(action, slot):
    """Get unique keyframe frame numbers from an action for a given slot."""
    frames = set()
    for fc in iter_slot_fcurves(action, slot):
        for kp in fc.keyframe_points:
            frames.add(round(kp.co.x))
    return frames

def print_keyframes():
    """Print all keyframe numbers in the current scene."""
    scene = bpy.context.scene
    all_keyframes = set()

    # Iterate through all objects in the scene
    for obj in scene.objects:
        anim = getattr(obj, "animation_data", None)
        if not anim:
            continue

        action = getattr(anim, "action", None)
        if not action:
            continue

        # Get the slot for this object
        slot = getattr(anim, "action_slot", None)
        
        # Collect keyframes using the Blender 5.0 API
        frames = unique_keyframe_frames(action, slot)
        all_keyframes.update(frames)

        # Also check NLA strips
        nla_tracks = getattr(anim, "nla_tracks", None)
        if nla_tracks:
            for track in nla_tracks:
                for strip in getattr(track, "strips", []):
                    strip_action = getattr(strip, "action", None)
                    if strip_action:
                        strip_frames = unique_keyframe_frames(strip_action, slot)
                        all_keyframes.update(strip_frames)

    # Scene-level animation data
    scene_anim = getattr(scene, "animation_data", None)
    if scene_anim:
        scene_action = getattr(scene_anim, "action", None)
        scene_slot = getattr(scene_anim, "action_slot", None)
        if scene_action:
            scene_frames = unique_keyframe_frames(scene_action, scene_slot)
            all_keyframes.update(scene_frames)

    # Output
    if all_keyframes:
        frames = sorted(all_keyframes)
        print(f"Total keyframes found: {len(frames)}")
        print(f"Keyframe numbers: {frames}")
    else:
        print("No keyframes found in the current scene.")

if __name__ == "__main__":
    print_keyframes()

print_keyframes()
