from __future__ import print_function
import threading
import time
import AvalonGameMaster
import AvalonNN
import random
import AgentFactory
import numpy
import argparse
import sys
import tensorflow
import keras
import timeit

import traceback

from matplotlib import pyplot as plt

def get_args(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("--num-agents", type=int, help="Number of agents to play.", default=5)
    parser.add_argument("--num-games", type=int, help="Number of games to be simmulated.", default=1000)
    parser.add_argument("--with-gpu", help="Train with gpu.", action="store_true")
    parser.add_argument("--tensorboard-path", help="Path to tensorboard directory (empty if no tensorboard).", default="/tmp/tensorboard")
    return parser.parse_args(argv[1:])

def plot_results(res):
    ind = numpy.arange(len(AvalonGameMaster.END_GAME_REASONS))
    plt.bar(ind, numpy.asarray(res), color=["red", "green", "red", "red"], edgecolor="black")
    plt.xticks(ind, AvalonGameMaster.END_GAME_REASONS,horizontalalignment = 'center')
    plt.ylabel("Frequency", fontweight='bold')
    plt.xlabel("End game reason.", fontweight='bold')
    plt.title("Avalon game outcomes after {} games.".format(sum(res)))

    for i,j in enumerate(res):
        plt.text(x=i-0.11, y=j+5, s=str(j), size=10)


    plt.show()    

def test():
    settings = AvalonGameMaster.GameSettings()
    settings.use_percival = True


    master = AvalonGameMaster.GameMaster(settings)
    a = AvalonNN.AvalonNNAgent(master)
    b = AvalonNN.AvalonNNAgent(master)
    c = AvalonNN.AvalonNNAgent(master)

    master.register_player(a)
    master.register_player(b)
    master.register_player(c)
    a.initialize()
    print("YA")

if __name__ == "__main__":
    args = get_args(sys.argv)

    t = timeit.default_timer()

    results = [0] * len(AvalonGameMaster.END_GAME_REASONS)

    settings = AvalonGameMaster.GameSettings()
    #settings.use_percival = True


    master = AvalonGameMaster.GameMaster(settings)
    master.logger.verbose = True
    players = []

    if args.with_gpu:
        config = tensorflow.ConfigProto()
        config.log_device_placement = False
        config.gpu_options.allow_growth = True
        config.gpu_options.force_gpu_compatible = True

        session = tensorflow.Session(config=config)

        keras.backend.tensorflow_backend.set_session(session)

    for i in range(args.num_agents):
        players.append(AvalonNN.AvalonNNAgent(master)) # (AgentFactory.BasicAgent(master))

    for p in players:
        master.register_player(p)

    for p in players:
        p.initialize()
    try:
        for i in range(args.num_games):
            master.run(t=t)
            res = master.join()
            print(res[0], "\n", res[2], AvalonGameMaster.END_GAME_REASONS[res[0]])

            results[res[2]] += 1

        print(results)
        plot_results(results)
    except:
        a,b,c = sys.exc_info()
        print("EPIC FAIL!\n{}\n{}".format(sys.exc_info()[1], "\n".join(traceback.format_exception(a,b,c))))
        exit()
