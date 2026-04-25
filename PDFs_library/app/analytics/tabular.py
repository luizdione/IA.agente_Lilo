# app/analytics/tabular.py

import pandas as pd

def analyze_file(path):
    df = pd.read_excel(path) if path.endswith("xlsx") else pd.read_csv(path)
    return df.describe()