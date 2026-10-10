from shiny import ui, render, App, Inputs, reactive
import pandas as pd
import seaborn as sns
import json
from pathlib import Path
from itertools import chain
import matplotlib.pyplot as plt

css_path = Path(__file__).parent / "styles.css"
www_dir = Path(__file__).parent / "www"

# constants
basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
filepath = "https://docs.google.com/spreadsheets/d/1TrqDiT_gXJaCpTRu19GR5e4TYDC8VISOoiM3TTh9JGk/export?format=csv&gid=217295091"
week_links_df = pd.read_csv(filepath)
week_links = dict(zip(week_links_df["Week"], week_links_df["Link"]))

# load data
card_event_df = pd.read_csv("./data/card_event_df.csv", index_col=False)
table_stats = pd.read_csv("./data/table_stats.csv", index_col=False)
# load card images
with open("./data/card_uris.json") as file:
    card_uris = json.load(file)

### working with data
# fixing list read in
table_stats["Deck"] = [eval(x) for x in table_stats["Deck"]]

# weeks count
N_weeks = int(table_stats["Week"].max())
# building selectize lists
# listing individual card appearances
card_value_counts = card_event_df[
    ~card_event_df["Card"].isin(basic_lands)
].Card.value_counts()
cards_counts_list = []
for i in range(len(card_value_counts)):
    cards_counts_list.append([card_value_counts.index[i], card_value_counts.iloc[i]])

# sorting by N decks then by alphabetical
sorted_choices = sorted(cards_counts_list, key=lambda x: (-x[1], x[0]))
deck_selectize = [
    str(card_name) + " (" + str(card_counts) + ")"
    for (card_name, card_counts) in sorted_choices
]
all_decks = "All (" + str(len(table_stats)) + ")"
deck_selectize = [all_decks] + deck_selectize

# listing player appearances
player_counts = table_stats["Player"].value_counts()
player_counts_list = []
for i in range(len(player_counts)):
    player_counts_list.append([player_counts.index[i], player_counts.iloc[i]])

# sorting players by N decks then by alphabetical
sorted_players = sorted(player_counts_list, key=lambda x: (-x[1], x[0]))
player_selectize = [
    str(player_name) + " (" + str(player_counts) + ")"
    for (player_name, player_counts) in sorted_players
]
all_players = "All (" + str(len(player_counts)) + " Players)"
player_selectize = [all_players] + player_selectize


# App function
def app_ui():

    my_ui = ui.page_fillable(
        ui.tags.head(ui.tags.script(src="device-detect.js")),  # Link the JS file
        ui.include_css(css_path),  # Link CSS file
        ui.navset_card_pill(
            ui.nav_panel(
                "Card Search",
                # ui.output_ui("pizzazz_background"),
                # some truly  cursed shit i did to make the inputs arrange correctly
                ui.page_fluid(
                    ui.layout_columns(
                        ui.page_fluid(
                            ui.layout_columns(
                                ui.input_selectize(
                                    "selectize_cards", "Card", deck_selectize
                                ),
                                ui.input_selectize(
                                    "selectize_players", "Player", player_selectize
                                ),
                            )
                        ),
                        ui.page_fluid(ui.output_ui("Checkbox_UI")),
                        fill=False,
                        col_widths=(4, 4),
                        height="50px",
                    ),
                    ui.page_fluid(ui.output_data_frame("deck_table")),
                ),
            ),
            ui.nav_panel(
                "Card Stats",
                ui.page_sidebar(
                    ui.sidebar(
                        ui.card(
                            ui.input_slider("weeks", "Weeks", 1, N_weeks, [0, N_weeks]),
                            ui.input_slider(
                                "N_decks", "Minimum Decks Containing Card", 2, 40, 15
                            ),
                            ui.input_checkbox("banned", "Include Banned Decks", True),
                            ui.input_checkbox("silly", "Include Silly Weeks", True),
                        ),
                        ui.card(ui.markdown("""
        #### Mirrored Winrates:
        Matches played against the same card are included in the dataset, so cards with high play rates will tend towards middle scores.
        """)),
                        bg="#e6e6e6",
                        width="400px",
                    ),
                    ui.page_auto(ui.output_ui("my_plot")),
                ),
            ),
            ui.nav_spacer(),
            ui.nav_control(
                ui.a(
                    "GitHub",
                    href="https://github.com/afspicciati/5CB-Shiny-App",
                    target="_blank",
                ),
            ),
        ),
        ### some failed attempts at favicon
        # ui.panel_title(
        #     window_title="Chancellor",
        #     title=ui.tags.head(
        #         ui.tags.link(
        #             rel="icon",
        #             type="image/x-icon",
        #             href="favicon.ico",
        #         )
        #     ),
        # ),
        # ui.head_content(
        #     ui.tags.link(
        #         rel="icon",
        #         type="image/png",
        #         sizes="32x32",
        #         href="favicon-32x32.png",
        #     )
        # ),
        title="Chancellor",
    )

    return my_ui


