from datetime import datetime, timedelta
import pytz
from hltv_async_api.Utils.datetools import localize_datetime_to_timezone


class News:
    def __init__(self, TIMEZONE):
        self.TIMEZONE = TIMEZONE

    def get_last_news(self, r, max_reg_news=2, only_today=True, only_featured=False):
        today = datetime.now(tz=pytz.timezone(self.TIMEZONE))
        article_days = {
            1: today.strftime('%d-%m'),
            2: (today - datetime.timedelta(days=1)).strftime('%d-%m'),
            3: 'old'
        }

        news = []
        reg_news_num = 0
        for i, news_date_div in enumerate(r.find_all('div', {'class', 'standard-box standard-list'}), start=1):
            date_ = article_days[i]
            f_news = []
            reg_news = []
            for featured_news_div in news_date_div.find_all('a',
                                                            {'class': 'newsline article featured breaking-featured'}):
                featured_id = featured_news_div['href'].split('/')[2]
                featured_title = featured_news_div.find('div', {'class': 'featured-newstext'}).text
                featured_description = featured_news_div.find('div', {'class': 'featured-small-newstext'}).text
                f_news.append({
                    'f_id': featured_id,
                    'f_title': featured_title,
                    'f_desc': featured_description,
                })

            if not only_featured and reg_news_num < max_reg_news:
                for news_div in news_date_div.find_all('a',
                                                       {'class': 'newsline article'}):
                    if reg_news_num > max_reg_news:
                        break
                    if news_div['class'] != 'newsline article featured breaking-featured':
                        news_id = news_div['href'].split('/')[2]
                        news_title = news_div.find('div', {'class': 'newstext'}).text
                        news_posted = news_div.find('div', {'class': 'newsrecent'}).text

                        reg_news.append({
                            'id': news_id,
                            'title': news_title,
                            'posted': news_posted,
                        })
                        reg_news_num += 1

            news.append({
                'date': date_,
                'f_news': f_news,
                'news': reg_news,
            })

            if only_today:
                break

        return news