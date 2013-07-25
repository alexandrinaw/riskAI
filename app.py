import sys
from flask import Flask, request
from risk.models import *
import json
import random
import math

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
    board['turn'] = game['turn']
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
        for enemy_country in board['countries'][country_name][
                'bordering_countries']:
            if board['countries'][enemy_country]['owner'] != my_name:
                board['countries'][country_name]['bordering_enemy_troops'] += (
                     game['countries'][enemy_country]['troops'])

        board['countries'][country_name]['unique_bordering_enemies'] = list(set(
                        board['countries'][country_name]['bordering_enemies']))

        for unique_enemy in (
             board['countries'][country_name]['unique_bordering_enemies']):
            if unique_enemy != "none":
                board['other_players'][unique_enemy]['troops_per_turn'] = (
                    enemy_troops_per_turn(board, unique_enemy))
                board['other_players'][unique_enemy]['cards'] = (
                                game['players'][unique_enemy]['cards'])

        board['countries'][country_name]['strategic_value'] = (
                set_strategic_value(board, country_name))

        board['countries'][country_name]['threat_value'] = (
            set_threat_value(board, country_name))

    return me, players, board

def enemy_troops_per_turn(board, enemy):
    countries_owned = 0
    continent_bonus = 0
    for continent in board['continents']:
        continent_owned=True
        for country in board['continents'][continent]['countries']:
            if (board['countries'][country]['owner'] == enemy):
                countries_owned+=1
            else:
                continent_owned=False
        if continent_owned:
            continent_bonus+=1
    return max(math.ceil(countries_owned / 3), 3) + continent_bonus
        
    
def set_threat_value(board, country_name):
    return (len(board['countries'][country_name]['bordering_enemies']) * 2 +
     board['countries'][country_name]['bordering_enemy_troops'] -
     len(board['countries'][country_name]['unique_bordering_enemies'])) 
    # + strategic value for enemies +
    # troops enemies get each turn +
    # cards enemies have

def set_strategic_value(board, country_name):
    num_bordering_countries = (
        len(board['countries'][country_name]['bordering_countries']))
    num_bordering_enemies = (
        len(board['countries'][country_name]['bordering_enemies']))
    access_points = (
        board['continents'][board['countries'][country_name]['continent']][
            'access points'])
    bonus = (board['continents'][board['countries'][country_name]['continent']][
        'bonus'])
    countries_in_continent = (
        len(board['continents'][board['countries'][country_name]['continent']][
            'countries']))
    return (
        10/num_bordering_countries + 10/access_points + bonus/2 + 
        (num_bordering_countries - num_bordering_enemies) + 
        ((num_bordering_countries - num_bordering_enemies) * 5 / 
        countries_in_continent))

def choose_country(board):
    unoccupied = [c for c in board['countries'] if (
                            board['countries'][c]['owner'] == 'none')]
    country_choice = random.choice(unoccupied)
    print "choose: %s" % country_choice
    return {"action":"choose_country", "data":country_choice}

def deploy_initial_troops(board, me):
    compared_value = 0
    for c in me.my_countries:
        if board['countries'][c]['strategic_value'] >= compared_value:
            chosen_country = c
            compared_value = board['countries'][c]['strategic_value']
    deploy_orders = {chosen_country: 1}
    print "initial deploy orders: %s" % deploy_orders
    return {"action":"deploy_troops", "data":deploy_orders}

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
                        for c1 in me.my_countries
                        for c2 in board['countries'][c1]['bordering_countries']
                        if board['countries'][c1]['troops'] > 1 
                        and c2 not in me.my_countries]
    if not possible_attacks or random.random() < pass_prob:
        response = {"action":"end_attack_phase"}
        print "ended attack phase"
    else:
        response = attack(board, possible_attacks)
    return response

def attack(board, possible_attacks):    
        attacking_country, defending_country = (
                                    random.choice(possible_attacks))
        attacking_troops = min(3, board['countries'][attacking_country][
            'troops'] - 1)
        moving_troops = random.randint(0,max(0, board['countries'][
            attacking_country]['troops'] - 4))
        data = {'attacking_country':attacking_country,
                'defending_country':defending_country,
                'attacking_troops':attacking_troops,
                'moving_troops':moving_troops}
        print "attacking %s from %s with %s troops" % (
           defending_country, attacking_country, attacking_troops)
        return {'action':'attack', 'data':data}

def reinforce(board, me):
    for c1 in me.countries:
        if c1[threat_value] > to_reinforce[threat_value]:
            to_reinforce = c1
    for c2 in to_reinforce.border_countries:
        if c2.troops > reinforce_from:
            reinforce_from = c2
    reinforce_countries = (to_reinforce, reinforce_from)
    
    if not reinforce_countries:
        print "ended turn"
        response = {"action":"end_turn"}
    else:
        (origin_country,destination_country) = reinforce_countries ()
        moving_troops = origin_country.troops-1

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
        if board['turn'] == 0:
            response = deploy_initial_troops(board, me)
        else:
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
