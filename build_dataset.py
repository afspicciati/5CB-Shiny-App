"""
This file builds the dataset for the shiny app to use, cleaning the data, and outputs a csv file when run
"""

import pandas as pd
import json

# reading in data from google sheet
filepath = "https://docs.google.com/spreadsheets/d/1TrqDiT_gXJaCpTRu19GR5e4TYDC8VISOoiM3TTh9JGk/export?format=csv&gid=0"
df = pd.read_csv(filepath)
df["Adjusted Score"] = round(df["Adjusted Score"], 2)
# write original data
df.to_csv("./app/data/raw_5cb_stats.csv", index=False)

# banlist
banned_cards = [
    "swift reconfiguration",
    "ghost quarter",
    "volatile fault",
    "thassa's oracle",
    "meddling mage",
    "curse of silence",
    "disruptor flute",
    "dark depths",
    "jace, wielder of mysteries",
    "chancellor of the annex",
    "scion of draco",
    "electrodominance",
    "mental misstep",
]

# reading in card data from scryfall
# json link does not update automatically, I'm not sure how to do that :-)
# updated 3/11/26 for tmnt
scryfall_cards_original = pd.read_json(
    "https://data.scryfall.io/default-cards/default-cards-20260429090820.json"
)
# cleaning scryfall card data
columns = [
    "oracle_id",
    "name",
    "scryfall_uri",
    "colors",
    "color_identity",
    "type_line",
    "image_uris",
    "released_at",
    "card_faces",
]
scryfall_cards = scryfall_cards_original[columns].sort_values(
    "released_at", ascending=True
)
# setting card names to lowercase to match my convention
scryfall_cards["name_lower"] = [str.lower(x) for x in scryfall_cards["name"]]
# removing the backside name from double-sided cards
scryfall_cards.loc[scryfall_cards.name_lower.str.contains("//"), "name_lower"] = [
    x.split(" //")[0]
    for x in scryfall_cards.loc[
        scryfall_cards.name_lower.str.contains("//"), "name_lower"
    ]
]
scryfall_cards.loc[scryfall_cards.name.str.contains("//"), "name"] = [
    x.split(" //")[0]
    for x in scryfall_cards.loc[scryfall_cards.name.str.contains("//"), "name"]
]

# building card-event dataframe
card_event = []
for i in range(len(df)):
    deck = set()
    deck_legal = True
    for j in range(5):
        card = df.iloc[i]["Card " + str(j + 1)].lower()
        if card not in deck:
            deck.add(card)
            if card in banned_cards:
                deck_legal = False
    for card in deck:
        # adding color identity stat by pulling from scryfall database
        # try/except here to catch cards with typos in name
        try:
            color_identity = (
                scryfall_cards[scryfall_cards["name_lower"] == card]
                .reset_index()
                .iloc[0]
                .color_identity
            )

            if len(color_identity) == 0:
                color_identity = "colorless"
            elif len(color_identity) > 1:
                color_identity = "gold"
            else:
                color_identity = color_identity[0]

            # additionally adding the capitalized name from scryfall
            card_name_caps = (
                scryfall_cards[scryfall_cards["name_lower"] == card]
                .reset_index()
                .iloc[0]["name"]
            )
        except:
            print(card)
            color_identity = "colorless"
            card_name_caps = card

        week = df.iloc[i]["Week"]
        deck_score = df.iloc[i]["Adjusted Score"]

        card_event.append(
            [card_name_caps, card, color_identity, week, deck_score, deck_legal]
        )

# each row is an instance of a single card in a deck (decks with duplicates only contain one entry)
card_event_df = pd.DataFrame(
    card_event,
    columns=[
        "Card",
        "Card Lower",
        "Color Identity",
        "Week",
        "Deck Score",
        "Deck Legal",
    ],
)

# adding column for how many decks a given card is played in
value_counts = card_event_df["Card"].value_counts()
card_event_df["N Decks"] = card_event_df["Card"].apply(lambda x: value_counts[x])
card_event_df.to_csv("./app/data/card_event_df.csv", index=False)

# building table-stats dataframe
decklist = []
for i in range(len(df)):
    deck_individual = []
    for j in range(5):
        card = df.iloc[i][f"Card {j+1}"].lower()
        # for adding card names to decklist
        deck_individual.append(
            scryfall_cards[scryfall_cards["name_lower"] == card]
            .reset_index()
            .iloc[0]["name"]
        )
        # for adding links
        card_uri = (
            scryfall_cards[scryfall_cards["name_lower"] == card]
            .reset_index()
            .iloc[0]["scryfall_uri"]
        )

        # for adding images
        card_data = scryfall_cards[(scryfall_cards["name_lower"] == card)]
        if len(card_data[card_data["image_uris"].notnull()]) > 0:
            card_image_uri = (
                card_data[card_data["image_uris"].notnull()]
                .reset_index()
                .iloc[0]["image_uris"]["normal"]
            )
        else:
            card_image_uri = card_data.reset_index()["card_faces"].iloc[0][0][
                "image_uris"
            ]["normal"]
        df.loc[i, f"Card {j+1}"] = card_uri + "SPACE" + card_image_uri
    decklist.append(deck_individual)
