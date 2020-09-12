import os
import cv2
import hydra
import pickle
import random
import librosa
import numpy as np
import pandas as pd
import soundfile as sf
import torch.utils.data as data
from const import BIRD_CODE, INV_BIRD_CODE
from albumentations.core.transforms_interface import DualTransform, BasicTransform
import albumentations as albu

PERIOD = 5


def mono_to_color(X: np.ndarray,
                  mean=None,
                  std=None,
                  norm_max=None,
                  norm_min=None,
                  eps=1e-6):
    # Stack X as [X,X,X]
    X = np.stack([X, X, X], axis=-1)

    # Standardize
    mean = mean or X.mean()
    X = X - mean
    std = std or X.std()
    Xstd = X / (std + eps)
    _min, _max = Xstd.min(), Xstd.max()
    norm_max = norm_max or _max
    norm_min = norm_min or _min
    if (_max - _min) > eps:
        # Normalize to [0, 255]
        V = Xstd
        V[V < norm_min] = norm_min
        V[V > norm_max] = norm_max
        V = 255 * (V - norm_min) / (norm_max - norm_min)
        V = V.astype(np.uint8)
    else:
        # Just zero
        V = np.zeros_like(Xstd, dtype=np.uint8)
    return V


class AudioTransform(BasicTransform):
    """ Transform for audio task. This is the main class where we override the targets and update params function for our need"""
    @property
    def targets(self):
        return {"data": self.apply}
    def update_params(self, params, **kwargs):
        if hasattr(self, "interpolation"):
            params["interpolation"] = self.interpolation
        if hasattr(self, "fill_value"):
            params["fill_value"] = self.fill_value
        return params
class AddGaussianNoise(AudioTransform):
    """ Do time shifting of audio """
    def __init__(self, always_apply=False, p=0.5):
        super(AddGaussianNoise, self).__init__(always_apply, p)
    def apply(self,data,**params):
        '''
        data : ndarray of audio timeseries
        '''
        noise = np.random.randn(len(data))
        data_wn = data + 0.005*noise
        return data_wn
class NoAugment(AudioTransform):
    """ Do time shifting of audio """
    def __init__(self, always_apply=False):
        super(NoAugment, self).__init__(always_apply)
    def apply(self,data,**params):
        '''
        data : ndarray of audio timeseries
        '''
        return data
def get_augmentation():
    train_transform = [
#         PitchShift(p=1.0,n_steps=4),
        AddGaussianNoise(p=1.0),
        NoAugment(),
    ]
    return albu.OneOf(train_transform)  # <- Compose

class SpectrogramDataset(data.Dataset):
    def __init__(self,
                 df: pd.DataFrame,
                 datadir,
                 phase,
                 config={}):
        self.df = df
        self.datadir = datadir
        self.img_size = config['img_size']
        self.melspectrogram_parameters = config['melspectrogram_parameters']

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx: int):
        sample = self.df.loc[idx, :]
        wav_name = sample["resampled_filename"]
        ebird_code = sample["ebird_code"]
        train_resampled_audio_dirs = [self.datadir + "/birdsong-resampled-train-audio-{:0>2}".format(i)  for i in range(5)]
        for dir_ in train_resampled_audio_dirs:
            path = f'{dir_}/{ebird_code}/{wav_name}'
            if os.path.exists(path):
                path_wav = path

        y, sr = sf.read(path_wav)

        len_y = len(y)
        effective_length = sr * PERIOD
        if len_y < effective_length:
            new_y = np.zeros(effective_length, dtype=y.dtype)
            start = np.random.randint(effective_length - len_y)
            new_y[start:start + len_y] = y
            y = new_y.astype(np.float32)
        elif len_y > effective_length:
            start = np.random.randint(len_y - effective_length)
            y = y[start:start + effective_length].astype(np.float32)
        else:
            y = y.astype(np.float32)

        melspec = librosa.feature.melspectrogram(y, sr=sr, **self.melspectrogram_parameters)
        melspec = librosa.power_to_db(melspec).astype(np.float32)
        image = mono_to_color(melspec)
        height, width, _ = image.shape
        image = cv2.resize(image, (int(width * self.img_size / height), self.img_size))
        image = np.moveaxis(image, 2, 0)
        image = (image / 255.0).astype(np.float32)

        labels = np.zeros(len(BIRD_CODE), dtype=int)
        labels[BIRD_CODE[ebird_code]] = 1
        return image, labels

