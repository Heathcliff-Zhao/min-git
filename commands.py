import os
import sys

from base import GIT_DIR, add_object, commit, get_ignore_list, compare_ignore


def _init_object_store():
    os.makedirs(os.path.join(GIT_DIR, 'objects'), exist_ok=True)
    print(f'Initialized empty Min-Git object store in {os.path.join(GIT_DIR, "objects")}')

def _init_index():
    os.makedirs(os.path.join(GIT_DIR, 'index'), exist_ok=True)
    print(f'Initialized empty Min-Git index in {os.path.join(GIT_DIR, "index")}')

def init_git_repo():
    print(f'Initialized empty Min-Git repository in {GIT_DIR}')
    os.makedirs(GIT_DIR, exist_ok=True)
    _init_object_store()
    _init_index()
    

def main():
    if len(sys.argv) < 2:
        print('Usage: python commands.py <command> [<args>]')
        sys.exit(1)

    command = sys.argv[1]
    if command == 'init':
        init_git_repo()
    elif command == 'add':
        if sys.argv[2] == '.':
            ignore_list = get_ignore_list() + [GIT_DIR]
            # print(ignore_list)
            for root, dirs, files in os.walk('.'):
                # print(root, dirs, files)
                for d in dirs:
                    if compare_ignore(d, ignore_list):
                        dirs.remove(d)
                for file in files:
                    file_path = os.path.join(root, file)
                    if not compare_ignore(file_path, ignore_list):
                        print(f'Added {file_path} to Min-Git object store')
                    #     sha1 = add_object(file_path)
                        # print(f'Added {file_path} to Min-Git object store as {sha1}')
        else:
            for file_path in sys.argv[2:]:
                sha1 = add_object(file_path)
                print(f'Added {file_path} to Min-Git object store as {sha1}')
    elif command == 'commit':
        message = sys.argv[2]
        sha1 = commit(message)
        print(f'Created commit with SHA-1 {sha1}')

if __name__ == '__main__':
    main()
