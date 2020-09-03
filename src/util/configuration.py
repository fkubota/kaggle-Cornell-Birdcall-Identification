import pandas as pd
import sklearn.model_selection as sms
import hydra

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
    melspectrogram_parameters = dataset_config["params"]
    loader_config = config["loader"][phase]

    dataset = datasets.SpectrogramDataset(
        df,
        datadir=datadir,
        img_size=dataset_config["img_size"],
        waveform_transforms=waveform_transforms,
        spectrogram_transforms=spectrogram_transforms,
        melspectrogram_parameters=melspectrogram_parameters)
    loader = data.DataLoader(dataset, **loader_config)
    return loader
