import sys
from flask import Flask, request
from risk.models import *
import json
import random
import math
import itertools

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
    board['cards_left'] = game['cards_left']
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
             ((game['countries'][bordering_country]['owner'] != my_name) and
             (game['countries'][bordering_country]['owner'] != 'none')))

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
                set_strategic_value(board, country_name, me))

        board['countries'][country_name]['threat_value'] = (
            set_threat_value(board, country_name, me))
        
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
        
    
def set_threat_value(board, country_name, me):
    enemy_troops_per_turn=sum(
        [board['other_players'][enemy]['troops_per_turn'] for enemy in 
         board['countries'][country_name]['unique_bordering_enemies'] 
                                                    if enemy != 'none'])
    enemy_card_worth = 0
    sets_exchanged = (44-board['cards_left']-sum([board['other_players'][player]
                    ['cards'] for player in board['other_players']]))/3
    if(sets_exchanged < 6):
        next_set_value = (sets_exchanged-1 + 2) * 2
    else:
        next_set_value = (sets_exchanged - 3) * 5
    for enemy in board['countries'][country_name]['unique_bordering_enemies']:
        if board['other_players'][enemy]['cards']!='none':
            if board['other_players'][enemy]['cards']==3:
                enemy_card_worth+=next_set_value/2
            elif board['other_players'][enemy]['cards']==4:
                enemy_card_worth+=next_set_value*3/4
            elif board['other_players'][enemy]['cards']==5:
                enemy_card_worth+=next_set_value
    bordering_enemies = len(
        board['countries'][country_name]['bordering_enemies']) 
    bordering_enemy_troops = board['countries'][country_name][
        'bordering_enemy_troops'] 
    unique_bordering_enemies = len(
        board['countries'][country_name]['unique_bordering_enemies']) 
    
    return (bordering_enemies*2 + bordering_enemy_troops - 
            unique_bordering_enemies + enemy_troops_per_turn/2 + 
            enemy_card_worth)
    # + strategic value for enemies +

def closest_enemy(board, source, me):
    queue = [] 
    visited = []
    queue.append(source + "-0")
    while len(queue) > 0: 
        item = queue.pop(0)
        country = item.split("-")[0]
        level = int(item.split("-")[1])
        if board['countries'][country]['owner'] != me.name:
            return level; 
        else:
            level += 1
            for c2 in board['countries'][country]['bordering_countries']: 
                if c2 not in visited:
                    queue.append(c2 + "-" + str(level))
                    visited.append(c2)
    return 42 

def set_strategic_value(board, country_name, me):
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
    our_countries_in_continent = len(list((c for c in board['continents'][board['countries'][country_name]['continent']][
            'countries'] if board['countries'][c]['owner'] == me.name)))
    return (
        10/num_bordering_countries + 10/access_points + bonus/2 + 
        (num_bordering_countries - num_bordering_enemies) + 
        ((our_countries_in_continent) * 5 / 
        countries_in_continent))

def compare_modified_values(board, list_to_compare):
    compared_value = 0
    for c in list_to_compare:
        if board['countries'][c]['troops'] == 'none':
            board['countries'][c]['troops'] = 0
        modified_value = (board['countries'][c]['strategic_value'] - 
                          board['countries'][c]['troops'])
        if modified_value >= compared_value:
            chosen_country = c
            compared_value = modified_value
    return chosen_country

def choose_country(board):
    unoccupied = [c for c in board['countries'] if (
                            board['countries'][c]['owner'] == 'none')]
    chosen_country = compare_modified_values(board, unoccupied)
    print "choose: %s" % chosen_country
    return {"action":"choose_country", "data":chosen_country}

def deploy_initial_troops(board, me):
    chosen_country = compare_modified_values(board, me.my_countries)
    deploy_orders = {chosen_country: 1}
    print "initial deploy orders: %s" % deploy_orders
    return {"action":"deploy_troops", "data":deploy_orders}

def deploy_troops(board, me):
    deploy_orders = {}
    troops_to_deploy = me.troops_to_deploy
    while troops_to_deploy > 0:
        compared_value = 0
        for c in me.my_countries:
            threat = board['countries'][c]['threat_value']
            strategic_value = board['countries'][c]['strategic_value']
            troops = board['countries'][c]['troops']
            if troops >= threat + strategic_value:
                continue
            if not board['countries'][c]['bordering_enemies']:
                continue
            modified_value = threat + strategic_value - troops
            if modified_value >= compared_value:
                chosen_country = c
                compared_value = modified_value
        if compared_value == 0:
            chosen_country = max([c for c in me.my_countries], key=(
                lambda x: board['countries'][c]['threat_value']))
        if chosen_country not in deploy_orders:
            deploy_orders[chosen_country] = 0
        deploy_orders[chosen_country] += 1
        board['countries'][chosen_country]['troops'] += 1
        troops_to_deploy -= 1
    print "deploy orders: %s" % deploy_orders
    return {"action":"deploy_troops", "data":deploy_orders}

