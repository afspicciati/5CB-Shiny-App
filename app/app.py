from shiny import ui, render, App, Inputs, reactive
import pandas as pd
import seaborn as sns

# constants
basic_lands = ["plains", "island", "swamp", "mountain", "forest"]
weeks_5cb = {
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
}

# load data
card_event_df = pd.read_csv("./data/card_event_df.csv")
raw_5cb_stats = pd.read_csv("./data/raw_5cb_stats.csv")

### working with data
# weeks count
N_weeks = raw_5cb_stats["Week"].max()
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
    @render.data_frame
    def deck_table():
        raw_5cb_stats["Week"] = [
            ui.a(f"""Week {w}""", href=weeks_5cb[w], target="_blank")
            for w in raw_5cb_stats["Week"]
        ]

        return raw_5cb_stats

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