class SpectrogramEventRandomDataset(data.Dataset):
    '''
    Event part と Random Crop part の和を出力する。
    '''
    def __init__(self,
                 df: pd.DataFrame,
                 datadir,
                 phase,
                 config={}):
        self.df = df
        self.datadir = datadir
        self.phase = phase
        self.ratio = config['ratio']
        self.img_size = config['img_size']
        self.melspectrogram_parameters = config['melspectrogram_parameters']
        
        this_file_dir = os.path.dirname(__file__)
        with open(f'{this_file_dir}/../data_ignore/event/nb034_event_intensity_500to16000hz/nb034_event_intensity_500to16000hz.pickle', mode='rb') as f:
            self.df_event = pickle.load(f)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx: int):
        # wav_path, ebird_code = self.file_list[idx]
        sample = self.df.loc[idx, :]
        wav_name = sample["resampled_filename"]
        ebird_code = sample["ebird_code"]
        train_resampled_audio_dirs = [self.datadir + "/birdsong-resampled-train-audio-{:0>2}".format(i)  for i in range(5)]
        for dir_ in train_resampled_audio_dirs:
            path = f'{dir_}/{ebird_code}/{wav_name}'
            if os.path.exists(path):
                path_wav = path



        y, sr = sf.read(path_wav)
        len_y = len(y)
        effective_length = sr * PERIOD
        if len_y < effective_length:
            new_y = np.zeros(effective_length, dtype=y.dtype)
            start = np.random.randint(effective_length - len_y)
            new_y[start:start + len_y] = y
            y = new_y.astype(np.float32)
        elif len_y > effective_length:
            basename = os.path.basename(path_wav)
            event_sec_list = self.df_event.query('filename == @basename').event_sec_list.to_list()[0]
#                 event_sec_list = self.string_to_list(event_sec_list)
            
            # on event (eventあり & train phase)
            if (len(event_sec_list) != 0) & (self.phase == 'train'):
                choice = random.choice(event_sec_list)
                # 前から2.5秒、後ろから2.5秒の範囲におさまってるか(境界問題)
                ed_sec = len_y / sr
                st_range_sec = PERIOD/2 + 0.0001
                ed_range_sec = ed_sec - st_range_sec
                range_in = (st_range_sec <= choice) & (choice <= ed_range_sec)
                if range_in:
                    event_start = int((choice - PERIOD/2) * sr)
                    event_y = y[event_start:event_start + effective_length].astype(np.float32)
                    start = np.random.randint(len_y - effective_length)
                    y = y[start:start + effective_length].astype(np.float32)
                    y += event_y
                    y = (1-self.ratio)*y + self.ratio*event_y
                else:
                    # ランダムにクロップ
                    start = np.random.randint(len_y - effective_length)
                    y = y[start:start + effective_length].astype(np.float32)
            # off event
            else:
                # event を検出できなかったらランダムにクロップ
                start = np.random.randint(len_y - effective_length)
                y = y[start:start + effective_length].astype(np.float32)
                
            # ----
        else:
            y = y.astype(np.float32)

        melspec = librosa.feature.melspectrogram(y, sr=sr, **self.melspectrogram_parameters)
        melspec = librosa.power_to_db(melspec).astype(np.float32)

        image = mono_to_color(melspec)
        height, width, _ = image.shape
        image = cv2.resize(image, (int(width * self.img_size / height), self.img_size))
        image = np.moveaxis(image, 2, 0)
        image = (image / 255.0).astype(np.float32)

        #         labels = np.zeros(len(BIRD_CODE), dtype="i")
        labels = np.zeros(len(BIRD_CODE), dtype="f")
        labels[BIRD_CODE[ebird_code]] = 1


        return image, labels


