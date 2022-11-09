import threading
from enum import Enum
import random
import AvalonNN
import timeit

class Logger():
    def __init__(self, active):
        self.verbose = active

    def log(self, *args):
        if self.verbose:
            print(*args)


class PlayerType(Enum):
    MERLIN=0
    ASSASSIN=1
    MINION_MORDRED=2
    MINION_ARTHUR=3
    PERCIVAL=4
    MORGANA=5
    MORDRED=6
    OBERON=7

GOOD = [PlayerType.MERLIN, PlayerType.MINION_ARTHUR, PlayerType.PERCIVAL]
BAD = [PlayerType.ASSASSIN, PlayerType.MINION_MORDRED]

END_GAME_REASONS = ["3 Failed missions.", "All missions compleated correctly.", "5 Rejected teams for a mission.", "Assassin guessed Merlin correctly."]

class Mission():
    def __init__(self, n_players, n_fails):
        self.team_size = n_players
        self.fails_to_fail = n_fails
        self.team_rejections = 0
        self.votes = None
        self.rejects = 0
        self.id = 0
        self.assigned_team = None

    def result(self):
        return self.votes > self.team_size - self.fails_to_fail and self.rejects < 5

    def __str__(self):
        aux = "Mission, with id {} has:".format(self.id)
        aux += "\n\tTeam size: {}\n\tFails to fail: {}\n\tSuccess votes: {}\n".format(self.team_size, self.fails_to_fail, self.votes)
        return aux

def get_mission_list(n_players):
    if n_players == 5:
        return [Mission(2,1), Mission(3,1), Mission(2, 1), Mission(3, 1), Mission(3,1)]
    elif n_players == 6:
        return [Mission(2,1), Mission(3,1), Mission(4,1), Mission(3,2), Mission(4,1)]
    elif n_players == 7:
        return [Mission(2,1), Mission(3,1), Mission(3,1), Mission(4,2), Mission(4,1)]
    elif n_players == 8:
        return [Mission(3,1), Mission(4,1), Mission(4,1), Mission(5,2), Mission(5,1)]
    elif n_players == 9:
        return [Mission(3,1), Mission(4,1), Mission(4,1), Mission(5,2), Mission(5,1)]
    elif n_players == 10:
        return [Mission(3,1), Mission(4,1), Mission(4,1), Mission(5,2), Mission(5,1)]

    raise ValueError("Invalid number of players {} expected 5-10.".format(n_players))


class GameInfo():
    def __init__(self, n_players):
        self.log = []
        self.journey = get_mission_list(n_players)
        for i in range(len(self.journey)):
            self.journey[i].id = i
        self.current_state = 0

    def is_over(self):
        return sum([0 if mission.result() else 1 for mission in self.journey[0:self.current_state]]) >= 3 or self.current_state >= len(self.journey) or self.journey[self.current_state].rejects > 4

    def get_game_over_reason(self):
        if sum([0 if mission.result() else 1 for mission in self.journey[0:self.current_state]]) >= 3:
            return False, 0
        if self.current_state >= len(self.journey):
            return True, 1
        if self.journey[self.current_state].rejects > 4:
            return False, 2

        return None

    def __str__(self):
        return 'Currently in mission {}.\n'.format(self.current_state) + "\n".join([str(m) for m in self.journey[0:self.current_state]])

class GameSettings():
    def __init__(self):
        self.num_players = 0
        self.use_morgana = False
        self.use_mordred = False
        self.use_oberon = False
        self.use_percival = False

    def get_roles(self):
        output = [PlayerType.MERLIN, PlayerType.MINION_MORDRED, PlayerType.MINION_ARTHUR]

        return set(output)

