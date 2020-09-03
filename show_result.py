import argparse    # 1. argparseをインポート
import pandas as pd
from glob import glob

DIR_HYDRA = './data/hydra_outputs'

parser = argparse.ArgumentParser()
parser.add_argument('-d', default=0)  # debug = 1 をいれる？
args = parser.parse_args() 

list_df = [pd.DataFrame()]
for path in sorted(glob(f'{DIR_HYDRA}/*/*/*/*')):
    if 'result_fold' in path:
        df = pd.read_csv(path)
        if df['debug'][0]==1 and args.d==0:
            pass
        else:
            list_df.append(df) 
print(pd.concat(list_df))
