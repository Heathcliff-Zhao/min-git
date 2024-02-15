import os
import hashlib
import json

GIT_DIR = '.min-git'

def add_object(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    sha1 = hashlib.sha1(data).hexdigest()
    object_dir = os.path.join(GIT_DIR, 'index', sha1[:2])
    os.makedirs(object_dir, exist_ok=True)
    object_path = os.path.join(object_dir, sha1[2:])
    with open(object_path, 'wb') as f:
        f.write(data)
    return sha1

def commit(message):
    index = {}
    for root, dirs, files in os.walk(GIT_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            sha1 = add_object(file_path)
            index[file_path] = sha1
    commit_data = {
        'message': message,
        'index': index
    }
    commit_json = json.dumps(commit_data, indent=2)
    sha1 = hashlib.sha1(commit_json.encode()).hexdigest()
    object_dir = os.path.join(GIT_DIR, 'objects', sha1[:2])
    os.makedirs(object_dir, exist_ok=True)
    object_path = os.path.join(object_dir, sha1[2:])
    with open(object_path, 'w') as f:
        f.write(commit_json)
    return sha1