class SpectrogramMultiRandomDataset(data.Dataset):
    def __init__(self,
                 df: pd.DataFrame,
                 datadir,
                 phase,
                 config={}):
        self.df = df
        self.datadir = datadir
        self.phase = phase
        self.img_size = config['img_size']
        self.melspectrogram_parameters = config['melspectrogram_parameters']
        self.n_random = config['n_random']

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx: int):
        sample = self.df.loc[idx, :]
        wav_name = sample["resampled_filename"]
        ebird_code = sample["ebird_code"]
        train_resampled_audio_dirs = [self.datadir + "/birdsong-resampled-train-audio-{:0>2}".format(i)  for i in range(5)]
        for dir_ in train_resampled_audio_dirs:
            path = f'{dir_}/{ebird_code}/{wav_name}'
            if os.path.exists(path):
                path_wav = path

        y, sr = sf.read(path_wav)

        len_y = len(y)
        effective_length = sr * PERIOD
        if len_y < effective_length:
            new_y = np.zeros(effective_length, dtype=y.dtype)
            start = np.random.randint(effective_length - len_y)
            new_y[start:start + len_y] = y
            y = new_y.astype(np.float32)
        elif len_y > effective_length:
            if self.phase == 'train':
                y_tmp = 0
                for _ in range(self.n_random):
                    start = np.random.randint(len_y - effective_length)
                    _y = y[start:start + effective_length].astype(np.float32)
                    y_tmp = y_tmp + _y
                y = y_tmp
            elif self.phase == 'valid':
                start = np.random.randint(len_y - effective_length)
                y = y[start:start + effective_length].astype(np.float32)
        else:
            y = y.astype(np.float32)

        melspec = librosa.feature.melspectrogram(y, sr=sr, **self.melspectrogram_parameters)
        melspec = librosa.power_to_db(melspec).astype(np.float32)
        image = mono_to_color(melspec)
        height, width, _ = image.shape
        image = cv2.resize(image, (int(width * self.img_size / height), self.img_size))
        image = np.moveaxis(image, 2, 0)
        image = (image / 255.0).astype(np.float32)

        labels = np.zeros(len(BIRD_CODE), dtype=int)
        labels[BIRD_CODE[ebird_code]] = 1
        return image, labels

class SpectrogramDatasetWithNoise(data.Dataset):
    def __init__(self,
                 df: pd.DataFrame,
                 datadir,
                 phase,
                 config={}):
        self.df = df
        self.datadir = datadir
        self.img_size = config['img_size']
        self.melspectrogram_parameters = config['melspectrogram_parameters']

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx: int):
        sample = self.df.loc[idx, :]
        wav_name = sample["resampled_filename"]
        ebird_code = sample["ebird_code"]
        train_resampled_audio_dirs = [self.datadir + "/birdsong-resampled-train-audio-{:0>2}".format(i)  for i in range(5)]
        for dir_ in train_resampled_audio_dirs:
            path = f'{dir_}/{ebird_code}/{wav_name}'
            if os.path.exists(path):
                path_wav = path

        y, sr = sf.read(path_wav)
        # Noise
        transforms = get_augmentation()
        y = transforms(data=y)['data']

        len_y = len(y)
        effective_length = sr * PERIOD
        if len_y < effective_length:
            new_y = np.zeros(effective_length, dtype=y.dtype)
            start = np.random.randint(effective_length - len_y)
            new_y[start:start + len_y] = y
            y = new_y.astype(np.float32)
        elif len_y > effective_length:
            start = np.random.randint(len_y - effective_length)
            y = y[start:start + effective_length].astype(np.float32)
        else:
            y = y.astype(np.float32)

        melspec = librosa.feature.melspectrogram(y, sr=sr, **self.melspectrogram_parameters)
        melspec = librosa.power_to_db(melspec).astype(np.float32)
        image = mono_to_color(melspec)
        height, width, _ = image.shape
        image = cv2.resize(image, (int(width * self.img_size / height), self.img_size))
        image = np.moveaxis(image, 2, 0)
        image = (image / 255.0).astype(np.float32)

        labels = np.zeros(len(BIRD_CODE), dtype=int)
        labels[BIRD_CODE[ebird_code]] = 1
        return image, labels