def attack_determination(board, me):
    possible_attacks = [(c1,c2)
                        for c1 in me.my_countries
                        for c2 in board['countries'][c1]['bordering_countries']
                        if board['countries'][c1]['troops'] > 1 
                        and c2 not in me.my_countries]
    good_attacks=[]
    for attack_combo in possible_attacks:
        if board['countries'][attack_combo[0]]['troops']>=2*board['countries'][attack_combo[1]]['troops']:
            good_attacks.append(attack_combo)
    if not possible_attacks or not good_attacks:
        response = {"action":"end_attack_phase"}
        print "ended attack phase"
    else:
        response = attack(board, good_attacks)
    return response

def attack(board, possible_attacks):    
        max_value = 0
        attacking_country, defending_country = (possible_attacks[0])
        for attack in possible_attacks:
            if board['countries'][attack[1]]['strategic_value']>max_value:
                max_value=board['countries'][attack[1]]['strategic_value']
                defending_country = attack[1]
                attacking_country = attack[0]
            elif attack[1]==defending_country:
                if (board['countries'][attack[0]]['troops'] > 
                     board['countries'][attacking_country]['troops']):
                    attacking_country=attack[0]
        attacking_troops = min(3, board['countries'][attacking_country][
            'troops'] - 1)
        moving_troops = 0
        troops_available = max(
                0, board['countries'][attacking_country]['troops'] - 4)
        threat = board['countries'][defending_country]['threat_value']
        strategic_value = board['countries'][defending_country][
                                                    'strategic_value']
        while troops_available > 0:
            compared_value = 0
            if moving_troops >= threat + strategic_value:
                break
            modified_value = threat + strategic_value - moving_troops
            if modified_value >= compared_value:
                moving_troops+=1
                compared_value = modified_value
                troops_available -= 1
        data = {'attacking_country':attacking_country,
                'defending_country':defending_country,
                'attacking_troops':attacking_troops,
                'moving_troops':moving_troops}
        print "attacking %s from %s with %s troops" % (
           defending_country, attacking_country, attacking_troops)
        return {'action':'attack', 'data':data}

def reinforce(board, me):
    threat_value = 0
    troops = 1 
    to_reinforce = None
    reinforce_from = None
    for c1 in me.my_countries:
        if not board['countries'][c1]['bordering_enemies']:
            if board['countries'][c1]['troops'] > troops:
                reinforce_from = c1
                troops = board['countries'][c1]['troops']
    if reinforce_from is not None:
        for c2 in board['countries'][reinforce_from]['bordering_countries']:
            if board['countries'][c2]['threat_value'] == 0:
                modified_value = closest_enemy(board, c2, me) 
            else: 
                modified_value = board['countries'][c2]['threat_value']
            if modified_value > threat_value:
                to_reinforce = c2
                threat_value = board['countries'][c2]['threat_value']       
    else:
        threat_value = 0
        troops = 1 
        for c1 in me.my_countries:
            if board['countries'][c1]['threat_value'] > threat_value:
                to_reinforce = c1
                threat_value = board['countries'][c1]['threat_value']
        if to_reinforce is not None:
            for c2 in board['countries'][to_reinforce]['bordering_countries']:
                if c2 in me.my_countries:
                    if board['countries'][c2]['troops'] > troops:
                        reinforce_from = c2
                        troops = board['countries'][c2]['troops']
        
    if reinforce_from is not None: 
        moving_troops = board['countries'][reinforce_from]['troops']-1
        print "reinforced %s from %s with %s troops -- Threat_value =  %s" % (
            to_reinforce, reinforce_from, moving_troops, threat_value)
        response = {'action':'reinforce', 'data':{
        'origin_country': reinforce_from, 
        'destination_country':to_reinforce,
        'moving_troops':moving_troops}}
        print response

    else:
        print "ended turn"
        response = {"action":"end_turn"}

    return response

def is_card_set(card_one, card_two, card_three):
    wild_cards = [card for card in [
        card_one, card_two, card_three] if (card['value'] == 'wild')]
    return ((len(wild_cards) >= 1) or 
        (card_one['value'] == card_two['value'] == card_three['value']) or 
        (card_one['value'] != card_two['value'] != card_three['value']))
    
def spend_cards(board, me):
    combos = itertools.combinations(me.cards,3)
    potential_sets = [c for c in combos if is_card_set(c[0], c[1],c[2])]
    if "pass" in me.available_actions:
        for player in board['other_players']:
            if board['other_players'][player]['cards']>=3:
                response = {'action':'pass'}
    else:
        trade_in = random.choice(potential_sets)
        if len(potential_sets)>1:
            owned_cards = [c for c in me.cards if c not in me.my_countries]
            for set in potential_sets:
                owned = 0
                for c in set:
                    for o in owned_cards:
                        if c==o:
                            owned+=1
                if owned==1:
                    trade_in=set
                    break
        trade_in = [c['country_name'] for c in trade_in]
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
