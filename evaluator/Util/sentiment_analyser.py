from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class SentimentAnalyser:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyse(self,  text):
        return self.analyzer.polarity_scores(text)

