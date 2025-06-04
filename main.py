import hou
import os
import shutil
import re

# Define file extensions to collect
TARGET_EXTENSIONS = {
    # Texture formats
    '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.exr', '.hdr', '.pic', '.rat',
    '.tga', '.bmp', '.gif', '.psd', '.iff', '.sgi', '.rgba', '.rgb',
    
    # Cache formats
    '.bgeo', '.bgeo.sc', '.geo', '.abc', '.fbx', '.obj', '.ply',
    '.vdb', '.sim', '.simdata', '.pc', '.pcd',
    
    # Alembic and USD
    '.usd', '.usda', '.usdc', '.usdz',
    
    # Video formats
    '.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    
    # Audio formats
    '.wav', '.mp3', '.aac', '.ogg', '.flac',
    
    # Other common formats
    '.lut', '.cube', '.3dl', '.csp', '.vf', '.m3u8'
}

def is_target_file(file_path):
    """Check if file has a target extension"""
    if not file_path:
        return False
    
    # Get file extension (convert to lowercase for comparison)
    _, ext = os.path.splitext(file_path.lower())
    
    # Handle special cases like .bgeo.sc
    if file_path.lower().endswith('.bgeo.sc'):
        return '.bgeo.sc' in TARGET_EXTENSIONS
    
    return ext in TARGET_EXTENSIONS

def is_frame_sequence(file_path):
    return re.search(r'\.\d{4,5}(\.\w+)+$', os.path.basename(file_path)) is not None

def get_sequence_files(path_pattern):
    path_pattern = hou.expandString(path_pattern)
    dir_path = os.path.dirname(path_pattern)
    base_name = os.path.basename(path_pattern)

    if '$F' in base_name or '#' in base_name:
        # 表達式或井字號情況
        frame_regex = re.sub(r'\$F\d*', r'\\d+', base_name)
        frame_regex = frame_regex.replace('#', r'\\d')
        regex = re.compile('^' + frame_regex + '$')
    else:
        # 雙重副檔名（ex. .0001.bgeo.sc）
        match = re.match(r'^(.*?)(\.\d{4,5})((?:\.\w+)+)$', base_name)
        if not match:
            return []
        prefix, _, suffix = match.groups()
        regex = re.compile('^' + re.escape(prefix) + r'\.\d{4,5}' + re.escape(suffix) + '$')

    return sorted([
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if regex.match(f)
    ])

def get_output_folder(hip_dir):
    # Ask output direction
    output_folder = hou.ui.selectFile(
        start_directory=hip_dir, # 預設開啟在 Houdini 檔案所在目錄
        title="Select Output Folder for Material Files",
        pattern="*", # 允許選擇任何資料夾
        collapse_sequences=False,
        file_type=hou.fileType.Directory
    )

    if not output_folder:
        print("Operation cancelled by user. No output folder selected.")
        hou.ui.displayMessage(
            "Collection cancelled. No output folder selected.",
            title="Houdini Material Collector"
        )
        return

    # Expand Houdini variables and normalize the path
    output_folder = hou.expandString(output_folder)
    output_folder = os.path.normpath(output_folder)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    return output_folder

def is_file_inside_hip(file_path, hip_dir):
    """Check if file is inside HIP directory"""
    try:
        # Get absolute paths for comparison
        abs_file_path = os.path.abspath(file_path)
        abs_hip_dir = os.path.abspath(hip_dir)
        
        # Check if file path starts with hip directory path
        return abs_file_path.startswith(abs_hip_dir)
    except:
        return False
    
def collect_file_parameters():
    """Collect all file reference parameters from all nodes."""
    file_parms = []
    skipped_rop_count = 0
    for node in hou.node('/').allNodes():
        try:
            if node.type().category().name() == "Driver":
                skipped_rop_count += 1
                continue
            
            for parm in node.parms():
                parm_template = parm.parmTemplate()
                # 確保 parm_template 存在，且它是 String 類型的參數模板
                # 使用 hou.parmTemplateType.String 來判斷參數基本類型
                if (parm_template is not None and 
                    parm_template.type() == hou.parmTemplateType.String and 
                    parm_template.stringType() == hou.stringParmType.FileReference):
                    file_parms.append((node, parm))
        except Exception as e:
            print(f"/---Error scanning node {node.path()}---/")
            print(f"Error: {e}")
            continue

    print(f"Found {len(file_parms)} file reference parameters to process...")
    if skipped_rop_count > 0:
        print(f"Skipped {skipped_rop_count} ROP nodes")
    return file_parms

def copy_hip_file(hip_file_path, output_folder):
    try:
        hip_file_name = os.path.basename(hip_file_path)
        base_name, ext = os.path.splitext(hip_file_name)
        destination_hip_path = os.path.join(output_folder, f"{base_name}_collected{ext}")
        hou.hipFile.save(file_name = destination_hip_path) #Save as

    except Exception as e:
        print(f"Error copying HIP file: {e}")
        return False

