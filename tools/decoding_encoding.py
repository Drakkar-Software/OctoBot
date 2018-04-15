import unicodedata


class DecoderEncoder:

    @staticmethod
    def decode_text(text):
        return str(unicodedata.normalize('NFKD', text).encode("utf-8", 'ignore'))
