# blizzard_gdpr_parser

Parses date-related information from my blizzard GDPR export.

For whatever reason, its an HTML file...

This searches for `tables` which contains things that look like dates/times, and parse those out of the file.

Was a very manual process, lots of small changes till I got the output I wanted, so not sure if it'd work for other people. Leaving it here as reference.

Used as part of my [`HPI`](https://github.com/purarue/HPI)

## Run

```
python3 parser.py ./path/to/html_dump.html ./data.json
```

The output is just lots of random events which have timestamps, like when I bought packs in HS, first games I played in random games, chat messages and Activity/IP info.
