import AvalonGameMaster
import threading
import time
import AvalonGameMaster
import random


class BaseAgent(threading.Thread):

    def __init__(self, master):
        super(BaseAgent, self).__init__()
        self.game = master
        self.game_over=False
        self.id = 0
        self.role = None
        self.daemon = True

    def run(self):
        while not self.game_over:
            pass

    def role_shown(self, player, role):
        self.game.logger.log("I, player {}, know that {} is {}.".format(self.id, player, role))

    def player_given_opinion(self, player, opinion):
        pass

    def give_my_opinion(self):
        pass

    def propose_team(self, n_players):
        p = random.sample(range(len(self.game.players)), n_players)
        self.game.logger.log("I, player {}, propose team: {}.".format(self.id, p))
        return p

    def vote_team(self, team):
        vote = bool(random.getrandbits(1))
        self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, vote, team))
        return 1 if vote else 0

    def vote_mission(self, mission):
        vote = bool(random.getrandbits(1))
        self.game.logger.log("I, player {}, vote {} to mission {}.".format(self.id, vote, mission))
        return 1 if vote else 0

    # event showing result of current mission vote
    def mission_vote_result(self, mission, team, result):
        pass

    # event showing result of vote
    def team_vote_result(self, team, votes):
        pass

    # event showing who is the new king
    def new_king(self, new_king_index):
        self.game.logger.log("I, player {}, see {} as new king.".format(self.id, new_king_index))

    def identify_self(self, role):
        self.id = role[0]
        self.role = role[1]
        self.game.logger.log("I, player {}, know that I am {}.".format(self.id, self.role))

    def guess_merlin(self):
        return random.sample(list(set(list(range(len(self.game.players)))) - set([self.id])), 1)[0]

    def end_game(self, have_won, win_condition, roles):
        self.game_over = True

    def set_master(self, new_master):
        self.game = new_master

    def show(self):
        self.game.logger.log("Value: {}".format(self.game_over))


class BasicAgent(BaseAgent):
    def __init__(self, master):
        super(BasicAgent, self).__init__(master)
        self.buddies = []
        self.bad = []
        self.suspects = []


    def role_shown(self, player, role):
        self.game.logger.log("I, player {}, know that {} is {}.".format(self.id, player, role))
        if (self.role in AvalonGameMaster.BAD and role in AvalonGameMaster.BAD) or (self.role in AvalonGameMaster.GOOD and role in AvalonGameMaster.GOOD) :
            self.buddies.append(player)
        else:
            self.bad.append(player)

    def propose_team(self, n_players):
        if self.role == AvalonGameMaster.PlayerType.MERLIN:
            new_list = random.sample(list(set(range(len(self.game.players))) - set(self.bad)), n_players)
            #new_list += random.sample(self.bad, n_players - len(new_list))

            return new_list

        elif self.role in AvalonGameMaster.GOOD:
            p = super(BasicAgent, self).propose_team(n_players)
            self.game.logger.log("I, player {}, propose team: {}.".format(self.id, p))
            return p
        else:
            new_list = self.buddies + random.sample(list(set(range(len(self.game.players))) - set(self.buddies)), n_players - len(self.buddies))
            return new_list

    def vote_team(self, team):
        if self.role in AvalonGameMaster.BAD:
            if self.id in team or any([b in team for b in self.buddies]):

                self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, True, team))
                return 1
            else:
                self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, False, team))
                return 0
        else:
            if self.game.game_info.journey[self.game.game_info.current_state].rejects == 4:
                self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, True, team))
                return 1
            if len(self.suspects) < 2:
                self.game.logger.log("I, player {}, vote with super to team {}.".format(self.id, team))
                return super(BasicAgent, self).vote_team(team)
            elif any([x in team for x in self.suspects[0].intersection(*self.suspects[1:])]):
                self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, False, team))
                return 0
            else:
                self.game.logger.log("I, player {}, vote {} to team {}.".format(self.id, True, team))
                return 1
                
    def vote_mission(self, mission):
        if self.role in AvalonGameMaster.GOOD:
            return 1
        else:
            return 0

    # event showing result of current mission vote
    def mission_vote_result(self, mission, team, result):
        self.suspects.append(set(team))

    def guess_merlin(self):
        candidates = set(list(range(len(self.game.players)))) - set([self.id])
        candidates = candidates - set(self.buddies)

        self.game.logger.log(candidates)
        return random.sample(list(candidates), 1)[0]

    def end_game(self, have_won, win_condition, roles):
        super(BasicAgent, self).end_game(have_won, win_condition, roles)        
        self.buddies = []
        self.bad = []
        self.suspects = []
