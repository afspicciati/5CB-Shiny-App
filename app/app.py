from shiny import ui, render, App, Inputs, reactive
import pandas as pd
import seaborn as sns

# constants
basic_lands = ['plains', 'island', 'swamp', 'mountain', 'forest']

# load data
card_event_df = pd.read_csv('./data/card_event_df.csv')
raw_5cb_stats = pd.read_csv('./data/raw_5cb_stats.csv')

### working with data
# weeks count
N_weeks = raw_5cb_stats['Week'].max()

# App function
def app_ui():

    my_ui = ui.page_sidebar(
        ui.sidebar(
            ui.card(
                ui.input_slider('weeks', 'Weeks', 1, N_weeks, [0,N_weeks]),
                ui.input_slider('N_decks', 'Minimum Decks Containing Card', 2, 10, 6),
                ui.input_checkbox('banned','Include Banned Decks', True),
                ui.input_checkbox('silly', 'Include Silly Weeks', True)
            ),
            ui.card(
                ui.markdown(
                """
                #### Mirrored Winrates:
                Matches played against the same card are included in the dataset, so cards with high play rates will tend towards middle scores.
                #### Silly Weeks:
                The 4th week of each month, starting with week 17.
                """
                )
            ),
            ui.tags.a("GitHub", href='https://github.com/afspicciati/5CB-Shiny-App', target='_blank'),
            bg='#e6e6e6'
        ),
        ui.page_fluid(
            ui.output_ui('my_plot')
        )
    )
    return(my_ui)



# Server function
def server(input: Inputs, output, session):
    
    @reactive.calc
    def create_graphing_df():
        graphing_df =  card_event_df[(~card_event_df['Card'].isin(basic_lands))
                        & (card_event_df['Week'] >= input.weeks()[0]) & (card_event_df['Week'] <= input.weeks()[1])
                        ]

        if not input.silly():
            silly_weeks = [17,21]
            graphing_df = graphing_df[~graphing_df['Week'].isin(silly_weeks)]

        if not input.banned():
            graphing_df = graphing_df[graphing_df['Deck Legal'] == True]


        score_agg = graphing_df.drop(columns=['Color Identity','Week']).groupby(by='Card',as_index=False).agg('mean').sort_values('Deck Score', ascending=False)
        score_sort = dict(zip(score_agg['Card'],score_agg['Deck Score']))
        return graphing_df.sort_values(by='Card', key=lambda x: x.map(score_sort), ascending=False)
    
    @reactive.calc
    def filtered_graphing_df():
        graphing_df = create_graphing_df()
        value_counts = graphing_df['Card'].value_counts() 
        graphing_df['N Decks'] = graphing_df['Card'].apply(lambda x: value_counts[x])
        graphing_df = graphing_df[graphing_df['N Decks'] >= input.N_decks()]
        return graphing_df, len(graphing_df['Card'].unique())/35 * 800
    

    @render.plot()
    def plot():
        graphing_df = filtered_graphing_df()[0]
        
        ax = sns.boxplot(x=graphing_df['Deck Score'], y=graphing_df['Card'],data=graphing_df,hue='N Decks',legend=True, saturation=1, palette='flare')
        ax.legend().set_title(title='Number of\n    Decks')
        return ax

    @render.ui
    def my_plot():
        return ui.output_plot('plot', width= '1000px', height=str(filtered_graphing_df()[1]) + 'px')

# This is a shiny.App object. It must be named `app`.
app = App(app_ui(), server)