class GameMaster():
    def __init__(self, game_settings=None):
        #super(GameMaster, self).__init__()
        self.players = []
        self.game_state = None
        self.game_info = None
        self.lock = threading.Lock()
        self.king_index = 0
        self.votes = None
        self.num_votes = 0
        self._good_wins = False
        self._string = ""
        self.logger = Logger(False)
        self.settings = GameSettings()
        if game_settings is not None:
            self.settings = game_settings

    def give_opinion(self, player, opinion):
        self.lock.acquire()
        self.logger.log("player {} has opinion.".format(player.id))
        self.lock.release()

    def propose_team(self, player, team):
        self.lock.acquire()
        self.logger.log("player {} has proposition.".format(player.id))
        self.lock.release()

    def register_player(self, player):
        self.players.append( [player, None, False] )
        self.settings.num_players += 1
        if not issubclass(type(player), AvalonNN.AvalonNNAgent):
            player.start()

    def role_selection(self):
        roles = []
        roles.append(PlayerType.MERLIN)
        roles.append(PlayerType.ASSASSIN)

        nArthur = len(self.players) - 2
        nMorgana = 0

        if len(self.players) == 5 or len(self.players) == 6:
            nArthur -= 1
            nMorgana = 1
        elif len(self.players) >= 7 and len(self.players) <= 9:
            nArthur -= 2
            nMorgana = 2
        else:
            nArthur -= 3
            nMorgana = 3

        if self.settings.use_percival:
            roles.append(PlayerType.PERCIVAL)
            nArthur -= 1
        if self.settings.use_morgana:
            roles.append(PlayerType.MORGANA)
            nArthur -= 1
        if self.settings.use_mordred:
            roles.append(PlayerType.MORDRED)
            nMorgana -= 1
        if self.settings.use_oberon:
            roles.append(PlayerType.OBERON)
            nMorgana -= 1        

        roles = roles + [PlayerType.MINION_ARTHUR] * nArthur
        roles = roles + [PlayerType.MINION_MORDRED] * nMorgana

        random.shuffle(roles)

        if nArthur < 0 or nMorgana < 0 or len(roles) != self.settings.num_players:
            raise ValueError("Roles cannot match players.\n {} to assign to {} players.".format(roles, self.settings.num_players))

        self.logger.log("Master says roles are: {}.".format(roles))


        for i in range(len(self.players)):
            self.players[i][0].identify_self((i,roles[i]))
            self.players[i][1] = roles[i]
            if roles[i] == PlayerType.MERLIN:
                for j in range(len(self.players)):
                    if roles[j] == PlayerType.MINION_MORDRED or roles[j] == PlayerType.ASSASSIN: 
                        self.players[i][0].role_shown(j, PlayerType.MINION_MORDRED)
            elif roles[i] == PlayerType.MINION_MORDRED or roles[i] == PlayerType.ASSASSIN:
                for j in range(len(self.players)):
                    if roles[j] == PlayerType.MINION_MORDRED or roles[j] == PlayerType.ASSASSIN: 
                        self.players[i][0].role_shown(j, PlayerType.MINION_MORDRED)

    def ask_make_team(self, player):
        return player.propose_team(self.game_info.journey[self.game_info.current_state].team_size)

    def broadcast_opinions(self):
        for p in self.players:
            temp = p[0].give_my_opinion()
            print("Master dice player {} has opinions: {}.".format(p[0].id, temp))
            for p2 in self.players:
                if p2[0].id == p[0].id:
                    continue
                else:
                    p2[0].player_given_opinion(p[0], temp)

    def run(self, t=0):
        # main loop
        self.game_state = None
        self.game_info = None
        self.king_index = 0
        self.votes = None
        self.num_votes = 0
        self._good_wins = False
        self._string = ""
        self.game_info = GameInfo(self.settings.num_players)

        for p in self.players:
            if issubclass(type(p[0]), AvalonNN.AvalonNNAgent):
                p[0].initialize()
                if not p[0].is_alive():
                    p[0].start()
        
        print("Load time is {} s.".format(timeit.default_timer() - t))

        self.role_selection()

        self.king_index = random.randint(0, self.settings.num_players - 1)
        self.logger.log(self.king_index)
        for p in self.players:
            p[0].new_king(self.king_index)
        

        while not self.game_info.is_over():
            # king = None
            self.team = None
            self.votes = [0]*len(self.players)

            # opinions
            self.broadcast_opinions()

            self.team = self.ask_make_team(self.players[self.king_index][0])

            self.logger.log("Master: player {} has proposed team {}.".format(self.king_index, self.team))

            for p in self.players:
                self.votes[p[0].id] = p[0].vote_team(self.team)

            self.logger.log("Master sees {}/{} approved votes.".format(sum(self.votes), len(self.players)))

            for p in self.players:
                p[0].team_vote_result(self.team, list(self.votes))

            if sum(self.votes) > len(self.players)/2:
                self.game_info.journey[self.game_info.current_state].assigned_team = list(self.team)
                self.logger.log("Master says: Team size is {} expected {}.".format(self.game_info.journey[self.game_info.current_state].team_size, len(self.team)))
                m_votes = [0]*self.game_info.journey[self.game_info.current_state].team_size

                for i,j in enumerate(self.team):
                    # add mission info
                    m_votes[i] = self.players[j][0].vote_mission(self.game_info.journey[self.game_info.current_state])

                for p in self.players:
                    p[0].mission_vote_result(self.game_info.journey[self.game_info.current_state], self.team, sum(m_votes) > len(self.team) - self.game_info.journey[self.game_info.current_state].fails_to_fail)

                self.logger.log(m_votes)

                self.game_info.journey[self.game_info.current_state].votes = sum(m_votes)
                
                self.logger.log("Master says mission {} is {result}.".format(self.game_info.journey[self.game_info.current_state], result='Success' if self.game_info.journey[self.game_info.current_state].result() else 'Fail'))

                self.game_info.current_state += 1
            else:
                # Add error counter to mission
                self.king_index = (self.king_index + 1) % len(self.players)

                for p in self.players:
                    p[0].team_vote_result(self.team, False)
                    p[0].new_king(self.king_index)
                self.game_info.journey[self.game_info.current_state].rejects += 1
                
            # win condition


        self._good_wins, self._string = self.game_info.get_game_over_reason()

        if self._good_wins:
            for p in self.players:
                if p[1] == PlayerType.ASSASSIN:
                    res = p[0].guess_merlin()
                    self.logger.log("Guess is {}, result {}.".format(res, self.players[res][1]))
                    if self.players[res][1] == PlayerType.MERLIN:
                        self._good_wins = False
                        self._string = 3
                    else:
                        self.logger.log("Assassin guessed Merlin incorrectly.")

        for p in self.players:
            if self._good_wins:
                if p[1] in GOOD:
                    p[0].end_game(True, self._string, self.players)
                else:
                    p[0].end_game(False, self._string, self.players)
            else:
                if p[1] in BAD:
                    p[0].end_game(True, self._string, self.players)
                else:
                    p[0].end_game(False, self._string, self.players)
        
        self.logger.log("Master says {} won because: {}.".format("GOOD" if self._good_wins else "EVIL", END_GAME_REASONS[self._string]))
        self.logger.log("\n\n{}.".format(self.game_info))
        #for p in self.players:
            #p[0].join()

    def render(self):
        self.logger.log(str(self.game_info))  # para gym.environment

    def join(self):
        val = self.game_info
        #threading.Thread.join(self)
        return (self._good_wins, val, self._string)
