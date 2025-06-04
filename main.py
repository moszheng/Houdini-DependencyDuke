import hou
import os
import shutil
import glob
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

def get_sequence_files(path_pattern):
    path_pattern = hou.expandString(path_pattern)

    dir_path = os.path.dirname(path_pattern)
    base_name = os.path.basename(path_pattern)

    # 建立 regex，將 frame number 部分變成可比對的 group
    # .0001.bgeo.sc 的情況，找出如 v1.XXXX 的變化
    frame_regex = re.sub(r'\$F\d*', r'\\d+', base_name)  # $F4 變成 \d+
    frame_regex = frame_regex.replace('#', r'\d')  # #### 變成 \d\d\d\d

    # 對於沒有顯式的 $F，但是 .0001.bgeo.sc 形式的情況
    if '$F' not in base_name and '#' not in base_name:
        # 嘗試匹配形如 .0001.bgeo.sc 的 frame number
        match = re.search(r'(.*?)(\.\d{4})\.bgeo\.sc$', base_name)
        if match:
            prefix = match.group(1)
            frame_regex = re.escape(prefix) + r'\.\d{4}\.bgeo\.sc'
        else:
            return []

    regex = re.compile('^' + frame_regex + '$')
    sequence_files = []

    for file in os.listdir(dir_path):
        if regex.match(file):
            sequence_files.append(os.path.join(dir_path, file))

    return sorted(sequence_files)

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
        hou.ui.displayMessage("Material collection cancelled. No output folder selected.",
                                title="Houdini Material Collector")
        return

    # 清理路徑，確保它是標準格式
    output_folder = hou.expandString(output_folder) # 處理可能存在的 $HIP 等變數
    output_folder = os.path.normpath(output_folder) # 正規化路徑，處理斜線方向等

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
        print("/--------------------------------------------------/")
    
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
            print(f"/----------Error scanning node {node.path()}------------/")
            print(f"Error: {e}")
            continue

    print(f"Found {len(file_parms)} file reference parameters to process...")
    if skipped_rop_count > 0:
        print(f"Skipped {skipped_rop_count} ROP nodes")
    return file_parms

def copy_hip_file(hip_file_path, output_folder):
    # Duplicate HIP
    try:
        hip_file_name = os.path.basename(hip_file_path)
        destination_hip_path = os.path.join(output_folder, hip_file_name)
        shutil.copy2(hip_file_path, destination_hip_path)
    except Exception as e:
        print(f"Error copying HIP file: {e}")
        return False

"""
遍歷 Houdini 場景中的所有節點，收集其引用的外部檔案。
並將它們複製到使用者指定的目標資料夾，同時保留相對於 Houdini 檔案根目錄的結構。
"""
def collect_material_files():
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
                # 檔案路徑
                file_path = parm.eval()
                expanded_file_path = hou.expandString(file_path) # 考慮到可能會有表達式，需要 expandString

                if not expanded_file_path or not os.path.exists(expanded_file_path): # 檢查路徑是否有效且存在
                    continue
                    
                absolute_path = os.path.abspath(expanded_file_path) # 將路徑正規化，處理相對路徑等
                
                if absolute_path in collected_files or absolute_path in external_collected_files:
                    continue
                
                original_filename = os.path.basename(absolute_path)

                if is_target_file(expanded_file_path):
                    # Handel cache seq
                    if '.bgeo.sc' in file_path:
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
                        
                        external_folder_output = os.path.join(output_folder, "external")
                        
                        if not os.path.exists(external_folder_output):
                            os.makedirs(external_folder_output)
                        
                        external_output_path = os.path.join(external_folder_output, original_filename) # Paths for external file
                        
                        # Copy to both HIP/external and output/external
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
                        print(f"  From: {absolute_path}")
                        print(f"  To: {new_path}")
                        print(f"  Node: {current_node.path()}")
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
                else:
                    # Track skipped files
                    if absolute_path not in skipped_files:
                        skipped_files.add(absolute_path)
                        print(f"✗ Skipped: {current_node.path()}")
            except Exception as e:
                print("/----------Error------------/")
                print(f"Error processing node {current_node.path()}:\n{e}")
                continue
        
        copy_hip_file(hip_file_path, output_folder)
        print(f"Total files collected: {len(collected_files)}")
        print(f"Total external files collected: {len(external_collected_files)}")
        print(f"Total files skipped: {len(skipped_files)}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
collect_material_files()