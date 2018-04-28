from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tools.decoding_encoding import DecoderEncoder

from evaluator.Util.abstract_util import AbstractUtil
from newspaper import Article
from config.cst import IMAGE_ENDINGS


class TextAnalysis(AbstractUtil):
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        # self.test()

    def analyse(self,  text):
        # The compound score is computed by summing the valence scores of each word in the lexicon, adjusted according
        # to the rules, and then normalized to be between -1 (most extreme negative) and +1 (most extreme positive).
        # https://github.com/cjhutto/vaderSentiment
        return self.analyzer.polarity_scores(text)["compound"]

    # returns the article object and the analysis result
    def analyse_web_page_article(self, url):
        article = Article(url)
        article.download()
        article.parse()
        return article, self.analyse(article.text)

    # return a list of high influential value websites
    @staticmethod
    def get_high_value_websites():
        return [
            "https://www.youtube.com"
                ]

    @staticmethod
    def is_analysable_url(url):
        url_ending = str(url).split(".")[-1]
        return url_ending.lower() not in IMAGE_ENDINGS

    # official account tweets that can be used for testing purposes
    def test(self):
        texts = [
            "So excited at what I am working on for the future.  I don’t get to talk about what I am actively doing on a daily basis because it’s far ahead of our messaging but I am beyond excited about it! #substratum $sub",
            "Have you read about VeChain and INPI ASIA's integration to bring nanotechnology for digital identity to the VeChainThor blockchain? NDCodes resist high temperature, last over 100 years, are incredibly durable and invisible to the naked eye",
            "Crypto market update: BTC holds near $9K, ETH rising over $640, BCH grows 85% on the week",
            "Extremely excited & proud to announce that #Substratum Node is NOW Open Source! https://github.com/SubstratumNetwork/SubstratumNode …#NetNeutrality $SUB #cryptocurrency #bitcoin #blockchain #technology #SubSavesTheInternet",
            "A scientific hypothesis about how cats, infected with toxoplasmosis, are making humans buy Bitcoin was presented at last night's BAHFest at MIT.",
            "Net Neutrality Ends! Substratum Update 4.23.18",
            "One more test from @SubstratumNet for today. :)",
            "Goldman Sachs hires crypto trader as head of digital assets markets",
            "Big news coming! Scheduled to be 27th/28th April... Have a guess...😎",
            "A great step to safer #exchanges: @WandXDapp Joins REMME’s 2018 Pilot Program for testing functionality of certificate-based signup and login for end users. https://medium.com/remme/wandx-joins-remmes-2018-pilot-program-588379aaea4d … #nomorepasswords #blockchain #crypto $REM"
            "omeone transferred $99 million in litecoin — and it only cost them $0.40 in fees. My bank charges me a hell of a lot more to transfer a hell of a lot less. Can we hurry up with this crypto/blockchain revolution I'm tired of paying fees out of my ass to a bunch of fat cats",
            "This week's Theta Surge on http://SLIVER.tv  isn't just for virtual items... five PlayStation 4s will be given out to viewers that use Theta Tokens to reward the featured #Fortnite streamer! Tune in this Friday at 1pm PST to win!",
            "The European Parliament has voted for regulations to prevent the use of cryptocurrencies in money laundering and terrorism financing. As long as they have good intention i don' t care.. but how much can we trust them??!?!"
            "By partnering with INPI ASIA, the VeChainThor Platform incorporates nanotechnology with digital identification to provide solutions to some of the worlds most complex IoT problems.",
            "Thanks to the China Academy of Information and Communication Technology, IPRdaily and Nashwork for organizing the event.",
            "Delivered a two hour open course last week in Beijing. You can tell the awareness of blockchain is drastically increasing by the questions asked by the audience. But people need hand holding and business friendly features to adopt the tech.",
            "Introducing the first Oracle Enabler tool of the VeChainThor Platform: Multi-Party Payment Protocol (MPP).",
            "An open letter from Sunny Lu (CEO) on VeChainThor Platform.",
            "VeChain has finished the production of digital intellectual property services with partner iTaotaoke. This solution provides a competitive advantage for an industry in need of trust-free reporting and content protections.#GoVeChain",
            "Special thanks to @GaboritMickael to have invited @vechainofficial to present our solution and make a little demo to @AccentureFrance",
            "VeChain’s COO, @kfeng027, is invited to ‘Crypto Media Collection Vo.1’ held at DeNA’s campus by Coinjinja in Tokyo, one of the largest cryptocurrency information platforms. Kevin’s speech begins at 16:35 UTC+9, livestreamed via https://ssl.twitcasting.tv/coinjinja ",
            "VeChain will pitch their solutions potentially landing a co-development product with LVMH.  In attendance will be CEOs Bill McDermott (SAP), Chuck Robbins (CISCO), Ginni Rometty (IBM), and Stephane Richard (Orange) as speakers -",
            "As the only blockchain company selected, VeChain is among 30 of 800+ hand-picked startups to compete for the second edition of the LVMH Innovation Award. As a result, VeChain has been invited to join the Luxury Lab LVMH at Viva Technology in Paris from May 24-26, 2018.",
            "VeChain to further its partnership with RFID leader Xiamen Innov and newly announced top enterprise solution provider CoreLink by deploying a VeChainThor enterprise level decentralized application - AssetLink.",
            "Today, a group of senior leaders from TCL's Eagle Talent program visited the VeChain SH office. @VeChain_GU demonstrated our advanced enterprise solutions and it's relation to TCL's market. As a result, we're exploring new developments within TCL related to blockchain technology.",
            "VeChain announces a partnership with eGrid, a leading publicly listed ERP, SCM and CRM solution provider to synergistically provide comprehensive blockchain technology backing for a significant portion of China’s automobile industry.",
            "We are glad to be recognized as Top 10 blockchain technology solution providers in 2018. outprovides a platform for CIOs and decision makers to share their experiences, wisdom and advice. Read the full version article via",
            "Talked about TOTO at the blockchain seminar in R University of Science and Technology business school last Saturday. It covered 3000 MBA students across business schools in China."
        ]
        for text in texts:
            print(str(self.analyse(text)) + " => "+str(DecoderEncoder.encode_into_bytes(text)))
