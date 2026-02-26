'''
This file builds the dataset for the shiny app to use, cleaning the data, and outputs a csv file when run
'''
import pandas as pd

# reading in data from google doc
filepath = "https://docs.google.com/spreadsheets/d/1TrqDiT_gXJaCpTRu19GR5e4TYDC8VISOoiM3TTh9JGk/export?format=csv&gid=0"
df = pd.read_csv(filepath)

# banlist
banned_cards = ['swift reconfiguration', 'ghost quarter', 'volatile fault', "thassa's oracle", 
                'meddling mage', 'curse of silence', 'disruptor flute', 'dark depths', 
                'jace, wielder of mysteries', 'chancellor of the annex', 'scion of draco', 'electrodominance']

# reading in card data from scryfall
# json link does not update automatically, I'm not sure how to do that :-)
scryfall_cards_original = pd.read_json('https://data.scryfall.io/default-cards/default-cards-20260224100756.json')
# cleaning scryfall card data
columns = ['oracle_id', 'name', 'scryfall_uri', 'colors', 'color_identity', 'type_line','image_uris', 'released_at', 'card_faces']
scryfall_cards = scryfall_cards_original[columns].sort_values('released_at', ascending = True)
# setting card names to lowercase to match my convention
scryfall_cards['name'] = [str.lower(x) for x in scryfall_cards['name']]
# removing the backside name from double-sided cards
scryfall_cards.loc[scryfall_cards.name.str.contains('//'), 'name'] = [x.split(' //')[0] for x in scryfall_cards.loc[scryfall_cards.name.str.contains('//'), 'name']]

# building card-event dataframe
card_event = []
for i in range(len(df)):
    deck = set()
    deck_legal = True
    for j in range(5):
        card = df.iloc[i]['Card ' + str(j+1)].lower()
        if card not in deck:
            deck.add(card)
            if card in banned_cards:
                deck_legal = False
    for card in deck:
        # adding color identity stat by pulling from scryfall database
        # try/except here to catch cards with typos in name
        try:
            color_identity = scryfall_cards[scryfall_cards['name'] == card].reset_index().iloc[0].color_identity

            if len(color_identity) == 0:
                color_identity = 'colorless'
            elif len(color_identity) > 1:
                color_identity = 'gold'
            else:
                color_identity = color_identity[0]
        except:
            print(card)
            color_identity = 'colorless'

        week = df.iloc[i]['Week']
        deck_score = round(df.iloc[i]['Adjusted Score'], 2)

        card_event.append([card,color_identity,week,deck_score,deck_legal])

# each row is an instance of a single card in a deck (decks with duplicates only contain one entry)
card_event_df = pd.DataFrame(card_event, columns=['Card','Color Identity','Week','Deck Score','Deck Legal'])

# adding column for how many decks a given card is played in
value_counts = card_event_df['Card'].value_counts() 
card_event_df['N Decks'] = card_event_df['Card'].apply(lambda x: value_counts[x])

card_event_df.to_csv('./card_event_df.csv')