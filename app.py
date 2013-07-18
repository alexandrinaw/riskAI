import sys
from flask import Flask, request
from risk.models import *
import json
import random

pass_prob = float(sys.argv[2])

app = Flask(__name__)

def unpack_json(game_json):
    # JSON: {'game':{'countries':{[countries]
    board_map = eval(open('board_map.rsk').readline())
    my_data = game_json['you']
    game = game_json['game']

    my_name = my_data['name']
    me = Player(my_name)
    me.new_cards = my_data['earned_cards_this_turn']
    me.is_eliminated = my_data['is_eliminated']
    me.troops_to_deploy = my_data['troops_to_deploy']
    me.available_actions = my_data['available_actions']
    me.my_countries = my_data['countries']
    me.cards = my_data['cards']
    players = game['players']
    for country_name in game['countries']:
        board_map.countries[country_name].owner = players[game['countries'][country_name]['owner']]
        board_map.countries[country_name].troops = game['countries'][country_name]['troops']
    return me, players, board_map

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
        unoccupied = [c for c in board.countries.values() if not c.owner]
        country_choice = random.choice(unoccupied)
        response = {"action":"choose_country", "data":country_choice.name}
        print "choose: %s" % country_choice
        return json.dumps(response)
    elif "deploy_troops" in me.available_actions:
        troops_to_deploy = me.troops_to_deploy
        deploy_orders = {}
        for _ in range(troops_to_deploy):
            c = random.choice(me.countries)
            deploy_orders[c.name] = deploy_orders.setdefault(c.name,0) + 1
        response = {"action":"deploy_troops", "data":deploy_orders}
        print "deploy orders: %s" % deploy_orders
        return json.dumps(response)
    elif "attack" in me.available_actions:
        possible_attacks = [(c1,c2)
                            for c1 in me.countries
                            for c2 in c1.border_countries
                            if c1.troops > 1 
                            and c2 not in me.countries]
        if not possible_attacks or random.random() < pass_prob:
            response = {"action":"end_attack_phase"}
            print "ended attack phase"
        else:
            attacking_country, defending_country = random.choice(possible_attacks)
            attacking_troops = min(3, attacking_country.troops-1)
            moving_troops = random.randint(0,max(0,attacking_country.troops-4))
            data = {'attacking_country':attacking_country.name,
                    'defending_country':defending_country.name,
                    'attacking_troops':attacking_troops,
                    'moving_troops':moving_troops}
            response = {'action':'attack', 'data':data}
            print "attacking %s from %s with %s troops" % (defending_country.name,
                                                           attacking_country.name,
                                                           attacking_troops)
        return json.dumps(response)
    elif "reinforce" in me.available_actions:
        reinforce_countries = [(c1,c2) for c1 in me.countries
                                for c2 in c1.border_countries
                                if c1.troops > 1
                                and c2 in me.countries]
        if not reinforce_countries:
            print "ended turn"
            response = {"action":"end_turn"}
            return json.dumps(response)
        (origin_country,destination_country) = random.choice(reinforce_countries)
        moving_troops = random.randint(1,origin_country.troops-1)
        print "reinforced %s from %s with %s troops" % (origin_country.name, destination_country.name, moving_troops)
        response = {'action':'reinforce', 'data':{'origin_country':origin_country.name,
                                                  'destination_country':destination_country.name,
                                                  'moving_troops':moving_troops}}
        return json.dumps(response)
    elif "spend_cards" in me.available_actions:
        combos = itertools.combinations(me.cards,3)
        potential_sets = [c for c in combos if c[0].is_set_with(c[1],c[2])]
        trade_in = random.choice(potential_sets)
        trade_in = [c.country_name for c in trade_in]
        response = {'action':'spend_cards', 'data':trade_in}
        print "traded in cards %s" % trade_in
        return json.dumps(response)
    print "something broke"
    return ''

if __name__ == '__main__':
    port = int(sys.argv[1])
    app.run(debug=True, host="0.0.0.0", port=port)
