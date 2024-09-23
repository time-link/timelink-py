# This is necessary to avoid error in docs generation
# File "/Users/jrc/develop/timelink-py/timelink/app/main.py", line 133, in <module>
#     app.mount("/static", StaticFiles(packages=[("timelink")]), name="static")
#                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "/Users/jrc/develop/timelink-py/.venv/lib/python3.11/site-packages/starlette/staticfiles.py", line 54, in __init__
#     self.all_directories = self.get_directories(directory, packages)
#                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "/Users/jrc/develop/timelink-py/.venv/lib/python3.11/site-packages/starlette/staticfiles.py", line 85, in get_directories
#     assert os.path.isdir(
# AssertionError: Directory ''statics'' in package 'timelink' could not be found.
