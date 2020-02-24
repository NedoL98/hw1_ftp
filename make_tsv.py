import pandas as pd

data = {"name": ["1000", "1001", "kek"], "password": ["biba", "keka", "zuka"]}
pd.DataFrame(data).to_csv("passwords_logins.tsv", sep = "\t", index = False)