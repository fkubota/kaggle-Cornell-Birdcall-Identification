import warnings
warnings.filterwarnings('ignore')
import hydra
from omegaconf import DictConfig
import logging
from src import utils
from src import configuration as C
from src import models
from src.early_stopping import EarlyStopping
# import src.early_stopping as es

logger = logging.getLogger(__name__)

def train(model, device, train_loader, optimizer, scheduler, loss_func):
    model.train()
    epoch_train_loss = 0
    for batch_idx, (data, target) in enumerate(progress_bar(train_loader)):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = loss_func(output, target)
        loss.backward()
        optimizer.step()
        epoch_train_loss += loss.item()*data.size(0)
    scheduler.step()
    loss = epoch_train_loss / len(train_loader.dataset)
    del data
    return loss



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

        loaders = {
            phase: C.get_loader(df_, datadir, cfg, phase)
            for df_, phase in zip([trn_df, val_df], ["train", "valid"])
        }
        model = models.get_model(cfg).to(device)
        criterion = C.get_criterion(cfg).to(device)
        optimizer = C.get_optimizer(model, cfg)
        scheduler = C.get_scheduler(optimizer, cfg)

        losses_train = []
        losses_valid = []
        epochs = []
        early_stopping = EarlyStopping(patience=12, verbose=True, path=save_path)
        n_epoch = settings['globals']['num_epochs']
# n_epoch = 50
        # for epoch in progress_bar(range(1, n_epoch+1)):
        #     print(f'\n epoch: {epoch} {time.ctime()}')
        #     loss_train = train(model, device, train_loader, optimizer, scheduler, loss_func)
        #     loss_valid, f_score_valid = get_epoch_loss_score(model, device, valid_loader, loss_func)
        #     print(f'loss_train: {loss_train:.6f}, loss_valid: {loss_valid:.6f}, f1(macro): {f_score_valid:.6f}')
        #     
        #     epochs.append(epoch)
        #     losses_train.append(loss_train)
        #     losses_valid.append(loss_valid)
        #     
        #     early_stopping(loss_valid, model)
        # 
        #     if early_stopping.early_stop:
        #         print("Early stopping")
        #         break

if __name__ == "__main__":
    run()
