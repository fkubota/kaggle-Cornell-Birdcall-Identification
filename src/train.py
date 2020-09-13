import logging
from criterion import mixup_criterion
from utils import mixup_data

def train(model, device, train_loader, optimizer, scheduler, loss_func, mixup=False):
    model.train()
    epoch_train_loss = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        if mixup:
            data, targets_a, targets_b, lam = mixup_data(data, target, alpha=1.0)

        optimizer.zero_grad()
        output = model(data)
        if mixup:
            loss = mixup_criterion(loss_func, output, targets_a, targets_b, lam)
        else:
            loss = loss_func(output, target)
        loss.backward()
        optimizer.step()
        epoch_train_loss += loss.item()*data.size(0)
    scheduler.step()
    loss = epoch_train_loss / len(train_loader.dataset)
    del data
    return loss

