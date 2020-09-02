import os
import torch
import random
import numpy as np
import logging

logger = logging.getLogger(__name__)

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)  # type: ignore
    torch.backends.cudnn.deterministic = True  # type: ignore
    torch.backends.cudnn.benchmark = True  # type: ignore
    logger.info(f'seed: {seed}')


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
