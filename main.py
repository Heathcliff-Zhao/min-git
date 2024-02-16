from mingit import MinGit


def main():
    min_git = MinGit('.')
    while True:
        command = input('MinGit> ')
        if command == 'init':
            min_git.init()
        elif command == 'status':
            min_git.status()
        elif command == 'log':
            min_git.log()
        elif command.startswith('add '):
            min_git.add(command.split()[1])
        elif command.startswith('commit '):
            min_git.commit(command.split()[1])
        elif command == 'diff':
            min_git.diff()
        else:
            print('Invalid command')
            exit(0)


main()
