import hou
import os
import shutil

def collect_material_files(output_folder):
    """
    遍歷 Houdini 場景中的所有節點，收集其引用的外部檔案。

    Args:
        output_folder (str): 目標資料夾，所有收集到的檔案將被複製到此。
    """
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")
            print("/--------------------------------------------------/")

        collected_files = set() # 用於追蹤已收集的檔案，避免重複複製

        # 遍歷場景中所有現有的節點實例
        for current_node in hou.node('/').allNodes():
            # 遍歷節點的所有參數
            for parm in current_node.parms():
                parm_template = parm.parmTemplate()

                # 確保 parm_template 存在，且它是 String 類型的參數模板
                # 使用 hou.parmTemplateType.String 來判斷參數基本類型
                if parm_template is not None and \
                   parm_template.type() == hou.parmTemplateType.String and \
                   parm_template.stringType() == hou.stringParmType.FileReference:
                    
                    file_path = parm.eval()
                    
                    # 考慮到可能會有表達式，需要 expandString
                    expanded_file_path = hou.expandString(file_path)

                    # 檢查路徑是否有效且存在
                    if expanded_file_path and os.path.exists(expanded_file_path):
                        # 將路徑正規化，處理相對路徑等
                        absolute_path = os.path.abspath(expanded_file_path)

                        if absolute_path not in collected_files:
                            destination_path = os.path.join(output_folder, os.path.basename(absolute_path))
                            
                            # 處理同名檔案衝突
                            if os.path.exists(destination_path):
                                base, ext = os.path.splitext(os.path.basename(absolute_path))
                                i = 1
                                while os.path.exists(os.path.join(output_folder, f"{base}_{i}{ext}")):
                                    i += 1
                                destination_path = os.path.join(output_folder, f"{base}_{i}{ext}")

                            shutil.copy2(absolute_path, destination_path)
                            collected_files.add(absolute_path)
                            print(f"Copied: {absolute_path} to {destination_path}")
                            
                            # 可選：更新原始參數的路徑為新的相對路徑
                            # relative_path = os.path.relpath(destination_path, os.path.dirname(current_node.path()))
                            # try:
                            #     parm.set(relative_path)
                            #     print(f"Updated parm {parm.name()} on node {current_node.name()} to {relative_path}")
                            # except Exception as update_err:
                            #     print(f"Warning: Could not update parm {parm.name()} on node {current_node.name()}: {update_err}")

        print("Material file collection complete.")

    except Exception as e:
        print(f"An error occurred: {e}")

collect_material_files("D:/Houdini_Packages/MyProject_MaterialFiles")