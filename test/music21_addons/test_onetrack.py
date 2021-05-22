from music21_addons.onetrack import to_text, parse_onetrack, Located


def test_location():
    loc = Located(1, 5, 2, 8)
    assert loc.location_intersects(1, 6, 1, 7)
    assert loc.location_intersects(1, 2, 1, 6)
    assert loc.location_intersects(2, 6, 3, 7)
    assert loc.location_intersects(1, 2, 3, 7)
    assert not loc.location_intersects(1, 1, 1, 3)
    assert not loc.location_intersects(3, 1, 3, 3)


def test_note():
    notes = ['A', 'Aq', 'A:100', 'Aq:100']
    for n in notes:
        rs = to_text(parse_onetrack(n))
        print(rs)
        assert rs == n


def test_chord():
    chords = ['[a]', '[a b]', '[a b]q', '[a b]:100', '[a b]q:100']
    for c in chords:
        rs = to_text(parse_onetrack(c))
        print(rs)
        assert rs == c


def test_setvol():
    sv = 'v:56'
    rs = to_text(parse_onetrack(sv))
    print(rs)
    assert rs == sv


def test_list():
    s = "C-3 Aq A:100 Aq:100 [a b4]q [c d]q:100 v:60"
    rs = to_text(parse_onetrack(s))
    print(rs)
    assert rs == s
