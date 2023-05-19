import re
from typing import Iterable, Iterator

import requests
from loguru import logger
from telebot.types import CallbackQuery

from keyboards.reply import top_news_menu
from loader import bot
from states.news_state import NewsState
from utils.misc import redis_cache as cache
from utils.news import utils as news_utils
from utils.top_news import get_top_news


@bot.callback_query_handler(func=lambda call: call.data == 'top_news', state=NewsState.got_news)
def bot_top_news(call: CallbackQuery):
    """
    Gets top news

    :param call: callback query
    :type call: CallbackQuery
    :rtype: None
    """
    logger.debug('bot_top_news() called')

    chat_id = call.message.chat.id
    user_id = call.from_user.id

    search_query, datetime_from, datetime_to, _, _ = \
        news_utils.retrieve_user_input(chat_id, user_id)

    most_important_news = get_cached_most_important_news(
        search_query, datetime_from, datetime_to)

    key_top_news = cache.get_key(
        'top_news', search_query, datetime_from, datetime_to)
    cached_get_top_news = cache.cached(
        key_top_news, datetime_to)(get_top_news)
    top_news = cached_get_top_news(most_important_news)

    if top_news:
        text = 'Here are the top news. You can choose one to list emotions'\
            ' or to read the full article.'
        bot.send_message(
            chat_id, text, reply_markup=top_news_menu.main(top_news))
    else:
        bot.send_message(chat_id, 'Unable to get top news.')


@bot.callback_query_handler(func=lambda call: call.data.startswith('news_'), state=NewsState.got_news)
def bot_news_item(call: CallbackQuery):
    """
    Gets news item

    :param call: callback query
    :type call: CallbackQuery
    :rtype: None
    """
    logger.debug('bot_news_item() called')

    chat_id = call.message.chat.id
    user_id = call.from_user.id
    news_id = re.search(r'^news_(\d+)$', call.data).group(1).strip()

    search_query, datetime_from, datetime_to, _, _ = \
        news_utils.retrieve_user_input(chat_id, user_id)

    try:
        most_important_news = get_cached_most_important_news(
            search_query, datetime_from, datetime_to)

        news_item = most_important_news[news_id]['news']
        title = news_item['title']
        url = news_item['url']
        bot.send_message(
            chat_id, title, reply_markup=top_news_menu.submenu(news_id, url))
    except (requests.RequestException, ValueError,
            requests.exceptions.JSONDecodeError) as exception:
        logger.exception(exception)
        bot.send_message(chat_id, 'Some error occurred.')


def get_cached_most_important_news(search_query: str, date_from: str,
                                   date_to: str) -> dict[dict]:
    """
    Gets most important news from cache

    :param search_query: search query
    :type search_query: str
    :param datetime_from: datetime from
    :type datetime_from: str
    :param datetime_to: datetime to
    :type datetime_to: str
    :raises ValueError: most important news not found
    :return: most important news
    :rtype: dict[dict]
    """
    key = cache.get_key('most_important_news', search_query,
                        date_from, date_to)
    most_important_news = cache.get(key)
    if not most_important_news:
        raise ValueError('Most important news not found.')

    return most_important_news
