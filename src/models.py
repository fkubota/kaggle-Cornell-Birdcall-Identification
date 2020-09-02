import numpy as np
import torch.nn as nn
import torch.nn.functional as F

from torchvision import models


class ResNet50(nn.Module):
    def __init__(self, params):
        super().__init__()
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


def get_model(config: dict):
    model_config = config["model"]
    model_name = model_config["name"]
    model_params = model_config["params"]

    model = eval(model_name)(model_params)
    return model
