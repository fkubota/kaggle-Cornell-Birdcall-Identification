import os
import hydra
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from model_lib import lib_resnest

from torchvision import models


def get_model(config: dict):
    model_config = config["model"]
    model_name = model_config["name"]
    model_params = model_config["params"]

    model = eval(model_name)(model_params)
    return model

####################################################################3
#     Resnet50
####################################################################3
class ResNet50(nn.Module):
    def __init__(self, params):
        super().__init__()
        self.__class__.__name__ = 'ResNet50'
        base_model_name = params['base_model']
        pretrained = params['pretrained']
        num_classes = params['n_classes']
        base_model = models.__getattribute__(
                base_model_name)(pretrained=pretrained)
        layers = list(base_model.children())[:-2]
        layers.append(nn.AdaptiveMaxPool2d(1))
        self.encoder = nn.Sequential(*layers)

        in_features = base_model.fc.in_features
        self.classifier = nn.Sequential(
            nn.Linear(in_features, 1024), nn.ReLU(), nn.Dropout(p=0.2),
            nn.Linear(1024, 1024), nn.ReLU(), nn.Dropout(p=0.2),
            nn.Linear(1024, num_classes))

    def forward(self, x):
        batch_size = x.size(0)
        x = self.encoder(x)
        x = x.view(batch_size, -1)
        x = self.classifier(x)
        multiclass_proba = F.softmax(x, dim=1)
        multilabel_proba = F.sigmoid(x)
        return {
            "logits": x,
            "multiclass_proba": multiclass_proba,
            "multilabel_proba": multilabel_proba
        }


####################################################################3
#     Resnest
####################################################################3
# ref: https://www.kaggle.com/ttahara/inference-birdsong-baseline-resnest50-fast
# ref: https://www.kaggle.com/hidehisaarai1213/inference-pytorch-birdcall-resnet-baseline
class ResNeSt(nn.Module):
    def __init__(self, params):
        super().__init__()
        num_classes = params['n_classes']
        self.classifier = lib_resnest.ResNet(
            lib_resnest.Bottleneck, [3, 4, 6, 3],
            radix=1, groups=1, bottleneck_width=64,
            deep_stem=True, stem_width=32, avg_down=True,
            avd=True, avd_first=True)

        this_file_dir = os.path.dirname(__file__)
        state_dict = torch.load(f'{this_file_dir}/../data_ignore/model/resnest50/'\
                'resnest50_fast_1s1x64d-d8fbf808.pth')
        self.classifier.load_state_dict(state_dict)
        
        del self.classifier.fc
        # # use the same head as the baseline notebook.
        self.classifier.fc = nn.Sequential(
            nn.Linear(2048, 1024), nn.ReLU(), nn.Dropout(p=0.2),
            nn.Linear(1024, 1024), nn.ReLU(), nn.Dropout(p=0.2),
            nn.Linear(1024, num_classes))
        device = torch.device("cuda")
        self.classifier.to(device)
        self.classifier.eval()

    def forward(self, x):
        x = self.classifier.conv1(x)
        x = self.classifier.bn1(x)
        x = self.classifier.relu(x)
        x = self.classifier.maxpool(x)

        x = self.classifier.layer1(x)
        x = self.classifier.layer2(x)
        x = self.classifier.layer3(x)
        x = self.classifier.layer4(x)

        x = self.classifier.avgpool(x)
#x = x.view(x.size(0), -1)
        x = torch.flatten(x, 1)
        if self.classifier.drop:
            x = self.classifier.drop(x)
        x = self.classifier.fc(x)

        multiclass_proba = F.softmax(x, dim=1)
        multilabel_proba = F.sigmoid(x)
        return {
            "logits": x,
            "multiclass_proba": multiclass_proba,
            "multilabel_proba": multilabel_proba
        }
