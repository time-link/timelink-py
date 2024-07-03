from pathlib import Path
import logging
import threading
import queue
import time

from timelink.notebooks import TimelinkNotebook

logging.basicConfig(level=logging.INFO)

# this is the generic context of the app
context = dict()

project_home = Path(__file__).parent.parent.parent

context['project_home'] = project_home

tlnb = TimelinkNotebook(project_home=project_home)

tlnb_info = tlnb.get_info(as_dataframe=False, show_token=True, show_password=True)
context['dbtype'] = tlnb_info['Database type']
context['info'] = tlnb_info


# Background worker and thread
def worker(task_queue, task_running):
    while True:
        # Wait for a task
        task, args, kwargs = task_queue.get()
        print(f"Starting task: {task.__name__}")

        try:
            # Indicate that a task is about to start
            task_running.set()

            # Execute the task
            task(*args, **kwargs)
        finally:
            # Indicate that the task has finished
            task_running.clear()

            # Mark the task as done
            task_queue.task_done()


def example_task(message, delay):
    time.sleep(delay)
    print(f"Task completed: {message}")


# Create a queue that will hold the tasks
task_queue = queue.Queue()

# Create an event to indicate if a task is running
task_running = threading.Event()

# Create and start the background thread
background_thread = threading.Thread(target=worker, args=(task_queue, task_running), daemon=True)
background_thread.start()


# task_queue.put((example_task, ("First task", 2), {}))
# task_queue.put((example_task, ("Second task", 3), {}))
