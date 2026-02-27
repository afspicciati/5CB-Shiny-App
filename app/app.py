from shiny import ui, render, App
from ui import app_ui
from server import server


# This is a shiny.App object. It must be named `app`.
app = App(app_ui(), server)