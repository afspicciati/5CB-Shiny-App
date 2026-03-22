from shiny import ui, render, App, Inputs, reactive
import pandas as pd
import seaborn as sns
import json

# constants
basic_lands = ["plains", "island", "swamp", "mountain", "forest"]
with open("./data/week_links.json") as file:
    week_links = json.load(file)

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
N_weeks = table_stats["Week"].max()
# building selectize list
cards_counts_list = []
card_value_counts = card_event_df[
    ~card_event_df["Card"].isin(basic_lands)
].Card.value_counts()
for i in range(len(card_value_counts)):
    cards_counts_list.append([card_value_counts.index[i], card_value_counts.iloc[i]])

sorted_choices = sorted(cards_counts_list, key=lambda x: (-x[1], x[0]))
selectize_choices = [
    str(card_name) + " (" + str(card_counts) + ")"
    for (card_name, card_counts) in sorted_choices
]


# App function
def app_ui():

    my_ui = ui.page_fillable(
        ui.navset_card_pill(
            ui.nav_panel(
                "Card Search",
                ui.input_selectize("selectize_cards", "Card", selectize_choices),
                ui.page_fluid(ui.output_data_frame("deck_table")),
            ),
            ui.nav_panel(
                "Card Stats",
                ui.page_sidebar(
                    ui.sidebar(
                        ui.card(
                            ui.input_slider("weeks", "Weeks", 1, N_weeks, [0, N_weeks]),
                            ui.input_slider(
                                "N_decks", "Minimum Decks Containing Card", 2, 10, 6
                            ),
                            ui.input_checkbox("banned", "Include Banned Decks", True),
                            ui.input_checkbox("silly", "Include Silly Weeks", True),
                        ),
                        ui.card(
                            ui.markdown(
                                """
        #### Mirrored Winrates:
        Matches played against the same card are included in the dataset, so cards with high play rates will tend towards middle scores.
        #### Silly Weeks:
        The 4th week of each month, starting with week 17.
        #### Mobile:
        On mobile, I recommend opening the plot in a seperate tab or saving it, for easier viewing.
        """
                            )
                        ),
                        bg="#e6e6e6",
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
        title="Chancellor",
    )

    return my_ui


# Server function
def server(input: Inputs, output, session):

    ### TAB 1 (card table)
    @reactive.calc
    def create_graphing_table():
        card = input.selectize_cards().split(" (")[0]
        graphing_table = table_stats[
            [card in table_stats["Deck"].iloc[i] for i in range(len(table_stats))]
        ].reset_index()

        for i in range(len(graphing_table)):
            for j in range(5):
                graphing_table.loc[i, f"Card {j+1}"] = ui.a(
                    graphing_table["Deck"].iloc[i][j],
                    href=graphing_table[f"Card {j+1}"].iloc[i],
                    target="_blank",
                )

        return graphing_table.drop("index", axis=1).sort_values(
            "Score", ascending=False
        )

    @render.data_frame
    def deck_table():
        graphing_table = create_graphing_table()

        # graphing_table["Week"] = [
        #     ui.a(str(w), href=week_links[str(w)], target="_blank")
        #     for w in graphing_table["Week"]
        # ]

        return graphing_table.drop("Deck", axis=1)

    ### TAB 2 (card stats)
    @reactive.calc
    def create_graphing_df():
        graphing_df = card_event_df[
            (~card_event_df["Card"].isin(basic_lands))
            & (card_event_df["Week"] >= input.weeks()[0])
            & (card_event_df["Week"] <= input.weeks()[1])
        ]

        if not input.silly():
            silly_weeks = [17, 21, 25]
            graphing_df = graphing_df[~graphing_df["Week"].isin(silly_weeks)]

        if not input.banned():
            graphing_df = graphing_df[graphing_df["Deck Legal"] == True]

        score_agg = (
            graphing_df.drop(columns=["Color Identity", "Week"])
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
        return graphing_df, len(graphing_df["Card"].unique()) / 35 * 800

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
        ax.legend().set_title(title="Number of\n    Decks")
        return ax

    @render.ui
    def my_plot():
        return ui.output_plot(
            "plot", width="1000px", height=str(filtered_graphing_df()[1]) + "px"
        )


# This is a shiny.App object. It must be named `app`.
app = App(app_ui(), server)
