import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def save_loss_figure(
        fold_i, epochs, losses_train, 
        losses_valid, save_dir):
    fig = plt.figure()
    plt.plot(epochs, losses_train, '-x', label='train')
    plt.plot(epochs, losses_valid, '-x', label='valid')
    plt.xlabel('epoch')
    plt.grid()
    plt.legend()
    fig.savefig(f'{save_dir}/loss_fold{fold_i}.png')

def save_result_csv(
        fold_i, debug, model_name, loss_name, 
        best_loss, best_f1, comment, save_dir):
    df = pd.DataFrame({
        'run_name': [save_dir.split('hydra_outputs/')[1]],
        'debug': [debug],
        'fold': [fold_i],
        'model_name': [model_name],
        'loss_name': [loss_name],
        'best_loss': [round(best_loss, 6)],
        'best_f1(macro)': [round(best_f1, 6)],
        'comment': [comment]
        })
    df.to_csv(f'{save_dir}/result_fold{fold_i}.csv', index=False)
