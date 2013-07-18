from flask import Flask, request
import json
import random

class Board:

    def __init__(self):
        self.board_map = eval(open('board_map.rsk').readline())

    def unpack_json(self, game_json):
        # JSON: {'game':{'countries':{[countries]
        my_data = game_json['you']
        game = game_json['game']

        self.my_name = my_data['name']
        self.my_new_cards = my_data['earned_cards_this_turn']
        self.is_eliminated = my_data['is_eliminated']
        self.troops_to_deploy = my_data['troops_to_deploy']
        self.available_actions = my_data['available_actions']
        self.countries = my_data['countries']
        self.cards = my_data['cards']
        self.players = game['players']
        #TODO - finish function

    def choose_action(self): #TODO
        pass
        #return action


app = Flask(__name__)

@app.route('/status')
def status():
    print "Received status check."

@app.route('/not_turn')
def not_turn():
    print "Received board."

@app.route('/turn', methods=['POST'])
def turn():
    game_json = json.loads(request.form['risk'])
    board.upack_json(game_json)
    response = board.choose_action()
    return json.dumps(response)


if __name__ == '__main__':
    board = Board()
    test_json = {}#TODO
