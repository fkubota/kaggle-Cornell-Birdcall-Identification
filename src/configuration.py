import os
import sys
import hydra
import pandas as pd
import sklearn.model_selection as sms

import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data

sys.path.insert(0, f'{os.getcwd()}/src')
import const
import datasets
import criterion

def get_device(device: str):
    return torch.device(device)

def get_split(config: dict):
    split_config = config["split"]
    name = split_config["name"]

    return sms.__getattribute__(name)(**split_config["params"])

def get_metadata(config: dict):
    ori_path = hydra.utils.get_original_cwd()
    data_config = config["data"]

    path_train_csv = f'{ori_path}/{data_config["train_df_path"]}'
    path_audio = f'{ori_path}/{data_config["train_audio_path"]}'
    train = pd.read_csv(path_train_csv)
    return train, path_audio

def get_loader(df: pd.DataFrame,
               datadir,
               config: dict,
               phase: str):
    dataset_config = config["dataset"]
    name = dataset_config['name']
    loader_config = config["loader"][phase]

    dataset = datasets.__getattribute__(name)(
            df,
            datadir=datadir,
            img_size=dataset_config['img_size'],
            config=dataset_config['params']
            )
    loader = data.DataLoader(dataset, **loader_config)
    return loader

def get_criterion(config: dict):
    loss_config = config["loss"]
    loss_name = loss_config["name"]
    loss_params = loss_config["params"]
    if (loss_params is None) or (loss_params == ""):
        loss_params = {}

    if hasattr(nn, loss_name):
        criterion_ = nn.__getattribute__(loss_name)(**loss_params)
    else:
        criterion_cls = criterion.__getattribute__(loss_name)
        if criterion_cls is not None:
            criterion_ = criterion_cls(**loss_params)
        else:
            raise NotImplementedError

    return criterion_

def get_optimizer(model: nn.Module, config: dict):
    optimizer_config = config["optimizer"]
    optimizer_name = optimizer_config.get("name")

    return optim.__getattribute__(optimizer_name)(model.parameters(),
                                                  **optimizer_config["params"])

def get_scheduler(optimizer, config: dict):
    scheduler_config = config["scheduler"]
    scheduler_name = scheduler_config.get("name")

    if scheduler_name is None:
        return
    else:
        return optim.lr_scheduler.__getattribute__(scheduler_name)(
            optimizer, **scheduler_config["params"])
