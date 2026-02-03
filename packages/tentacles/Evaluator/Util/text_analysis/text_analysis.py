#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import octobot_commons.constants as commons_constants
try:
    import vaderSentiment.vaderSentiment as vaderSentiment
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock vaderSentiment imports
        class VaderSentimentImportMock:
            class SentimentIntensityAnalyzer:
                def __init__(self, *args):
                    raise ImportError("vaderSentiment not installed")
    vaderSentiment = VaderSentimentImportMock()


class TextAnalysis:
    IMAGE_ENDINGS = ["png", "jpg", "jpeg", "gif", "jfif", "tiff", "bmp", "ppm", "pgm", "pbm", "pnm", "webp", "hdr",
                     "heif",
                     "bat", "bpg", "svg", "cgm"]

    def __init__(self):
        super().__init__()
        self.analyzer = vaderSentiment.SentimentIntensityAnalyzer()
        # self.test()

    def analyse(self,  text):
        # The compound score is computed by summing the valence scores of each word in the lexicon, adjusted according
        # to the rules, and then normalized to be between -1 (most extreme negative) and +1 (most extreme positive).
        # https://github.com/cjhutto/vaderSentiment
        return self.analyzer.polarity_scores(text)["compound"]

    # return a list of high influential value websites
    @staticmethod
    def get_high_value_websites():
        return [
            "https://www.youtube.com"
        ]

    @staticmethod
    def is_analysable_url(url):
        url_ending = str(url).split(".")[-1]
        return url_ending.lower() not in TextAnalysis.IMAGE_ENDINGS

    # official account tweets that can be used for testing purposes
    def test(self):
        texts = [
            "Have you read about VeChain and INPI ASIA's integration to bring nanotechnology for digital identity to "
            "the VeChainThor blockchain? NDCodes resist high temperature, last over 100 years, are incredibly durable "
            "and invisible to the naked eye",
            "A scientific hypothesis about how cats, infected with toxoplasmosis, are making humans buy Bitcoin was "
            "presented at last night's BAHFest at MIT.",
            "Net Neutrality Ends! Substratum Update 4.23.18",
            "One more test from @SubstratumNet for today. :)",
            "Goldman Sachs hires crypto trader as head of digital assets markets",
            "Big news coming! Scheduled to be 27th/28th April... Have a guess...",
            "This week's Theta Surge on http://SLIVER.tv  isn't just for virtual items... five PlayStation 4s will "
            "be given out to viewers that use Theta Tokens to reward the featured #Fortnite streamer! Tune in this "
            "Friday at 1pm PST to win!",
            "The European Parliament has voted for regulations to prevent the use of cryptocurrencies in money "
            "laundering and terrorism financing. As long as they have good intention i don' t care.. but how "
            "much can we trust them??!?!"
            "By partnering with INPI ASIA, the VeChainThor Platform incorporates nanotechnology with digital "
            "identification to provide solutions to some of the worlds most complex IoT problems.",
            "Thanks to the China Academy of Information and Communication Technology, IPRdaily and Nashwork for "
            "organizing the event.",
            "Delivered a two hour open course last week in Beijing. You can tell the awareness of blockchain is "
            "drastically increasing by the questions asked by the audience. But people need hand holding and "
            "business friendly features to adopt the tech.",
            "Introducing the first Oracle Enabler tool of the VeChainThor Platform: Multi-Party Payment Protocol "
            "(MPP).",
            "An open letter from Sunny Lu (CEO) on VeChainThor Platform.",
            "VeChain has finished the production of digital intellectual property services with partner iTaotaoke. "
            "This solution provides a competitive advantage for an industry in need of trust-free reporting and "
            "content protections.#GoVeChain",
            "Special thanks to @GaboritMickael to have invited @vechainofficial to present our solution and make "
            "a little demo to @AccentureFrance",
            "VeChain will pitch their solutions potentially landing a co-development product with LVMH.  In "
            "attendance will be CEOs Bill McDermott (SAP), Chuck Robbins (CISCO), Ginni Rometty (IBM), and Stephane "
            "Richard (Orange) as speakers -",
            "As the only blockchain company selected, VeChain is among 30 of 800+ hand-picked startups to compete "
            "for the second edition of the LVMH Innovation Award. As a result, VeChain has been invited to join the "
            "Luxury Lab LVMH at Viva Technology in Paris from May 24-26, 2018.",
            "VeChain to further its partnership with RFID leader Xiamen Innov and newly announced top enterprise "
            "solution provider CoreLink by deploying a VeChainThor enterprise level decentralized application - "
            "AssetLink.",
            "Today, a group of senior leaders from TCL's Eagle Talent program visited the VeChain SH office. "
            "@VeChain_GU demonstrated our advanced enterprise solutions and it's relation to TCL's market. As a "
            "result, we're exploring new developments within TCL related to blockchain technology.",
            "We are glad to be recognized as Top 10 blockchain technology solution providers in 2018. outprovides a "
            "platform for CIOs and decision makers to share their experiences, wisdom and advice. Read the full "
            "version article via",
            "Talked about TOTO at the blockchain seminar in R University of Science and Technology business school "
            "last Saturday. It covered 3000 MBA students across business schools in China."
        ]
        for text in texts:
            print(str(self.analyse(text)) + " => "+str(text.encode("utf-8", "ignore")))
