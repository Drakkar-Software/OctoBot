import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OctoBot-Installer-Updater')
    parser.add_argument('-u', '--update', help='update OctoBot with the latest version available',
                        action='store_true')

    args = parser.parse_args()
    if args.update:
        pass
    else:
        # dowload https://github.com/cjhutto/vaderSentiment/tree/master/vaderSentiment
        # create log and config
        pass
