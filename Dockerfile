from python:3

copy main.py /
copy server.py /
copy tests.py /
copy passwords_logins.tsv /

cmd ["python3", "main.py"]