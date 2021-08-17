import logging
from enum import Enum

import requests

from back_office.config import SLACK_ENRICHMENT_NOTIFICATION_URL


class SlackChannel(Enum):
    ENRICHMENT_NOTIFICATIONS = 'ENRICHMENT_NOTIFICATIONS'

    def slack_url(self) -> str:
        if self == self.ENRICHMENT_NOTIFICATIONS:
            return SLACK_ENRICHMENT_NOTIFICATION_URL
        raise NotImplementedError(f'Missing slack channel url {self}.')


def send_slack_notification(message: str, channel: SlackChannel) -> None:
    url = channel.slack_url()
    answer = requests.post(url, json={'text': message})
    if not (200 <= answer.status_code < 300):
        logging.error('Error with status code', answer.status_code)
        logging.error(answer.content.decode())
