import berserk
from dotenv import load_dotenv
import os
import requests
import time
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc

import base64 
import ndjson
import re
import pandas as pd
from controls import ID_NOM

#IMAGE :
image_directory =  os.getcwd() + '/assets/'
image_filename = image_directory + 'Lichess_Logo_2019.png' # replace with your own image
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

def load_lichess_api_key():
    load_dotenv(".env")
    return os.getenv("LICHESS_KEY")

def create_lichess_session():
    LICHESS_KEY = load_lichess_api_key()
    session = berserk.TokenSession(LICHESS_KEY)
    client = berserk.Client(session=session)
    return client

def get_my_email(client):
    return client.account.get_email()

#Fonction scrape:
def get(url):
    while True:
        response = requests.get(url)
        if response.status_code != 200:
            time.sleep(1)
        else:
            return response


def Header(app):
    return html.Div([get_header(app), html.Br([]), get_new_menu()])


def get_header(app):
    header = html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src='data:image/png;base64,{}'.format(encoded_image.decode()),
                        className='logo'
                    ),
                    html.A(
                        html.Button("Team sur Lichess", id="big-lichess-button"),
                        href="https://lichess.org/team/echiquier-nazairien",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [html.H5("Echiquier Nazairien")],
                        className="seven columns main-title",
                    ),
                    html.Div(
                        [
                            dcc.Link(
                                "Full View",
                                href="/echiquier-nazairien/full-view",
                                className="full-view-link",
                            )
                        ],
                        className="five columns",
                    ),
                ],
                className="twelve columns",
                style={"padding-left": "0"},
            ),
        ],
        className="row",
    )
    return header


def get_menu(): 
    menu = html.Div(
        [
            dcc.Link(
                "Vue générale du club",
                href="/echiquier-nazairien/overview",
                className="tab first",
            ),
            dcc.Link(
                "Resultats individuels",
                href="/echiquier-nazairien/individual-results",
                className="tab",
            ),
            dcc.Link(
                "Tournois Internes",
                href="/echiquier-nazairien/tournament-results",
                className="tab",
            ),
            dcc.Link(
                "Challenge Nazairien",
                href="/echiquier-nazairien/tournament-swiss-results",
                className='tab'
            ),
            dcc.Link(
                "Match d'équipe PDL",
                href="/echiquier-nazairien/tournament-team-results",
                className='tab'
            ),
        ],
        className="row all-tabs",
    )
    return menu

def get_new_menu():
    menu = dbc.Navbar(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(html.Img(
                            src='data:image/png;base64,{}'.format(encoded_image.decode()),
                            className='logo'
                        ),
                        ),
                        dbc.Col(dbc.NavbarBrand("Lichess App", className="ml-2")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="https://lichess.org/",
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        ],
        color="dark",
        dark=True,
    )
    return menu

def make_dash_table(df):
    """ Return a dash definition of an HTML table for a Pandas dataframe """
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table


def update_club_informations(club):
    resp = get("https://lichess.org/api/team/{}".format(str(club)))
    rep = resp.json()
    rep['location'] = "Saint-Nazaire"
    return rep['name'], rep['description'], ID_NOM.get(rep['leader']['name'], rep['leader']['name']), rep['nbMembers'], rep['location']

def update_players_list(club):
    rep = get("https://lichess.org/api/team/{}/users".format(str(club)))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    available_users = df.id.unique()
    return available_users.tolist(), [{'label': ID_NOM.get(str(i), str(i)), 'value': str(i)} for i in sorted(available_users)], df.sort_values('perfs.blitz.rating', ascending=False).username.array[0]

def update_tournament_list(club):
    rep = get('https://lichess.org/api/team/{}/swiss'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    return [{'label': str(df.name[i]), 'value': str(df.id[i])} for i in range(len(df))], df[df.status == 'finished'].id.values[0]

def update_team_arena_list(club):
    rep = get('https://lichess.org/api/team/{}/arena'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df = df[df.fullName.str.contains("PDL")]
    return [{'label': str(df.loc[i, 'fullName']), 'value': str(df.loc[i, 'id'])} for i in df.index], df[df.status == 30]['id'].iloc[0]


def update_tables_club_puzzle(club):
    rep = get("https://lichess.org/api/team/{}/users".format(str(club)))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df_table = df[['username', 'perfs.{}.games'.format('puzzle'), 'perfs.{}.rating'.format('puzzle'), 'perfs.{}.prog'.format('puzzle')]]
    return df_table


def filter_list_between_strings(start, end, liste):
    index_start, index_end = liste.index(start + '-puzzle.csv'), liste.index(end + '-puzzle.csv')
    if index_start <= index_end:
        sublist = [element for index, element in enumerate(liste) if index in range(index_start, index_end+1)]
    else:
        sublist = [element for index, element in enumerate(liste) if index in range(index_end, index_start+1)]
    return sublist

