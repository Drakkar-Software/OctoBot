import unicodedata


class DecoderEncoder:

    @staticmethod
    def decode_text(text):
        return unicodedata.normalize('NFKD', text)

    @staticmethod
    def encode_into_bytes(text, encoding="utf-8", errors="ignore"):
        return str(text.encode(encoding, errors))
