import os
import hashlib
import json
import time
import fnmatch
import difflib


class MinGit:
    def __init__(self, repo_path='.'):
        self.repo_path = os.path.abspath(repo_path)
        self.git_dir = os.path.join(self.repo_path, '.min-git')
        self.objects_dir = os.path.join(self.git_dir, 'objects')
        self.index_path = os.path.join(self.git_dir, 'index')
        self.head_path = os.path.join(self.git_dir, 'HEAD')

    def init(self):
        os.makedirs(self.git_dir, exist_ok=True)
        os.makedirs(self.objects_dir, exist_ok=True)
        with open(self.index_path, 'w') as f:
            json.dump({}, f)
        with open(self.head_path, 'w') as f:
            f.write('')
        print(f"Initialized empty Min-Git repository in {self.repo_path}")

    def create_tree_object(self, entries):
        tree_data = json.dumps(entries, indent=4)
        return self.hash_object(tree_data, obj_type='tree')

    def hash_object(self, data, obj_type='blob', store=True):
        if obj_type == 'tree':
            full_data = data.encode()
        else:
            header = f"{obj_type} {len(data)}\0"
            full_data = header.encode() + data
        sha1 = hashlib.sha1(full_data).hexdigest()
        if store:
            obj_path = os.path.join(self.objects_dir, sha1[:2], sha1[2:])
            os.makedirs(os.path.dirname(obj_path), exist_ok=True)
            with open(obj_path, 'wb') as f:
                f.write(full_data)
        return sha1

    def read_ignore_patterns(self):
        ignore_file_path = os.path.join(self.repo_path, '.min-gitignore')
        ignore_patterns = []
        if os.path.exists(ignore_file_path):
            with open(ignore_file_path, 'r') as file:
                ignore_patterns = [line.strip() for line in file if line.strip() and not line.startswith('#')]
        return ignore_patterns

    def is_ignored(self, path, ignore_patterns):
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def add(self, filepath):
        if os.path.isfile(filepath):
            self.add_file(filepath)
        ignore_patterns = self.read_ignore_patterns()
        for root, dirs, files in os.walk(filepath, topdown=True):
            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(root, d), ignore_patterns)]
            for file in files:
                file_path = os.path.join(root, file)
                if not self.is_ignored(file_path, ignore_patterns):
                    self.add_file(file_path)

    def add_file(self, filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        sha1 = self.hash_object(data, store=False)

        with open(self.index_path, 'r') as f:
            index = json.load(f)

        rel_path = os.path.relpath(filepath, self.repo_path)
        if rel_path not in index or index[rel_path] != sha1:
            self.hash_object(data)
            index[rel_path] = sha1
            with open(self.index_path, 'w') as f:
                json.dump(index, f, indent=4)

    def write_tree(self):
        with open(self.index_path, 'r') as f:
            index = json.load(f)
            
        tree_entries = [{"path": path, "mode": "100644", "sha": sha} for path, sha in index.items()]
        tree_data = json.dumps(tree_entries, indent=4)
        return self.hash_object(tree_data, 'tree')

    def last_commit_tree(self):
        if os.path.exists(self.head_path) and os.path.getsize(self.head_path) > 0:
            with open(self.head_path, 'r') as f:
                last_commit_sha = f.read().strip()
                commit_path = os.path.join(self.objects_dir, last_commit_sha[:2], last_commit_sha[2:])
                with open(commit_path, 'rb') as f:
                    commit_data = f.read()
                    null_index = commit_data.index(b'\0') + 1
                    commit_body = commit_data[null_index:]
                    commit_info = json.loads(commit_body.decode())
                    return commit_info['tree']
        return None

    def commit(self, message):
        current_tree_sha = self.write_tree()
        last_tree_sha = self.last_commit_tree()

        if current_tree_sha == last_tree_sha:
            print("Nothing to commit, working tree clean.")
            return

        parent = ''
        if os.path.exists(self.head_path) and os.path.getsize(self.head_path) > 0:
            with open(self.head_path, 'r') as f:
                parent = f.read().strip()
        commit_info = {
            'tree': current_tree_sha,
            'parent': parent,
            'author': 'Yue Zhao <yuezhao@yuezhao.com>',
            'committer': 'Yue Zhao <yuezhao@yuezhao.com>',
            'message': message,
            'timestamp': time.time()
        }
        commit_data = json.dumps(commit_info, indent=4).encode()
        commit_sha = self.hash_object(commit_data, 'commit')
        with open(self.head_path, 'w') as f:
            f.write(commit_sha)
        print(f"[min-git commit] {commit_sha}")

    def log(self):
        current = ''
        if os.path.exists(self.head_path):
            with open(self.head_path, 'r') as f:
                current = f.read().strip()
        while current:
            commit_path = os.path.join(self.objects_dir, current[:2], current[2:])
            with open(commit_path, 'rb') as f:
                commit_data = f.read()
                null_index = commit_data.index(b'\0') + 1
                commit_body = commit_data[null_index:]
                commit_info = json.loads(commit_body.decode())
                print(f"commit {current}\nAuthor: {commit_info['author']}\nDate: {time.ctime(commit_info['timestamp'])}\n\n    {commit_info['message']}\n")
                current = commit_info['parent']

    def status(self):
        with open(self.index_path, 'r') as f:
            index = json.load(f)

        last_tree = self.last_commit_tree()
        last_tree_files = self.build_tree_snapshot(last_tree) if last_tree else {}

        unstaged_changes = self.check_working_dir_changes(index)
        staged_changes = {path: sha for path, sha in index.items() if last_tree_files.get(path) != sha}
        untracked_files = self.find_untracked_files(index)

        if unstaged_changes:
            print("Changes not staged for commit:")
            for path in unstaged_changes:
                print(f"\tmodified: {path}")
        if staged_changes:
            print("Changes to be committed:")
            for path in staged_changes:
                print(f"\tnew file: {path}" if path not in last_tree_files else f"\tmodified: {path}")
        if untracked_files:
            print("Untracked files:")
            for path in untracked_files:
                print(f"\t{path}")
        if not any([unstaged_changes, staged_changes, untracked_files]):
            print("nothing to commit, working tree clean")

    def check_working_dir_changes(self, index):
        changes = {}
        for path, sha in index.items():
            file_path = os.path.join(self.repo_path, path)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    data = f.read()
                file_sha = self.hash_object(data, store=False)
                if file_sha != sha:
                    changes[path] = file_sha
        return changes

    def find_untracked_files(self, index):
        untracked = []
        ignore_patterns = self.read_ignore_patterns()
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(root, d), ignore_patterns)]
            for file in files:
                file_path = os.path.join(root, file)
                if not self.is_ignored(file_path, ignore_patterns):
                    file_path = os.path.relpath(file_path, self.repo_path)
                    if file_path not in index:
                        untracked.append(file_path)
        return untracked

    def parse_tree_object(self, tree_sha):
        tree_path = os.path.join(self.objects_dir, tree_sha[:2], tree_sha[2:])
        with open(tree_path, 'rb') as f:
            tree_data = f.read()
        return json.loads(tree_data.decode())

    def build_tree_snapshot(self, tree_sha, path_prefix=""):
        snapshot = {}
        tree_entries = self.parse_tree_object(tree_sha)
        for tree_entry in tree_entries:
            path, sha = tree_entry['path'], tree_entry['sha']
            entry_path = os.path.join(path_prefix, path)
            obj_type = self.get_object_type(sha)
            if obj_type == 'blob':
                snapshot[entry_path] = sha
            elif obj_type == 'tree':
                subtree_snapshot = self.build_tree_snapshot(sha, entry_path)
                snapshot.update(subtree_snapshot)
        return snapshot

    def get_object_type(self, sha):
        obj_path = os.path.join(self.objects_dir, sha[:2], sha[2:])
        with open(obj_path, 'rb') as f:
            data = f.read()
        end_of_type = data.find(b'\0')
        obj_type = data[:end_of_type].decode().split(' ')[0]
        return obj_type
    
    def get_object_data(self, sha):
        obj_path = os.path.join(self.objects_dir, sha[:2], sha[2:])
        with open(obj_path, 'rb') as f:
            data = f.read()
        end_of_type = data.find(b'\0')
        return data[end_of_type + 1:]
    
    def checkout(self, *args):
        raise NotImplementedError
    
    def diff(self):
        with open(self.index_path, 'r') as f:
            index = json.load(f)
        for path, sha in index.items():
            file_path = os.path.join(self.repo_path, path)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    data = f.read()
                file_sha = self.hash_object(data, store=False)
                if file_sha != sha:
                    print(f"diff --git a/{path} b/{path}")
                    print(f"index {sha[:7]}..{file_sha[:7]} 100644")
                    print(f"--- a/{path}")
                    print(f"+++ b/{path}")
                    for diff_ in difflib.unified_diff(self.get_object_data(sha).decode().splitlines(), data.decode().splitlines(), lineterm=''):
                        print(diff_)
    
    def merge(self, *args):
        raise NotImplementedError
    
    def rebase(self, *args):
        raise NotImplementedError
    
    def tag(self, *args):
        raise NotImplementedError
    
    def branch(self, *args):
        raise NotImplementedError
    
    def remote(self, *args):
        raise NotImplementedError
    
    def push(self, *args):
        raise NotImplementedError
    
    def pull(self, *args):
        raise NotImplementedError
    
    def clone(self, *args):
        raise NotImplementedError
    
    def fetch(self, *args):
        raise NotImplementedError


if __name__ == '__main__':
    min_git = MinGit('.')
    min_git.init()

    min_git.add('.')

    min_git.status()

    min_git.commit('Initial commit')

    min_git.log()

    min_git.status()
