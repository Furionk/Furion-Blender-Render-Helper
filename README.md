# Furion Blender Render Helper

This is just a blender plugin for me to batch render with multi-channel output and customizable filename patterns.

## Version 1.4.3 (November 22, 2025)
- ✅ **Blender 5.0 Support** - Full compatibility with Blender 5.0's new layered animation system for keyframe detection
- ✅ **Backward Compatible** - Maintains support for Blender 4.x direct fcurves access
- ✅ **Persistent Frame List** - Frame numbers now persist across sessions (saved in scene data)
- 🔧 Fixed keyframe suggestion display issue 

![image](https://github.com/Furionk/FurionRenderHelper/blob/main/furion_render_helper.png)

## Key Features

- 🎯 **Batch Frame Rendering** - Batch render by typing frame ranges (e.g., `1,5,10-15,30`)
- 🔑 **Smart Keyframe Detection** - Auto-suggest keyframes for blocking stage renders. Supports both Blender 4.x and 5.0 animation systems. Intelligently extracts keyframes from the Dope Sheet, skipping interpolated frames. Respects your frame range: if you type `1-100`, only keyframes between 1 and 100 are included (keyframes at 100+ are filtered out). Frame numbers persist across sessions. Perfect for reviewing animation blocking without rendering unnecessary in-between frames.


- 🎨 **Multi-Channel Output** - Render multiple passes (Combined, Depth, Mist, Normal, etc.) in a single batch
- 📝 **Customizable Filenames** - Use flexible token patterns with date/time support
- 💾 **Persistent Settings** - Output folder and filename patterns are saved between sessions
- 🔀 **Flexible Storage** - Choose between global user preferences or per-project scene properties

## Quick Start

1. **Set Output Folder** - Click "Set Output Folder" or leave blank to use blend file directory
2. **Configure Storage** (Optional) - Go to Preferences > Add-ons > Furion Render Helper to choose:
   - **User Preferences**: Global output folder for all projects (default)
   - **Scene Properties**: Per-project output folder saved in blend file
3. **Enable Render Passes** - Go to View Layer Properties > Passes and enable desired outputs channels (optional)
4. **Configure Pattern** (Optional) - Use tokens like `(FileName)_(Frame)_(Channel)` for custom naming
5. **Enter Frames** - Type frame numbers: `1,5,10` or ranges: `1-5,10-15` or click keyframe icon
6. **Render** - Click "Render Specific Frames" or "Render Current Frame"

## Filename Tokens

| Token | Output | Notes |
|-------|--------|-------|
| `(FileName)` | `MyProject` | Blend file name |
| `(Camera)` | `Camera` | Scene camera name |
| `(ViewLayer)` | `ViewLayer` | View layer name |
| `(Frame)` | `0001` | Frame with padding |
| `(Channel)` | `Combined`, `Depth`, `Mist` | Render pass name (required for multi-pass) |
| `(Start:yyyyMMdd)` | `20251028` | Render start date/time |
| `(End:HHmmss)` | `172118` | Render end time |
| `(BatchStart:yyyyMMdd)` | `20251028` | Batch render start date/time |
| `(RenderDurationSeconds)` | `45.23` | Render duration in seconds |

### Date/Time Format
- `yyyy` = year, `MM` = month, `dd` = day, `HH` = hour, `mm` = minute, `ss` = second

### Example Patterns

```
(FileName)_(Camera)_frame_(Frame)
→ MyProject_Camera_frame_0001.png

(FileName)_(Frame)_(Channel)
→ MyProject_0001_Combined.png
→ MyProject_0001_Depth.png

(FileName)_(ViewLayer)_(Frame)_(Start:yyyyMMdd)
→ MyProject_Beauty_0001_20251028.png

(FileName)_(Frame)_(RenderDurationSeconds)s
→ MyProject_0001_45.23s.png

(FileName)_(BatchStart:yyyyMMdd)_(Frame)
→ MyProject_20251028_0001.png
```

## Multi-Channel Rendering

**Enable passes in Blender:**  
Properties > View Layer Properties > Passes > Data/Light sections

**Add `(Channel)` token when rendering multiple passes:**
- ✅ With token: Each pass saves separately  
  `MyProject_0001_Combined.png`, `MyProject_0001_Depth.png`
- ⚠️ Without token: Passes overwrite each other  
  `MyProject_0001.png` (only last pass saved)

## Output Folder Storage Options

Choose where to store your output folder path in **Preferences > Add-ons > Furion Render Helper**:

### User Preferences (Default)
- ✅ Global setting saved in Blender's config folder
- ✅ Same output folder across all blend files
- ✅ Perfect for solo artists with consistent folder structure
- Example: All projects render to `C:\Renders\`

### Scene Properties
- ✅ Per-project setting stored in blend file
- ✅ Each blend file can have its own output folder
- ✅ Perfect for studios, multiple clients, or project-specific workflows
- Example: ClientA renders to `D:\ClientA\Renders\`, ClientB to `D:\ClientB\Renders\`

**Tip:** The panel shows which mode is active with a badge (🎬 Scene Properties or ⚙️ User Preferences)

## Requirements

- Blender 4.2+ (tested with 4.x and 5.0)
- Supports Windows, macOS, Linux

## Location

Properties > Render Properties > **Furion Render Helper**

---

**License:** MIT