def collect_material_files():
    """
    遍歷 HIP 中的所有節點，收集引用的檔案。
    並將它們複製到使用者指定的資料夾，同時保留相對於 HIP 根目錄的結構。
    外連檔案會整合進 $HIP/external，並更新原始引用處的連結
    """
    try:
        hip_file_path = hou.hipFile.path() # 獲取當前 Houdini 檔案的路徑

        if not hip_file_path:
            print("Error: Current Houdini scene is not saved. Please save the file first.")
            return

        hip_dir = os.path.dirname(hip_file_path) # 獲取 Houdini 檔案所在的目錄作為根目錄
    
        # Get output folder
        output_folder = get_output_folder(hip_dir)
        if not output_folder:
            return

        # Collect files
        collected_files = set() # 用於追蹤已收集的檔案，避免重複複製
        skipped_files = set()
        external_collected_files = set() # 追蹤移動到 external 的檔案
        parameters_updated = [] # 追蹤更新的參數
        """
        Get all file reference parameters in one pass
        and Process all file parameters
        """
        for current_node, parm in collect_file_parameters():
            try:
                file_path = parm.eval()
                expanded_file_path = hou.expandString(file_path) # 考慮會有表達式

                if not expanded_file_path or not os.path.exists(expanded_file_path): # 檢查路徑是否有效且存在
                    continue
                    
                absolute_path = os.path.abspath(expanded_file_path) # 將路徑正規化，處理相對路徑等
                
                # Skip if already processed
                if absolute_path in collected_files or absolute_path in external_collected_files:
                    continue
                
                original_filename = os.path.basename(absolute_path)

                if not is_target_file(expanded_file_path): #
                    skipped_files.add(expanded_file_path)
                    print(f"✗ Skipped: {current_node.path()}")
                    continue

                if is_frame_sequence(file_path):

                    sequence_files = get_sequence_files(file_path)
                    for seq_file in sequence_files:
                        if not os.path.exists(seq_file):
                            continue
                        if seq_file in collected_files:
                            continue

                        relative_path = os.path.relpath(seq_file, hip_dir)
                        destination_path = os.path.join(output_folder, relative_path)
                        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

                        shutil.copy2(seq_file, destination_path)
                        collected_files.add(seq_file)

                    print(f"✓ Collected sequence: {len(sequence_files)} frames from {file_path}")
                    continue

                if not is_file_inside_hip(absolute_path, hip_dir): # 判斷外部連結
                    
                    external_output_folder = os.path.join(output_folder, "external")
                    
                    if not os.path.exists(external_output_folder):
                        os.makedirs(external_output_folder)
                    
                    external_output_path = os.path.join(external_output_folder, original_filename) # Paths for external file
                    
                    shutil.copy2(absolute_path, external_output_path)
                    
                    # Update parameter: $HIP/external/filename
                    new_path = f"$HIP/external/{os.path.basename(absolute_path)}"
                    parm.set(new_path)
                    
                    external_collected_files.add(absolute_path)
                    parameters_updated.append({
                        'node': current_node.path(),
                        'parameter': parm.name(),
                        'old_path': file_path,
                        'new_path': new_path,
                        'original_file': absolute_path
                    })

                    print(f"✓ Moved external file: {original_filename}")
                    print(f"  - From: {absolute_path}")
                    print(f"  - To: {new_path}")
                    print(f"  - Node: {current_node.path()}")
                    collected_files.add(absolute_path)

                else:
                    relative_path = os.path.relpath(absolute_path, hip_dir)
                    destination_path = os.path.join(output_folder, relative_path)
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

                    # 處理同名檔案衝突
                    if os.path.exists(destination_path):
                        base, ext = os.path.splitext(os.path.basename(absolute_path))
                        i = 1
                        while os.path.exists(os.path.join(output_folder, f"{base}_{i}{ext}")):
                            i += 1
                        destination_path = os.path.join(output_folder, f"{base}_{i}{ext}")

                    # Copy2
                    shutil.copy2(absolute_path, destination_path)
                    collected_files.add(absolute_path)
                    # print(f"Copied:\n {absolute_path} \n to {destination_path}")
                
            except Exception as e:
                print("/----------Error------------/")
                print(f"Error processing node {current_node.path()}:\n{e}")
                continue
        
        copy_hip_file(hip_file_path, output_folder)
        print("=" * 30)
        print(f"Total files collected: {len(collected_files)}")
        print(f"Total external files collected: {len(external_collected_files)}")
        print(f"Total files skipped: {len(skipped_files)}")
        hou.ui.displayMessage(
            "Collection Complete!!",
            title="Houdini Material Collector"
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        
collect_material_files()