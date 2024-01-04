import os
import csv
import hashlib
import time
from datetime import datetime
import psutil
import shutil
import configparser
import threading
import queue

def calculate_md5(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_file_info(file_path, extensions_to_calculate_md5):
    _, file_name_with_extension = os.path.split(file_path)
    file_name, file_extension = os.path.splitext(file_name_with_extension)
    
    file_size = os.path.getsize(file_path)
    access_time = datetime.fromtimestamp(os.path.getatime(file_path))
    modify_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    create_time = datetime.fromtimestamp(os.path.getctime(file_path))

    md5_hash = ''
    if file_extension.lower() in extensions_to_calculate_md5:
        md5_hash = calculate_md5(file_path)
    
    return (file_name, file_extension, file_path, file_size, access_time, modify_time, create_time, md5_hash)

def save_to_csv(data, filename='files_info.csv'):
    columns = ['File Name', 'File Extension', 'File Path', 'File Size', 'Access Date', 'Modify Date', 'Create Date', 'MD5']
    write_header = not os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        if write_header:
            writer.writerow(columns)
        writer.writerows(data)

def get_configuration():
    config = configparser.ConfigParser()
    default_settings = {
        'cpu_threshold': '20',
        'sleep_time': '0.05',
        'thread_count': '4',
        'file_extensions': '.doc,.docx,.ppt,.pptx,.xls,.xlsx,.pdf,.iso,.zip,.rar,.7z,.exe,.jpg,.jpeg,.png,.bmp,.gif,.mp3,.wav,.flac,.mp4,.avi,.mkv,.wmv'
    }
    
    if not os.path.exists('conf.ini'):
        config['DEFAULT'] = default_settings
        with open('conf.ini', 'w') as configfile:
            config.write(configfile)
    config.read('conf.ini')
    
    return {
        'cpu_threshold': float(config['DEFAULT'].get('cpu_threshold', default_settings['cpu_threshold'])),
        'sleep_time': float(config['DEFAULT'].get('sleep_time', default_settings['sleep_time'])),
        'thread_count': int(config['DEFAULT'].get('thread_count', default_settings['thread_count'])),
        'file_extensions': set(config['DEFAULT'].get('file_extensions', default_settings['file_extensions']).lower().split(','))
    }

def worker(file_queue, results_queue, cpu_threshold, sleep_time, extensions_to_calculate_md5):
    while True:
        try:
            file_path = file_queue.get(timeout=3)  # 3 seconds timeout
        except queue.Empty:
            break
        try:
            print(f"Processing : {file_path}")
            results_queue.put(get_file_info(file_path, extensions_to_calculate_md5))
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        while psutil.cpu_percent(1) > cpu_threshold:
            time.sleep(sleep_time)
        time.sleep(sleep_time)

def main():
    config = get_configuration()
    cpu_threshold = config['cpu_threshold']
    sleep_time = config['sleep_time']
    thread_count = config['thread_count']
    
    if os.path.exists('files_info.csv'):
        shutil.copy2('files_info.csv', 'files_info_backup.csv')
        os.remove('files_info.csv')

    file_queue = queue.Queue()
    results_queue = queue.Queue()
    partitions = [part.mountpoint for part in psutil.disk_partitions() if 'removable' not in part.opts]

    for partition in partitions:
        for root, dirs, files in os.walk(partition):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    file_queue.put(file_path)

    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=worker, args=(file_queue, results_queue, cpu_threshold, sleep_time, config['file_extensions']))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    all_files_info = list(results_queue.queue)
    save_to_csv(all_files_info)

if __name__ == '__main__':
    main()
