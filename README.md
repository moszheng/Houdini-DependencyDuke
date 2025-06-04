# Dependency Duke - Houdini Material Collector

A Python script for SideFX Houdini that automatically collects and organizes all external file dependencies from your scene, making your projects portable and self-contained.

## Features

- **Automatic File Discovery**: Scans all nodes in your Houdini scene for file references
- **Smart File Filtering**: Only collects files with specified extensions (textures, caches, etc.)
- **External File Management**: Automatically relocates files outside the `$HIP` directory to `$HIP/external`
- **Path Updating**: Updates all parameter paths to maintain proper file references
- **Preserve Directory Structure**: Maintains relative folder structure for internal files
- **Conflict Resolution**: Handles duplicate filenames automatically
- **Comprehensive Logging**: Detailed console output showing all operations

## Supported File Formats

### Texture Formats
- `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.exr`, `.hdr`, `.pic`, `.rat`
- `.tga`, `.bmp`, `.gif`, `.psd`, `.iff`, `.sgi`, `.rgba`, `.rgb`

### Cache Formats
- `.bgeo`, `.bgeo.sc`, `.geo`, `.abc`, `.fbx`, `.obj`, `.ply`
- `.vdb`, `.sim`, `.simdata`, `.pc`, `.pcd`

### USD/Alembic
- `.usd`, `.usda`, `.usdc`, `.usdz`

### Video/Audio
- `.mov`, `.mp4`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`
- `.wav`, `.mp3`, `.aac`, `.ogg`, `.flac`

### Other Formats
- `.lut`, `.cube`, `.3dl`, `.csp`, `.vf`, `.m3u8`

## How It Works

### Internal Files (within `$HIP` directory)
- Files are copied to the output folder maintaining their relative directory structure
- No parameter changes are made
- Original file paths remain valid

### External Files (outside `$HIP` directory)
- Files are copied to `output_folder/external/`
- Parameter paths are updated to `$HIP/external/filename`
- Scene is automatically saved with updated paths

## Installation

1. Save the script as `material_collector.py` in your Houdini scripts directory
2. Or run directly in Houdini's Python Shell

## Usage

### Basic Usage

```python
# Run in Houdini's Python Shell or Script Editor
exec(open('/path/to/material_collector.py').read())

# Or import and run
import material_collector
material_collector.collect_material_files()
```

### Step-by-Step Process

1. **Save Your Scene**: Make sure your Houdini scene is saved before running
2. **Run the Script**: Execute the script in Houdini's Python environment
3. **Select Output Folder**: Choose where to collect all files
4. **Review Results**: Check console output for detailed operation log

## Output Structure

```
Output_Folder/
├── your_scene.hip          # Updated Houdini scene file
├── external/               # External files relocated here
│   ├── texture1.png
│   ├── model1.fbx
│   └── ...
├── textures/              # Internal files (maintaining structure)
│   └── internal_tex.exr
├── geo/
│   └── cache.bgeo
└── ...
```

## Script Functions

### Core Functions
- `collect_material_files()`: Main function that orchestrates the collection process
- `is_target_file(file_path)`: Checks if a file matches target extensions
- `is_file_inside_hip(file_path, hip_dir)`: Determines if file is within HIP directory
- `get_output_folder(hip_dir)`: UI dialog for selecting output directory
- `copy_hip_file(hip_file_path, output_folder)`: Copies the Houdini scene file

### Customization
You can modify the `TARGET_EXTENSIONS` set at the top of the script to include or exclude specific file formats:

```python
TARGET_EXTENSIONS = {
    '.png', '.jpg', '.exr',  # Only collect these formats
    # Add or remove extensions as needed
}
```

## Console Output Example

```
✓ Moved external file: texture.png
  From: C:/Users/Desktop/textures/texture.png
  To: $HIP/external/texture.png
  Node: /obj/geo1/principledshader1

✗ Skipped: /obj/geo2/file1 (not target format)

Total files collected: 15
Total external files collected: 3
Total files skipped: 2
```

## Requirements

- SideFX Houdini (any recent version)
- Python environment within Houdini
- Write permissions for output directory

## Error Handling

- Checks file existence before attempting operations
- Continues processing even if individual nodes fail

## Important Notes

⚠️ **Scene Modification**: This script modifies your Houdini scene by updating file paths for external files. Make sure to backup your scene before running.

⚠️ **File Overwriting**: The script will overwrite existing files in the output folder if they have the same name.

⚠️ **Path Format**: External files are referenced using Houdini's `$HIP` variable format (`$HIP/external/filename`).

1. External Link: but not overwrite origin file?

## Troubleshooting

### Common Issues

1. **"Scene not saved" error**: Save your Houdini scene before running the script
2. **Permission errors**: Ensure you have write access to the output directory
3. **Missing files**: Check that all referenced files exist on disk
4. **Path issues**: Verify that file paths don't contain special characters