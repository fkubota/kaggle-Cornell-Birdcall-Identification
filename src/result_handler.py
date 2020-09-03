import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def save_loss_figure(epochs, losses_train, losses_valid, save_dir):
    fig = plt.figure()
    plt.plot(epochs, losses_train, '-x', label='train')
    plt.plot(epochs, losses_valid, '-x', label='valid')
    plt.xlabel('epoch')
    plt.grid()
    plt.legend()
    fig.savefig(f'{save_dir}/loss.png')

def save_result_csv(
        debug, model_name, loss_name, 
        best_loss, best_f1, save_dir):
    df = pd.DataFrame({
        'debug': debug,
        'model_name': model_name,
        'loss_name': loss_name,
        'best_loss': best_loss,
        'best_f1(macro)': best_f1,
        })
    df.to_csv(f'{save_dir}/result.csv')
