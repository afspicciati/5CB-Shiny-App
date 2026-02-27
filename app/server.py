from shiny import ui, render, App
import pandas as pd
import seaborn as sns


card_event_df = pd.read_csv('../card_event_df.csv')
score_agg = card_event_df.drop(columns=['Color Identity','Week']).groupby(by='Card',as_index=False).agg('mean').sort_values('Deck Score', ascending=False)
score_sort = dict(zip(score_agg['Card'],score_agg['Deck Score']))
basic_lands = ['plains', 'island', 'swamp', 'mountain', 'forest']
graphing_df = card_event_df[(card_event_df['N Decks'] >4) & (~card_event_df['Card'].isin(basic_lands))].sort_values(by='Card', key=lambda x: x.map(score_sort), ascending=False)



# Server function
def server(input, output, session):
    @render.plot()
    def plot():
        ax = sns.boxplot(x=graphing_df['Deck Score'], y=graphing_df['Card'],data=graphing_df,hue='N Decks',legend=True, saturation=1, palette='flare')
        ax.figure.set_size_inches(1, 20)
        ax.legend().set_title(title='Number of\n    Decks')
        return ax