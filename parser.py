import sys
import json
from pathlib import Path

import dateparser
from bs4 import BeautifulSoup as soup
from logzero import logger

IGNORE = set(
    [
        "Home Address",
        "Security",
        "Gameplay History",
        "Beta Opt In Details",
        "Wallet Information",
        "User Data By Region",
        "GDPR_Data_Glossary",
        "Hero Stats",
        "Progression",
        "Versus A.I. Matches",
        "Hotkeys",
        "Account",
        "Currencies",
        "Loot Chests",
        "Toon",
        "Player",
        "Player Unlock",
        "Player Lootbox",
        "Player Lootbox Unlock",
        "Player Map Stat",
        "Player All Hero Stat",
        "Hero",
        "Player Unlock",
        "Hero Stat",
        "Achievement",
        "Player Celebration",
        "Player Endorsements",
        "Player",
        "Favorites",
    ]
)

INCLUDE_KEY_VALUE_TABLES = set(
    [
        "Battle.net Account",
        "Account Link",
        "Hearthstone",
        "Heroes",
        "Overwatch",
        "Game History",
    ]
)
INCLUDE_GENERAL_TABLES = set(
    [
        "Orders",
        "Key Claims",
        "Received Gifts",
        "Overwatch Chat",
        "Activity History",
        "Licenses_Hearthstone",
        "Licenses_Others",
        "Licenses_Overwatch",
        "Licenses_WoW",
        "Hearthstone Esports Votes",
    ]
)


def check_whitelist_backlist(key: str, whitelist, blacklist):
    k = str(key).lower()
    if any([x in k for x in whitelist]):
        if not all([x in k for x in blacklist]):
            return True
    else:
        return False


def key_is_date_like(key: str) -> bool:
    return check_whitelist_backlist(key, ["time", "date"], ["birth"])


# convert to text and strip an element
def ss(x):
    if hasattr(x, "text"):
        return x.text.strip()
    else:
        return x.strip()


def not_intish(ss):
    try:
        int(ss)
        return False
    except:
        return True


def is_date_parseable(val):
    s = ss(val)
    return dateparser.parse(s) is not None


# like 'battle.net account data'
def parse_key_value_table(table, header_tag):
    """
    Parses a key-value like talbe, looks for dates
    as values as column names that look like they describe dates
    """
    for tr in table.find_all("tr"):
        if len(tr.find_all("th")) > 0:
            continue
        kv = tr.find_all("td")
        try:
            assert len(kv) == 2
        except:
            logger.warning(f"{kv} doesnt have 2 entires, expected key-value pairs")
        key, value = kv
        # if key looks like a description to a date, or value looks like date
        if key_is_date_like(ss(key)) or (
            not_intish(ss(value)) and is_date_parseable(value)
        ):
            # value is date like
            yield (ss(value), (header_tag, ss(key)))


def parse_regular_table(table, header_tag):
    """
    Parses a HTML table by using the names of the headers which look like dates
    as dates, and the rest as the data
    """
    headers = [ss(k) for k in table.find_all("th")]
    assert len(headers) > 0
    try:
        date_index = list(map(key_is_date_like, headers)).index(True)
    except ValueError:
        logger.warning("Couldnt find date-like key in {}".format(headers))
        return
    for tr in table.find_all("tr"):
        if len(tr.find_all("td")) == 0 and len(tr.find_all("th")) > 0:
            continue
        td_text = [ss(k) for k in tr.find_all("td")]
        en_td_text = list(enumerate(td_text))

        # split into date and non date columns
        date_info = en_td_text[date_index][1]
        non_date_info = [v for k, v in en_td_text if k != date_index]
        yield (date_info, (header_tag, "|".join(non_date_info)))


def rename_headers(header):
    if header == "Game History":
        return "HotS Game History"
    else:
        return header


def ends_with_hearthstone_region(hh):
    return any([hh.endswith(f"({reg})") for reg in ["EU", "NA", "US"]])


def ignore_friends_lists(hh):
    return any(
        [x in hh for x in ("Club List", "Block List", "Friends", "Case History")]
    )


def parse_if_known(header, table):
    """
    Use a couple different table matching patterns to parse event data from tables
    """
    hh = ss(header).strip()
    # ignore friend/block lists, anything explicitly IGNORED and EU/NA HearthStone info
    if hh in IGNORE or ignore_friends_lists(hh) or ends_with_hearthstone_region(hh):
        logger.debug(f"Ignoring table {hh}...")
        return []
    # key-value tables
    if header in INCLUDE_KEY_VALUE_TABLES:
        for k, v in parse_key_value_table(table, rename_headers(header)):
            yield (k, v)
            logger.debug(f"{k} {v}")
    elif header in INCLUDE_GENERAL_TABLES:
        for k, v in parse_regular_table(table, rename_headers(header)):
            yield (k, v)
            logger.debug(f"{k} {v}")
    else:
        logger.exception(f"Ignoring {hh}...")


def validate_date_keys(items):
    for k, v in items:
        date_val = dateparser.parse(k)
        if date_val is None:
            logger.warning(f"Couldn't parse {k} into a date...")
        else:
            yield (date_val.timestamp(), v)


def parse_html_file(path: Path):
    with path.open("r") as pf:
        contents = pf.read()

    all_events = []
    bsoup = soup(contents, "html.parser")

    for table in bsoup.find_all("table"):
        prev_sib = table.find_previous_sibling()
        # only match tables right after a heading
        if not (str(prev_sib.name) in [f"h{i}" for i in range(1, 7)]):
            logger.warning(f"Ignoring {str(prev_sib)[:100]}...")
            continue
        new_events = list(parse_if_known(prev_sib.text.strip(), table))
        all_events.extend(new_events)

    validated_events = list(validate_date_keys(all_events))
    return validated_events


if __name__ == "__main__":
    with open(sys.argv[2], "w") as battle_f:
        json.dump(parse_html_file(Path(sys.argv[1])), battle_f)
