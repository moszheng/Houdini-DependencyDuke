import hou
import os
import shutil

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

        # Duplicate HIP
        hip_file_name = os.path.basename(hip_file_path)
        destination_hip_path = os.path.join(output_folder, hip_file_name)
        shutil.copy2(hip_file_path, destination_hip_path)

        # Collect files
        collected_files = set() # 用於追蹤已收集的檔案，避免重複複製
        
        for current_node in hou.node('/').allNodes():
            try:
                for parm in current_node.parms():
                    parm_template = parm.parmTemplate()

                    # 確保 parm_template 存在，且它是 String 類型的參數模板
                    # 使用 hou.parmTemplateType.String 來判斷參數基本類型
                    if parm_template is not None and \
                    parm_template.type() == hou.parmTemplateType.String and \
                    parm_template.stringType() == hou.stringParmType.FileReference:
                        
                        # 檔案路徑
                        file_path = parm.eval()
                        expanded_file_path = hou.expandString(file_path) # 考慮到可能會有表達式，需要 expandString

                        if expanded_file_path and os.path.exists(expanded_file_path): # 檢查路徑是否有效且存在
                            
                            absolute_path = os.path.abspath(expanded_file_path) # 將路徑正規化，處理相對路徑等

                            if absolute_path not in collected_files:
                                # os.path.relpath 會計算 absolute_path 相對於 start (houdini_hip_dir) 的相對路徑
                                relative_path = os.path.relpath(absolute_path, hip_dir)
                                #目標路徑
                                # destination_path = os.path.join(output_folder, os.path.basename(absolute_path))
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
                                print(f"Copied:\n {absolute_path} \n to {destination_path}")
            except Exception as e:
                print("/----------Error------------/")
                print(f"Error processing node {current_node.path()}:\n{e}")
                continue
        hou.ui.displayMessage(f"Material file collection complete! Copied {len(collected_files)} files to: {output_folder}",
                              title="Houdini Material Collector")
        print("Material file collection complete.")

    except Exception as e:
        print(f"An error occurred: {e}")

collect_material_files()