import os
import torch
import random
import numpy as np
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)  # type: ignore
    torch.backends.cudnn.deterministic = True  # type: ignore
    torch.backends.cudnn.benchmark = True  # type: ignore

def get_debug_config(config):
    config['globals']['num_epochs'] = 3
    config['split']['params']['n_splits'] = 2
    return config

def get_debug_df(df):
    birds = df['ebird_code'].unique()
    df_merge = pd.DataFrame(columns=df.columns)
    for bird in birds:
        mask = df['ebird_code'] == bird
        df_merge = df_merge.append(df[mask].iloc[0:1, :])
    df_merge = df_merge.reset_index(drop=True)
    return df_merge

def transform_balanced_dataset(train):
    '''
    class imbalanced に対処
    '''
    n_file_max = train['ebird_code'].value_counts().max()
    add_dfs = []
    for bird in train['ebird_code'].unique():
        mask = train['ebird_code'] == bird
        _df = train[mask].sort_values('duration')[::-1]
        mask = _df['duration'] > 20
        df = _df[mask]
       
        n_add_file = n_file_max - len(_df)
        idx = 0
        dfs = []
        while len(dfs) < n_add_file:
            dfs.append(df.iloc[[idx], :])
            if len(df)-1 > idx:
                idx += 1
            else:
                idx = 0
        if len(dfs) == 0:
            pass
        else:
            add_dfs.append(pd.concat(dfs))
    df_concat = pd.concat(add_dfs)
    train = pd.concat([train, df_concat]).reset_index(drop=True)
    return train

def remove_short_duration(train):
    '''
    5 sec 未満のデータは学習に使わない
    '''
    mask = train['duration'] >= 5
    train = train[mask].reset_index(drop=True)
    return train


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.info('hello')

    set_seed()

if __name__ == '__main__':
    main()
