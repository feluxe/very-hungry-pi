import os
from glob import iglob

kb = 1000
mb = 1000 * kb
gb = 1000 * mb

root_dir = "/home/felix/**/*"

for path1 in iglob(root_dir, recursive=True):

    try:
        fstat1 = os.stat(path1)
    except OSError:
        continue

    if fstat1.st_size >= 100 * mb:

        f1_path = path1
        f1_size = fstat1.st_size
        f1_inode = fstat1.st_ino

        for path2 in iglob(root_dir, recursive=True):

            try:
                fstat2 = os.stat(path2)
            except OSError:
                continue

            f2_size = fstat2.st_size

            if f2_size < 100 * mb:
                continue

            if f2_size != f1_size:
                continue

            f2_inode = fstat2.st_ino

            if f2_inode == f1_inode:
                continue

            f2_path = path2

            print(f1_path + ' == ' + f2_path)
            print(str(f1_inode) + " vs " + str(f2_inode))

            # TODO: At this point, you have to check both file hashes.
            # TODO: What about file meta data (permissions etc.)? You have to 
            # compare it too...
            # TODO: If both files are identical, I think it should be fine to 
            # remove one and create hardlinks.

