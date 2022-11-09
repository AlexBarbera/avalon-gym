import keras
import numpy
import AgentFactory
import AvalonGameMaster

fallo_delta = 0.1
REWARD_MISSION = 0.2
REWARD_TEAM = 0.2
REWARD_WIN = 1.0


def train_agent(agent, memory):
    for game in memory:
        for play in game:
            agent.fit(play[0], play[1], batch_size=1, epochs=1, verbose=1)

        agent.reset_states()

class AvalonNNAgent(AgentFactory.BaseAgent):
    def __init__(self, master, *args, **kwargs):
        super(AvalonNNAgent, self).__init__(master)
        self.memory = []
        self.current_game_memory = []
        self.models = None
        self.my_opinion = None
        self.others_opinion = None
        self.buffer = []
        self.current_game = []

    def initialize(self):
        if self.models is None:
            self.__build_model()

        for m in self.models:
            m.reset_states()

        self.my_opinion = numpy.zeros((len(self.game.players), len(self.game.settings.get_roles())))
        self.others_opinion = numpy.zeros((len(self.game.players) - 1, len(self.game.players), len(self.game.settings.get_roles())))

        self.current_game = []

    def role_shown(self, player, role):
        self.game.logger.log("I, player {}, know that {} is {}.".format(self.id, player, role))
        self.my_opinion[player] = 1 if role in AvalonGameMaster.GOOD else -1

    def __build_model(self):
        in_self_opinion = keras.layers.Input(batch_shape=(1, 1, 1, self.game.settings.num_players, len(self.game.settings.get_roles())))  # nplayers x n_roles
        in_other_opinion = keras.layers.Input(batch_shape=(1, 1, len(self.game.players) - 1, len(self.game.players), len(self.game.settings.get_roles())))  # nPLayers - 1 x nPlayers - 1 x 3

        in_team = keras.layers.Input(shape=(len(self.game.players),))

        inputs = keras.layers.concatenate([in_other_opinion, in_self_opinion], axis=2) # ahora es una matriz de NxN

        h = keras.layers.ConvLSTM2D(128, (1,1), return_sequences=True, stateful=True)(inputs)
       # h = keras.layers.ConvLSTM2D(64, (1,1), return_sequences=True, stateful=True)(h)
        h = keras.layers.ConvLSTM2D(32, (1,1), stateful=True)(h)

        output_vote_team = keras.layers.Dense(1, activation="sigmoid", name="output_vote_team")(keras.layers.Dense(16, activation="relu")(keras.layers.Flatten()(h)))
        output_vote_mission = keras.layers.Dense(1, activation="sigmoid", name="output_vote_mission")(keras.layers.Dense(16, activation="relu")(keras.layers.Flatten()(h)))
        output_make_team = keras.layers.Dense(len(self.game.players), activation="softmax", name="output_make_team")(keras.layers.Dense(16, activation="relu")(keras.layers.Flatten()(h)))

        output_my_opinion = keras.layers.Conv2D(len(self.game.settings.get_roles()), (5,1), activation="softmax", name="output_roles")(keras.layers.Conv2D(16, (1,1))(h))
        output_opinion = keras.layers.Conv2D(len(self.game.settings.get_roles()), (5,1), activation="softmax", name="output_give_opinion")(keras.layers.Conv2D(16, (1,1))(h))

        model_my_opinion = keras.models.Model([in_other_opinion, in_self_opinion], output_my_opinion)
        model_opinion = keras.models.Model([in_other_opinion, in_self_opinion], output_opinion)

        model_make_team = keras.models.Model([in_other_opinion, in_self_opinion], output_make_team)
        model_vote_team = keras.models.Model([in_other_opinion, in_self_opinion, in_team], output_vote_team)
        model_vote_mission = keras.models.Model([in_other_opinion, in_self_opinion, in_team], output_vote_mission)


        model_my_opinion.compile("nadam", loss=["categorical_crossentropy"])
        model_opinion.compile("nadam", loss=["categorical_crossentropy"])

        model_make_team.compile("nadam", loss=["categorical_crossentropy"])
        model_vote_team.compile("nadam", loss=["binary_crossentropy"])
        model_vote_mission.compile("nadam", loss=["binary_crossentropy"])
        # output.compile("adam", loss={"output_vote":"binary_crossentropy", "output_team":"categorical_crossentropy", "output_opinion":"categorical_crossentropy"}, metrics=["acc"])

        self.models = (model_my_opinion, model_opinion, model_make_team, model_vote_team, model_vote_mission)


    # event showing result of current mission vote
    def mission_vote_result(self, mission, team, result):
        pass

    # event showing result of vote
    def team_vote_result(self, team, votes):
        pass

    def vote_mission(self, mission):
        team = numpy.zeros((1, len(self.game.players)))
        team[0, mission.assigned_team] = 1
        s1 = self.others_opinion.shape
        s2 = self.my_opinion.shape

        x = self.models[4].predict([self.others_opinion.reshape((1,1) + s1), self.my_opinion.reshape((1,1,1) + s2), team])[0,0]
        print(x)
        return x > 0.5 
    
    def vote_team(self, team):
        s1 = self.others_opinion.shape
        s2 = self.my_opinion.shape
        t = numpy.zeros((1,len(self.game.players)))
        t[0, team] = 1
        x = self.models[3].predict([self.others_opinion.reshape((1,1) + s1), self.my_opinion.reshape((1,1,1) + s2), t])[0,0]
        print(x, self.models[3].layers[-1].name)
        return 1 if x > 0.5 else 0

    def end_game(self, have_won, win_condition, roles):
        r = 1 if have_won else -1

        for i in range(len(self.current_game)):
            self.current_game[i][1] = r + self.current_game[i][1]

        self.buffer.append(self.current_game)

        # TODO train
        self.current_game = []

    def give_my_opinion(self):
        s1 = self.others_opinion.shape
        s2 = self.my_opinion.shape

        x = self.models[1].predict([self.others_opinion.reshape((1,1) + s1), self.my_opinion.reshape((1,1,1) + s2)])
        return x

    def player_given_opinion(self, player, opinion):
        aux = player.id
        if aux > self.id:
            aux -= 1

        self.others_opinion[aux] = opinion

    def train(self):
        pass

