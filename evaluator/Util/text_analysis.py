from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from evaluator.Util.abstract_util import AbstractUtil


class TextAnalysis(AbstractUtil):
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyse(self,  text):
        return self.analyzer.polarity_scores(text)
