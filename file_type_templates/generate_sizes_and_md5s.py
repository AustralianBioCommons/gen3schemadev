
import hashlib
import os
import glob
import json


def main():
    dummy_files = glob.glob("dummy*")
    file_stats = {}
    for dummy_file in dummy_files:
        with open(dummy_file, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        md5 = file_hash.hexdigest()
        file_stats[dummy_file] = {"file_size": os.path.getsize(dummy_file),
                                  "md5": md5}
    with open("file_stats.json", "w") as f:
        json.dump(file_stats, f, indent=4, sort_keys=True)
    print(file_stats)



if __name__ == '__main__':
    main()