import warnings
warnings.filterwarnings('ignore')
import os
import gc
import hydra
import torch
import logging
import subprocess
from fastprogress import progress_bar
from omegaconf import DictConfig
from src import utils
from src import configuration as C
from src import models
from src.early_stopping import EarlyStopping
from src.train import train
from src.eval import get_epoch_loss_score
import src.result_handler as rh

cmd = "git rev-parse --short HEAD"
hash_ = subprocess.check_output(cmd.split()).strip().decode('utf-8')
logger = logging.getLogger(__name__)


@hydra.main(config_path="./run_config.yaml")
def run(cfg: DictConfig) -> None:
    logger.info('='*30)
    logger.info('::: pipeline start :::')
    logger.info('='*30)
    logger.info(f'git hash is: {hash_}')
    logger.info(f'all params\n{"="*80}\n{cfg.pretty()}\n{"="*80}')
    comment = cfg['globals']['comment']
    assert comment!=None, 'commentを入力してください。(globals.commet=hogehoge)'

    if cfg['globals']['debug']:
        logger.info('::: set debug mode :::')
        cfg = utils.get_debug_config(cfg)

    global_params = cfg["globals"]
    utils.set_seed(50)
    device = C.get_device(global_params["device"])
    splitter = C.get_split(cfg)
    df, datadir = C.get_metadata(cfg)
    logger.info(f'meta_df: {df.shape}')
    output_dir = os.getcwd()
    output_dir_ignore = output_dir.replace('/data/', '/data_ignore/')
    if not os.path.exists(output_dir_ignore):
            os.makedirs(output_dir_ignore)

    for fold_i, (trn_idx, val_idx) in enumerate(
            splitter.split(df, y=df["ebird_code"])):
        if fold_i not in global_params["folds"]:
            continue
        logger.info("=" *30)
        logger.info(f"Fold {fold_i}")
        logger.info("=" *30)

        trn_df = df.loc[trn_idx, :].reset_index(drop=True)
        val_df = df.loc[val_idx, :].reset_index(drop=True)
        if global_params['remove_short']:
            logger.info(f'::: remove short duration :::')
            trn_df = utils.remove_short_duration(trn_df)
        if global_params['balanced']:
            logger.info(f'::: train class balanced :::')
            trn_df = utils.transform_balanced_dataset(trn_df)
        if global_params['debug']:
            trn_df = utils.get_debug_df(trn_df)
            val_df = utils.get_debug_df(val_df)

        logger.info(f'trn_df: {trn_df.shape}')
        logger.info(f'val_df: {val_df.shape}')
        train_loader = C.get_loader(trn_df, datadir, cfg, 'train')
        valid_loader = C.get_loader(val_df, datadir, cfg, 'valid')

        model = models.get_model(cfg).to(device)
        criterion = C.get_criterion(cfg).to(device)
        optimizer = C.get_optimizer(model, cfg)
        scheduler = C.get_scheduler(optimizer, cfg)

        losses_train = []
        losses_valid = []
        epochs = []
        best_f1 = 0
        best_loss = 0
        save_path = f'{output_dir_ignore}/{model.__class__.__name__}_fold{fold_i}.pth'
        early_stopping = EarlyStopping(patience=12, verbose=True, path=save_path)
        n_epoch = cfg['globals']['num_epochs']
        for epoch in progress_bar(range(1, n_epoch+1)):
            logger.info(f'::: epoch: {epoch}/{n_epoch} :::')
            loss_train = train(
                    model, device, train_loader, 
                    optimizer, scheduler, criterion)
            loss_valid, fscore_valid = get_epoch_loss_score(
                    model, device, valid_loader, criterion)
            logger.info(f'loss_train: {loss_train:.6f}, loss_valid: {loss_valid:.6f}, f1(macro): {fscore_valid:.6f}')

            epochs.append(epoch)
            losses_train.append(loss_train)
            losses_valid.append(loss_valid)

            is_update = early_stopping(loss_valid, model, global_params['debug'])
            if is_update:
                best_loss = loss_valid
                best_f1 = fscore_valid 

            if early_stopping.early_stop:
                logger.info("Early stopping")
                break

        # result handling
        rh.save_loss_figure(
                fold_i,
                epochs, losses_train,
                losses_valid, output_dir)
        rh.save_result_csv(
                fold_i,
                global_params['debug'],
                f'{model.__class__.__name__}',
                cfg['loss']['name'],
                best_loss, best_f1, 
                comment,
                output_dir)
        logger.info(f'best_loss: {best_loss:.6f}, best_fscore(macro): {best_f1:.6f}')
    logger.info('::: success :::\n\n\n')

    # 開放
    del train_loader
    del valid_loader
    del model
    del optimizer
    del scheduler
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    run()