# Server function
def server(input, output, session):

    ### TAB 1 (card table)

    # a failed attempt to make the background change when you hit pizzazz button
    # @render.ui
    # @reactive.event(input.pizzazz)
    # def pizzazz_background():
    #     return ui.Theme(preset="darkly")

    @render.ui
    def Checkbox_UI():
        mobile = input.is_mobile()

        if mobile:
            style = "margin-bottom: 0px;"
        else:
            style = "margin-bottom: 48px;"

        return ui.layout_columns(
            ui.page_fluid(
                ui.page_fillable(ui.a(ui.HTML(f"<p style='{style}'>"))),
                ui.input_checkbox("pizzazz", "Pizzazz Decks", False),
            ),
            ui.page_fluid(
                ui.page_fillable(ui.a(ui.HTML(f"<p style='{style}'>"))),
                ui.input_checkbox("card_format", "View Cards as Text?", False),
            ),
            col_widths=(5, 7),
        )

    @reactive.calc
    def create_graphing_table():

        mobile = input.is_mobile()

        # changing deck names to be hyperlinks
        deck_hyperlinks = []
        for i in range(len(table_stats)):
            row = table_stats.iloc[i]
            deck_name = str(row["Deck Name"])
            if deck_name.startswith("https://"):
                href = deck_name
            else:
                href = week_links[row["Week"]]

            if mobile:
                split = deck_name.split(" ")
                for i in range(len(split)):
                    if len(split[i]) > 10:
                        n_split = int(len(split[i]) / 15) + 1
                        idx_split = int(len(split[i]) / n_split)
                        split[i] = " ".join(
                            [
                                split[i][j : j + idx_split]
                                for j in range(0, len(split[i]), idx_split)
                            ]
                        )
                deck_name = " ".join(chain(split))
                deck_name = deck_name[:150]
            else:
                deck_name = deck_name[:200]

            link_ui = ui.a(
                deck_name,
                href=href,
                target="_blank",
            )
            deck_hyperlinks.append(link_ui)

        graphing_table = table_stats.reset_index()
        graphing_table["Deck Name"] = deck_hyperlinks

        # filtering data by card input
        card_choice = input.selectize_cards().split(" (")[0]
        if card_choice != "All":
            # filter table to input
            graphing_table = table_stats[
                [
                    card_choice in table_stats["Deck"].iloc[i]
                    for i in range(len(table_stats))
                ]
            ].reset_index()

        #  filtering data by player input
        player_choice = input.selectize_players().split(" (")[0]
        if player_choice != "All":
            graphing_table = graphing_table[
                graphing_table["Player"] == player_choice
            ].reset_index(drop=True)

        # filtering data by pizzazz
        pizzazz_choice = input.pizzazz()
        if pizzazz_choice:
            graphing_table = graphing_table[graphing_table["Pizzazz"] == 1].reset_index(
                drop=True
            )

        ### placing cards into graphing table
        # this is broken into two operations, for mobile or
        # desktop users. The code is unfortunately long here
        # but it seems more efficient to do it this way.
        card_format_choice = input.card_format()

        if mobile:
            card_style = "width:57px;height:80px;"
        else:
            card_style = "width:165px;height:231px;"

        # as text
        if card_format_choice:
            deck_list = []
            for i in range(len(graphing_table)):
                current_deck = []
                for j in range(5):
                    card_uri = graphing_table[f"Card {j+1}"].iloc[i].split("SPACE")[0]
                    # creating single element for mobile display
                    card = ui.a(
                        graphing_table["Deck"].iloc[i][j],
                        href=card_uri,
                        target="_blank",
                        style="color: black;",
                    )
                    current_deck.append(card)
                current_deck_html = ui.p(
                    current_deck[0],
                    ui.br(),
                    current_deck[1],
                    ui.br(),
                    current_deck[2],
                    ui.br(),
                    current_deck[3],
                    ui.br(),
                    current_deck[4],
                )
                deck_list.append(current_deck_html)
        # as images
        else:
            deck_list = []
            for i in range(len(graphing_table)):
                current_deck = []
                for j in range(5):
                    card_uri = graphing_table[f"Card {j+1}"].iloc[i].split("SPACE")[0]
                    image_uri = graphing_table[f"Card {j+1}"].iloc[i].split("SPACE")[1]
                    card = ui.a(ui.HTML(f"""<a href="{card_uri}">
                                <img src="{image_uri}" alt="{graphing_table['Deck'].iloc[i][j]}" style={card_style}>
                                        </a>"""))
                    current_deck.append(card)
                if mobile:

                    current_deck_html = ui.HTML(
                        f"""
                        <p>{current_deck[0]} {current_deck[1]} {current_deck[2]} <br>
                            &emsp;&emsp;&emsp;&ensp;&nbsp;{current_deck[3]} {current_deck[4]} </p>"""
                    )
                else:
                    current_deck_html = ui.HTML(
                        f"""<p>{current_deck[0]} {current_deck[1]} {current_deck[2]}{current_deck[3]} {current_deck[4]} </p>"""
                    )
                deck_list.append(current_deck_html)

        graphing_table.drop(["index", "Deck", "Pizzazz"], axis=1, inplace=True)

        if mobile:
            deck_col_name = "~~~~~~~~~~~~~~~~~~~Deck~~~~~~~~~~~~~~~~~~~~"
        else:
            deck_col_name = "Deck"

        graphing_table[deck_col_name] = deck_list
        graphing_table = graphing_table[
            [
                "Week",
                "Player",
                "Deck Name",
                deck_col_name,
                "Score",
            ]
        ]

        graphing_table = graphing_table.sort_values("Score", ascending=False)

        return graphing_table, mobile, card_format_choice

    @render.data_frame
    def deck_table():
        graphing_table, mobile, text = create_graphing_table()

        if mobile:
            if text:
                width = 500
            else:
                width = 700
        # non-mobile
        else:
            if text:
                width = 700
            else:
                width = 1500

        if mobile:
            height = "1000px"
        else:
            height = "800px"

        return render.DataGrid(
            graphing_table,
            width=str(width) + "px",
            height=height,
            styles=[
                {"cols": [0], "style": {"width": "1px"}},
                {"location": "body", "cols": [1], "style": {"width": "1px"}},
                {"location": "body", "cols": [2], "style": {"width": "1px"}},
                {
                    "location": "body",
                    "cols": [3],
                    "style": {"width": f"{str(width - 50)}px"},
                },
                {"location": "body", "cols": [4], "style": {"width": "1px"}},
            ],
        )

    ### TAB 2 (card stats)
    @reactive.calc
    def create_graphing_df():
        graphing_df = card_event_df[
            (~card_event_df["Card"].isin(basic_lands))
            & (card_event_df["Week"] >= input.weeks()[0])
            & (card_event_df["Week"] <= input.weeks()[1])
        ]

        if not input.silly():
            silly_weeks = [17 + (4 * (n + 1)) for n in range(100)] + [52.1, 52.3]
            graphing_df = graphing_df[~graphing_df["Week"].isin(silly_weeks)]

        if not input.banned():
            graphing_df = graphing_df[graphing_df["Deck Legal"] == True]

        score_agg = (
            graphing_df.drop(columns=["Card Lower", "Color Identity", "Week"])
            .groupby(by="Card", as_index=False)
            .agg("mean")
            .sort_values("Deck Score", ascending=False)
        )
        score_sort = dict(zip(score_agg["Card"], score_agg["Deck Score"]))
        return graphing_df.sort_values(
            by="Card", key=lambda x: x.map(score_sort), ascending=False
        )

    @reactive.calc
    def filtered_graphing_df():
        graphing_df = create_graphing_df()
        value_counts = graphing_df["Card"].value_counts()
        graphing_df["N Decks"] = graphing_df["Card"].apply(lambda x: value_counts[x])
        graphing_df = graphing_df[graphing_df["N Decks"] >= input.N_decks()]

        # # calculating graph width based on device size
        mobile = input.is_mobile()

        if mobile:
            width = 550
            sns.set_context("paper")
        else:
            width = 1100
            sns.set_context("notebook")

        # calculating graph height based on n cards in graph, and device size
        n_cards = len(graphing_df["Card"].unique())
        if n_cards < 11:
            height = "325px"
        else:
            height = str(n_cards * 27) + "px"

        return graphing_df, width, height

    @render.plot()
    def plot():
        graphing_df = filtered_graphing_df()[0]

        ax = sns.boxplot(
            x=graphing_df["Deck Score"],
            y=graphing_df["Card"],
            data=graphing_df,
            hue="N Decks",
            legend=True,
            saturation=1,
            palette="flare",
        )

        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin + 0.2, ymax - 0.2)

        ax.legend(bbox_to_anchor=(1, 1)).set_title(title="Number of\n    Decks")
        return ax

    @render.ui
    def my_plot():
        graph_inputs = filtered_graphing_df()

        return ui.output_plot("plot", width=graph_inputs[1], height=graph_inputs[2])


app = App(app_ui(), server, static_assets=www_dir)
