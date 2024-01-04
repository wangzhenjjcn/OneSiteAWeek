import os
import tkinter as tk
from tkinter import filedialog

def rename_files_in_directory(directory):
    try:
        files = os.listdir(directory)
    except FileNotFoundError:
        print(f"The directory {directory} does not exist.")
        return

    for file in files:
        file_path = os.path.join(directory, file)

        if os.path.isfile(file_path):
            parts = file.split('-')
            if len(parts) >= 3:
                new_name = '-'.join(parts[1:])
                new_file_path = os.path.join(directory, new_name)
                os.rename(file_path, new_file_path)
                print(f'Renamed {file} to {new_name}')

def main():
    root = tk.Tk()
    root.withdraw()  # 隐藏tkinter主窗口

    # 显示文件夹选择对话框
    directory = filedialog.askdirectory(title='Select Folder')
    if directory:
        rename_files_in_directory(directory)
    else:
        print("No folder selected.")

if __name__ == "__main__":
    main()
