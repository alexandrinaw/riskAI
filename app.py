import sys
from flask import Flask, request
from risk.models import *
import json
import random

if len(sys.argv) > 2:
    pass_prob = float(sys.argv[2])
else:
    pass_prob = 0.1 # Probability of ending attack phase.

app = Flask(__name__)

def unpack_json(game_json):
    # JSON: {'game':{'countries':{[countries]
    board = eval(open('board_map.rsk').readline())
    my_data = game_json['you']
    game = game_json['game']

    my_name = my_data['name']
    print "You are %r" % my_name
    me = Player(my_name)
    me.new_cards = my_data['earned_cards_this_turn']
    me.is_eliminated = my_data['is_eliminated']
    me.troops_to_deploy = my_data['troops_to_deploy']
    me.available_actions = my_data['available_actions']
    me.my_countries = my_data['countries']
    me.cards = my_data['cards']
    players = game['players']
    for player in game['players']:
        if player != my_name:
            board['other_players'] = game['players']
    for country_name in game['countries']:
        board['countries'][country_name]['owner'] = (
             game['countries'][country_name]['owner'])
        board['countries'][country_name]['troops'] = (
                            game['countries'][country_name]['troops'])
        board['countries'][country_name]['bordering_enemies'] = list(
             game['countries'][bordering_country]['owner'] for 
             bordering_country in (
                board['countries'][country_name]['bordering_countries']) if 
             (game['countries'][bordering_country]['owner'] != my_name))
        board['countries'][country_name]['bordering_enemy_troops'] = 0
        #TODO: Need to check to see if it's really an enemy country
        for enemy_country in board['countries'][country_name][
                                                'bordering_countries']:
            board['countries'][country_name]['bordering_enemy_troops'] += (
                 game['countries'][enemy_country]['troops'])
        board['countries'][country_name]['unique_bordering_enemies'] = list(set(
                        board['countries'][country_name]['bordering_enemies']))
        for unique_enemy in (
             board['countries'][country_name]['unique_bordering_enemies']):
            if unique_enemy != "none":
                board['other_players'][unique_enemy]['troops_per_turn'] = 0
                                                        #needs to be calculated
                board['other_players'][unique_enemy]['cards'] = (
                                game['players'][unique_enemy]['cards'])
            board['countries'][country_name]['strategic_value'] = (
              10/len(board['countries'][country_name]['bordering_countries']) +
              (10/(board['continents'][
                board['countries'][country_name]['continent']][
                 'access points']) +
              ((board['continents'][board['countries'][country_name][
                                                'continent']]['bonus'])/2) +
               (len(board['countries'][country_name]['bordering_countries']) - 
                len(board['countries'][country_name]['bordering_enemies']) +
                (len(board['countries'][country_name]['bordering_countries']) - 
                len(board['countries'][country_name]['bordering_enemies']))*5/ 
                len(board['continents'][board['countries'][country_name][
                                              'continent']]['countries']))))

        board['countries'][country_name]['threat_value'] = (
             len(board['countries'][country_name]['bordering_enemies']) * 2 +
             board['countries'][country_name]['bordering_enemy_troops'] -
             len(board['countries'][country_name]['unique_bordering_enemies'])) 
            # + strategic value for enemies +
            # troops enemies get each turn +
            # cards enemies have
    return me, players, board
    
def choose_country(board):
    unoccupied = [c for c in board['countries'] if (
                            board['countries'][c]['owner'] == 'none')]
    country_choice = random.choice(unoccupied)
    print "choose: %s" % country_choice
    return {"action":"choose_country", "data":country_choice}

def deploy_troops(board, me):
    troops_to_deploy = me.troops_to_deploy
    deploy_orders = {}
    for _ in range(troops_to_deploy):
        c = random.choice(me.my_countries)
        deploy_orders[c] = deploy_orders.setdefault(c,0) + 1
    print "deploy orders: %s" % deploy_orders
    return {"action":"deploy_troops", "data":deploy_orders}

def attack_determination(board, me):
    possible_attacks = [(c1,c2)
                        for c1 in me.countries
                        for c2 in c1.border_countries
                        if c1.troops > 1 
                        and c2 not in me.countries]
    if not possible_attacks or random.random() < pass_prob:
        response = {"action":"end_attack_phase"}
        print "ended attack phase"
    else:
        response = attack(board)
    return response

def attack(board):    
        attacking_country, defending_country = (
                                    random.choice(possible_attacks))
        attacking_troops = min(3, attacking_country.troops-1)
        moving_troops = random.randint(0,max(0,attacking_country.troops-4))
        data = {'attacking_country':attacking_country.name,
                'defending_country':defending_country.name,
                'attacking_troops':attacking_troops,
                'moving_troops':moving_troops}
        response = {'action':'attack', 'data':data}
        print "attacking %s from %s with %s troops" % (
           defending_country.name, attacking_country.name, attacking_troops)
        return response

def reinforce(board, me):
    reinforce_countries = [(c1,c2) for c1 in me.countries
                            for c2 in c1.border_countries
                            if c1.troops > 1
                            and c2 in me.countries]
    if not reinforce_countries:
        print "ended turn"
        response = {"action":"end_turn"}
    else:
        (origin_country,destination_country) = random.choice(
                                                    reinforce_countries)
        moving_troops = random.randint(1,origin_country.troops-1)
        print "reinforced %s from %s with %s troops" % (
                origin_country.name, destination_country.name, moving_troops)
        response = {'action':'reinforce', 'data':{
                     'origin_country':origin_country.name, 
                     'destination_country':destination_country.name, 
                     'moving_troops':moving_troops}}
    return response


def spend_cards(board, me):
    combos = itertools.combinations(me.cards,3)
    potential_sets = [c for c in combos if c[0].is_set_with(c[1],c[2])]
    trade_in = random.choice(potential_sets)
    trade_in = [c.country_name for c in trade_in]
    response = {'action':'spend_cards', 'data':trade_in}
    print "traded in cards %s" % trade_in
    return response

@app.route("/status")
def status():
    print 'got status check'
    return ''

@app.route("/not_turn")
def not_turn():
    print 'got board'
    return ''

@app.route('/turn', methods=['POST'])
def turn():
    r = json.loads(request.form['risk'])
    me, players, board = unpack_json(r)
    print me.available_actions
    if "choose_country" in me.available_actions:
        response = choose_country(board)
    elif "deploy_troops" in me.available_actions:
        response = deploy_troops(board, me)
    elif "attack" in me.available_actions:
        response = attack_determination(board, me)
    elif "reinforce" in me.available_actions:
        response = reinforce(board, me)
    elif "spend_cards" in me.available_actions:
        response = spend_cards(board, me)
    return json.dumps(response)

if __name__ == '__main__':
    port = int(sys.argv[1])
    app.run(debug=True, host="0.0.0.0", port=port)
