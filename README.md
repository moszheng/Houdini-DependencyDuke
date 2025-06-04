# Dependency Duke - Houdini Assets Collector

A Python script for SideFX Houdini that automatically **collects, organizes, and relocates all external file dependencies** from your scene, making your projects portable and self-contained.

## Features

- **Automatic File Discovery**: Scans all nodes in your Houdini scene for file references
- **Preserve Directory Structure**: Maintains relative folder structure for internal files
- **External File Management**: Automatically relocates files outside the `$HIP` directory to `$HIP/external`
- **Path Updating**: Updates all parameter paths to maintain proper file references
- **Conflict Resolution**: Handles duplicate filenames automatically

## Installation

1. Make a shelf tool and paste the code.


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

## Requirements

- SideFX Houdini (any recent version)
- Python environment within Houdini
- Write permissions for output directory


## Troubleshooting

### Common Issues

1. **"Scene not saved" error**: Save your Houdini scene before running the script
2. **Permission errors**: Ensure you have write access to the output directory
3. **Missing files**: Check that all referenced files exist on disk
4. **Path issues**: Verify that file paths don't contain special characters