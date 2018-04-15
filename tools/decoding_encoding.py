import unicodedata


class DecoderEncoder:

    @staticmethod
    def decode_text(text, decoding="utf-8", errors="ignore"):
        return unicodedata.normalize('NFKD', text.decode(decoding, errors))

    @staticmethod
    def encode_into_bytes(text, encoding="utf-8", errors="ignore"):
        return text.encode(encoding, errors)
