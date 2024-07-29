from datetime import datetime

import pytz


def localize_datetime_to_timezone(TIMEZONE, date_: datetime = None, date_str: str = None) -> datetime:
        if not TIMEZONE:
            return date_
        if date_str:
            date_ = datetime.strptime(date_str, '%d-%m-%Y')
        if date_.tzinfo:
            return date_.astimezone(pytz.timezone(TIMEZONE))

        return pytz.timezone('Europe/Copenhagen').localize(date_).astimezone(pytz.timezone(TIMEZONE))


def normalize_date(parts) -> str:
        month_abbreviations = {
            'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4',
            'May': '5', 'Jun': '6', 'Jul': '7', 'Aug': '8',
            'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        month = month_abbreviations[parts[0]]
        day = parts[1][:-2]
        return day + '-' + month


def normalize_date_(date_) -> str:
        words = date_.split()
        num = ''.join(c for c in words[-2] if c.isdigit())
        date_string = words[-3] + num + words[-1]
        date = datetime.strptime(date_string, "%B%d%Y")
        return date.strftime("%d-%m-%Y")