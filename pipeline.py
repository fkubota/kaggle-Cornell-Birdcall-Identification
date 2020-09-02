import warnings
warnings.filterwarnings('ignore')
import hydra
import logging
from fastprogress import progress_bar
from omegaconf import DictConfig
from src import utils
from src import configuration as C
from src import models
from src.early_stopping import EarlyStopping
from src.train import train
import time

logger = logging.getLogger(__name__)


@hydra.main(config_path="./config/base_config.yaml")
def run(cfg: DictConfig) -> None:
    logger.info('logger start')
    logger.info(f'all params\n{"="*70}\n{cfg.pretty()}\n{"="*70}')

    global_params = cfg["globals"]
    utils.set_seed(50)
    device = C.get_device(global_params["device"])
    splitter = C.get_split(cfg)
    df, datadir = C.get_metadata(cfg)

    for i, (trn_idx, val_idx) in enumerate(
            splitter.split(df, y=df["ebird_code"])):
        if i not in global_params["folds"]:
            continue
        logger.info("=" * 20)
        logger.info(f"Fold {i}")
        logger.info("=" * 20)

        trn_df = df.loc[trn_idx, :].reset_index(drop=True)
        val_df = df.loc[val_idx, :].reset_index(drop=True)

        train_loader = C.get_loader(trn_df, datadir, cfg, 'train')
        valid_loader = C.get_loader(val_df, datadir, cfg, 'valid')

        model = models.get_model(cfg).to(device)
        criterion = C.get_criterion(cfg).to(device)
        optimizer = C.get_optimizer(model, cfg)
        scheduler = C.get_scheduler(optimizer, cfg)

        losses_train = []
        losses_valid = []
        epochs = []
        save_path = './hoge'
        early_stopping = EarlyStopping(patience=12, verbose=True, path=save_path)
        n_epoch = cfg['globals']['num_epochs']
        for epoch in progress_bar(range(1, n_epoch+1)):
            logger.info(f'\n epoch: {epoch} {time.ctime()}')
            loss_train = train(
                    model, device, train_loader, 
                    optimizer, scheduler, criterion)
            loss_valid, f_score_valid = get_epoch_loss_score(
                    model, device, valid_loader, criterion)
            logger.info(f'loss_train: {loss_train:.6f}, loss_valid: {loss_valid:.6f}, f1(macro): {f_score_valid:.6f}')

            epochs.append(epoch)
            losses_train.append(loss_train)
            losses_valid.append(loss_valid)

            early_stopping(loss_valid, model)

            if early_stopping.early_stop:
                print("Early stopping")
                break

if __name__ == "__main__":
    run()