df["Deck"] = decklist
df["Score"] = df["Adjusted Score"]
df.drop("Adjusted Score", axis=1, inplace=True)

# adding a trophy emoji to the score of trophy decks!
trophy = []
# for i in range(len(card_event_df)):
for i in range(len(df)):
    event = df.iloc[i]
    # print(event["Deck Score"])
    # print(max(card_event_df[df["Week"] == event["Week"]]["Score"]))
    trophy.append(event["Score"] != df[df["Week"] == event["Week"]]["Score"].max())

df["Score"] = [str(score) for score in df["Score"]]
df["Score"] = df["Score"].where(trophy, df["Score"] + " 👑")

df.to_csv("./app/data/table_stats.csv", index=False)


# buildling dictionary of scryfall img links
card_uris = dict()
for card in card_event_df["Card Lower"].unique():
    card_data = scryfall_cards[(scryfall_cards["name_lower"] == card)]
    if len(card_data[card_data["image_uris"].notnull()]) > 0:
        card_uris[card] = (
            card_data[card_data["image_uris"].notnull()]
            .reset_index()
            .iloc[0]["image_uris"]["normal"]
        )
    # special case for double-sided cards. Only grabbing first printing front face, hence the iloc[0][0]
    else:
        card_uris[card] = card_data.reset_index()["card_faces"].iloc[0][0][
            "image_uris"
        ]["normal"]

with open("./app/data/card_uris.json", "w") as file:
    json.dump(card_uris, file, indent=4)

# reading weeks dictionary to file (so github may be cloned)
week_links = {
    1: "https://tappedout.net/mtg-decks/5-card-blind-week-1-the-mirror-crackd-1/",
    2: "https://tappedout.net/mtg-decks/5-card-blind-week-2-mysterious-mysteries/",
    3: "https://tappedout.net/mtg-decks/5-card-blind-week-3-flying-spaghetti-monsters-1/",
    4: "https://tappedout.net/mtg-decks/5-card-blind-week-4-return-of-the-hatebears/",
    5: "https://tappedout.net/mtg-decks/5-card-blind-week-5-oh-the-wurmanity/",
    6: "https://tappedout.net/mtg-decks/5-card-blind-week-6-combos-galore/",
    7: "https://tappedout.net/mtg-decks/5-card-blind-week-7-scorched-earth/",
    8: "https://tappedout.net/mtg-decks/5-card-blind-week-8-misstep-up-to-the-plate-2/",
    9: "https://tappedout.net/mtg-decks/5-card-blind-week-9-pili-your-palas/",
    10: "https://tappedout.net/mtg-decks/5-card-blind-week-10-oof-oko/",
    11: "https://tappedout.net/mtg-decks/5-card-blind-week-11-why-i-otter/",
    12: "https://tappedout.net/mtg-decks/5-card-blind-week-12-big-guys-and-discard/",
    13: "https://tappedout.net/mtg-decks/5-card-blind-week-13-be-vigilant/",
    14: "https://tappedout.net/mtg-decks/5-card-blind-week-14-mirrodin-hosts-5cb/",
    15: "https://tappedout.net/mtg-decks/5-card-blind-week-15-return-of-the-eldrazi/",
    16: "https://tappedout.net/mtg-decks/5-card-blind-week-16-wake-up-and-smell-the-lotus/",
    17: "https://tappedout.net/mtg-decks/5-card-blind-week-17-a-crash-of-footfalls/",
    18: "https://tappedout.net/mtg-decks/5-card-blind-week-18-shadowy-missteps/",
    19: "https://tappedout.net/mtg-decks/5-card-blind-week-19-land-of-1000-counters/",
    20: "https://tappedout.net/mtg-decks/5-card-blind-week-20-hivemind-pairs/",
    21: "https://tappedout.net/mtg-decks/5-card-blind-week-21-105-card-blind/",
    22: "https://tappedout.net/mtg-decks/5-card-blind-week-22-keeping-the-peace/",
    23: "https://tappedout.net/mtg-decks/5-card-blind-week-23-3-of-a-kind/",
    24: "https://tappedout.net/mtg-decks/5-card-blind-week-24-dont-let-your-guard-down/",
    25: "https://tappedout.net/mtg-decks/5-card-blind-week-25-123-draw/",
    26: "https://tappedout.net/mtg-decks/5-card-blind-week-26-creature-combats-back-1/",
    27: "https://tappedout.net/mtg-decks/5-card-blind-week-27-start-your-engines/",
    28: "https://tappedout.net/mtg-decks/5-card-blind-week-28-we-hate-lands/?cb=1776269622",
    29: "https://tappedout.net/mtg-decks/5-card-blind-week-29-advanced-ritual-magic/?cb=1776910093",
    30: "https://tappedout.net/mtg-decks/5-card-blind-week-30-neck-and-neck/?cb=1777480322",
    31: "https://tappedout.net/mtg-decks/5-card-blind-week-31-copy-their-stylus/?cb=1778084725",
    32: "https://tappedout.net/mtg-decks/5-card-blind-week-32-mono-white-delver/?cb=1778688913",
}

with open("./app/data/week_links.json", "w") as file:
    json.dump(week_links, file, indent=4)
