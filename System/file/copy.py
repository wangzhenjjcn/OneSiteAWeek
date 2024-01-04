import os
import time
import threading

def copy_file_with_rate_limit(src_path, dst_path, rate_limit_kb_per_sec):
    with open(src_path, 'rb') as src_file, open(dst_path, 'wb') as dst_file:
        while True:
            start_time = time.time()
            data = src_file.read(rate_limit_kb_per_sec * 1024)
            if not data:
                break
            dst_file.write(data)
            elapsed_time = time.time() - start_time
            sleep_time = max(0, 1.0 - elapsed_time)
            time.sleep(sleep_time)

def copy_directory_worker(src_dir, dst_dir, file_paths, rate_limit_kb_per_sec):
    filecount=0
    for src_rel_path in file_paths:
        filecount+=1
        src_path = os.path.join(src_dir, src_rel_path)
        dst_path = os.path.join(dst_dir, src_rel_path)
        if os.path.exists(dst_path):  # 检查目标文件是否已存在
            print(f'[{filecount}] Skipping {dst_path} as it already exists.')
            continue  # 如果已存在，则跳过此文件
        print(f'[{filecount}]Copying {src_path} to {dst_path}')
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        copy_file_with_rate_limit(src_path, dst_path, rate_limit_kb_per_sec)


def copy_directory_with_rate_limit(src_dir, dst_dir, rate_limit_kb_per_sec, num_threads=16):
    all_files = [os.path.relpath(os.path.join(root, file), src_dir)
                 for root, _, files in os.walk(src_dir) for file in files]
    files_per_thread = len(all_files) // num_threads
    threads = []

    for i in range(num_threads):
        start_idx = i * files_per_thread
        end_idx = (i + 1) * files_per_thread if i != num_threads - 1 else None
        thread_files = all_files[start_idx:end_idx]
        thread = threading.Thread(
            target=copy_directory_worker,
            args=(src_dir, dst_dir, thread_files, rate_limit_kb_per_sec)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

# 使用函数复制目录
src_dir = 'I://'
dst_dir =  'U://I/'
rate_limit_kb_per_sec = 120000  # 限制速度为每秒100KB
copy_directory_with_rate_limit(src_dir, dst_dir, rate_limit_kb_per_sec)

 