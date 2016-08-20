# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
import re
import os
import sys
from slackclient import SlackClient


SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')

try:
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
    EXTERNAL_BOTS_ID = os.environ['EXTERNAL_BOTS_ID']
except KeyError as error:
    sys.stderr.write('Please set the environment variable {0}'.format(error))
    sys.exit(1)


class FixMentionRTMBot(object):
    RE_MENTION = re.compile(r'(@\w+)')

    RE_MESSAGE_BY = re.compile(r'by (\w+ \w+)')

    def __init__(self):
        self.slack_client = SlackClient(SLACK_API_TOKEN)
        self.external_bots = []
        for bot_id in EXTERNAL_BOTS_ID.split(','):
            self.external_bots.append(bot_id.strip())
        self.users = {}

    def connect(self):
        resp = self.slack_client.rtm_connect()
        for user in self.slack_client.server.users:
            self.users[user.name] = user

    def start(self):
        self.connect()
        while True:
            for event in self.slack_client.rtm_read():
                self.process(event)
                self.catch_all(event)

    def process(self, data):
        if "type" in data:
            function_name = "process_" + data["type"]
            process_func = getattr(self, function_name, None)
            if process_func and callable(process_func):
                process_func(data)

    def process_message(self, data):
        if data.get('subtype', None) == 'bot_message' and 'bot_id' in data:
            bot_id = data['bot_id']
            channel = data['channel']
            if bot_id in self.external_bots:
                for message in data['attachments']:
                    self.process_bot_message(channel, message)

    def process_bot_message(self, channel_id, message):
        text = message.get('text')
        if not text:
            return

        pretext = message.get('pretext')
        message_by = None
        if pretext:
            message_by = self.RE_MESSAGE_BY.search(pretext)
            message_by = message_by.groups(1)[0] if message_by else None

        mentions = self.RE_MENTION.findall(text)
        user_mentions = []

        for mention in mentions:
            user_mention = self.find_user_mention(mention)
            if user_mention:
                user_mentions.append('<@{}> ^'.format(user_mention))

        text = " ".join(user_mentions)
        username = message_by if message_by else 'FixMention'
        self.slack_client.api_call("chat.postMessage", channel=channel_id, text=text,
                                   username=username)

    def find_user_mention(self, mention):
        for name in self.users:
            if name in mention or mention in name:
                return self.users[name].id
        return None

        # ts, user_id, text = data['ts'], data['user'], data['text']
        # user = self.users[user_id]
        # if user.name == 'FixMention':
        #     print "Message From FixMention"

    def catch_all(self, data):
        pass


if __name__ == '__main__':
    bot = FixMentionRTMBot()
    bot.start()
