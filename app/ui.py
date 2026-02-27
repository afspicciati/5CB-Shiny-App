from shiny import ui, render, App

# User Interface

def app_ui():

    my_ui = ui.page_fluid(
        ui.output_plot("plot", width= '100%', height='800px')
    )
    return(my_ui)