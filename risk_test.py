import risk


def print_state(testboard):
    print testboard.board_map['countries'] 

def test_counts(testboard):
    assert len(testboard.board_map['countries']) == 42

def test_borders(testboard):
    for country in testboard.board_map['countries']:
        for bordering_country in testboard.board_map['countries'][country][
                                                      'bordering_countries']:
            assert country in testboard.board_map['countries'][bordering_country][
                                                   'bordering_countries']


testboard = risk.Board()
test_counts(testboard)
test_borders(testboard)
