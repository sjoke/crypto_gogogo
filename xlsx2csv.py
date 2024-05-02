import pandas as pd

for sheet_name, df in pd.read_excel(r"/Users/jiaokeshi/Downloads/Joke.xlsx", sheet_name=None).items():
    df.to_csv(f'docs/output_{sheet_name}.csv', index=False, encoding='utf-8')