from wizmodifier import codec


def test_encode_uses_compact_separators():
    assert codec.encode({"a": 1, "b": [2, 3]}) == '{"a":1,"b":[2,3]}'


def test_encode_preserves_non_ascii():
    assert codec.encode({"x": "Halo dunia ☎"}) == '{"x":"Halo dunia ☎"}'


def test_decode_roundtrip():
    raw = '{"speechId":8309}'
    assert codec.encode(codec.decode(raw)) == raw


def test_decode_literal_null():
    assert codec.decode("null") is None
