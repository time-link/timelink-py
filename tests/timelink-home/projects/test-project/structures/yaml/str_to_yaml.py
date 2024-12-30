import os
import yaml
import json
from pprint import pprint


json_path = "/Users/jrc/develop/timelink-py/tests/timelink-home/projects/test-project/structures/sources.str.json"

with open(json_path) as stream:
    pystr = json.load(stream)
    groups = pystr['groups']

# print current directory
print(os.getcwd())

path = 'tests/timelink-home/projects/test-project/structures/yaml/sample-stru.yml'
with open(path) as stream:
    pyaml = yaml.full_load(stream)

pprint(pyaml)
