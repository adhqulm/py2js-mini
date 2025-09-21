tasks = []


def add_task(name):
    tasks.append(name)


def list_tasks():
    i = 0
    for _ in tasks:
        print(i, tasks[i])
        i = i + 1


add_task("buy milk")
add_task("walk dog")
list_tasks()
