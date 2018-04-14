from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class SentimentAnalyser:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyse(self, sentences):
        for sentence in sentences:
            vs = self.analyzer.polarity_scores(sentence)
            print("{:-<65} {}".format(sentence, str(vs)))
