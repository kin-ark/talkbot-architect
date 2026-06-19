from decode_pdf import decode_text


def test_decode_known_string():
    # +31 glyph shift: "8J[ 5BMLCPU" decodes to "Wiz Talkbot"
    assert decode_text("8J[ 5BMLCPU") == "Wiz Talkbot"


def test_decode_preserves_spaces_and_newlines():
    assert decode_text("1SPEVDU\n") == "Product\n"
