import os

def merge_all_label_txt(folder_path: str, output_name: str = "all_labels_merged.txt"):
    """
    合并文件夹内所有txt标签文件到单个文件
    :param folder_path: labels文件夹完整路径
    :param output_name: 输出合并文件名称，生成在labels目录下
    """
    # 拼接输出文件完整路径
    output_file = os.path.join(os.path.dirname(__file__), output_name)
    total_lines = 0
    file_count = 0

    # 打开输出文件，追加写入模式
    with open(output_file, "w", encoding="utf-8") as out_f:
        # 遍历文件夹内所有文件
        for filename in os.listdir(folder_path):
            # 只处理txt文件，跳过输出文件自身
            if filename.lower().endswith(".txt") and filename != output_name:
                file_path = os.path.join(folder_path, filename)
                # 跳过子文件夹，只处理文件
                if not os.path.isfile(file_path):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as in_f:
                        lines = in_f.readlines()
                        # 过滤空行
                        valid_lines = [line.strip() + "\n" for line in lines if line.strip()]
                        if valid_lines:
                            out_f.writelines(valid_lines)
                            total_lines += len(valid_lines)
                            file_count += 1
                            print(f"已读取 {filename} ，有效标注 {len(valid_lines)} 行")
                except Exception as e:
                    print(f"读取失败 {filename}，错误：{str(e)}")

    print("=" * 50)
    print(f"合并完成！")
    print(f"处理文件总数：{file_count}")
    print(f"合并标注总行数：{total_lines}")
    print(f"输出文件路径：{output_file}")


if __name__ == "__main__":
    # --------------------------
    # 修改这里为你的labels文件夹路径
    target_folder = r"./labeled_data/labels"
    # --------------------------
    merge_all_label_txt(target_folder)