from pprint import pprint

import requests


if __name__ == "__main__":
    tokens = ['AAAA', 'BBBB']
    for token in tokens:
        print(token)
        r = requests.get('http://localhost:5000/systems', params={'token': token})
        pprint(r.json())
        print()
