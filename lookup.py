import json
import sys

with open("/agent_memory/static_config.json") as f:
    config = json.load(f)

def get_fact(key):
    keys = key.split(".")
    val = config
    for k in keys:
        val = val.get(k)
        if val is None:
            print("[!] Not found")
            exit(1)
    print(val)

if __name__ == '__main__':
    get_fact(sys.argv[1])

    