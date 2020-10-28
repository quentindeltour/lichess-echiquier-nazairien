import berserk
from dotenv import load_dotenv
import os
import requests
import time
import dash_html_components as html
import dash_core_components as dcc
import base64 
import ndjson
import re
import pandas as pd

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
    return html.Div([get_header(app), html.Br([]), get_menu()])


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
                                href="/dash-echiquier-nazairien/full-view",
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
                href="/dash-echiquier-nazairien/overview",
                className="tab first",
            ),
            dcc.Link(
                "Resultats individuels",
                href="/dash-echiquier-nazairien/individual-results",
                className="tab",
            ),
            dcc.Link(
                "Resultats des Tournois",
                href="/dash-echiquier-nazairien/tournament-results",
                className="tab",
            ),
            dcc.Link(
                "Classement Général",
                href="/dash-echiquier-nazairien/tournament-general-results",
                className='tab'
            ),
            dcc.Link(
                "Challenge Puzzle",
                href="/dash-echiquier-nazairien/puzzle-results",
                className="tab",
            ),
        ],
        className="row all-tabs",
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
    return rep['name'], rep['description'], rep['leader']['name'], rep['nbMembers'], rep['location']

def update_players_list(club):
    rep = get("https://lichess.org/api/team/{}/users".format(str(club)))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    available_users = df.username.unique()
    return available_users.tolist(), [{'label': str(i), 'value': str(i)} for i in sorted(available_users)], df.sort_values('perfs.blitz.rating', ascending=False).username.array[0]

def update_tournament_list(club):
    rep = get('https://lichess.org/api/team/{}/swiss'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    return [{'label': str(df.name[i]), 'value': str(df.id[i])} for i in range(len(df))], df[df.status == 'finished'].id.values[0]

def update_global_tournament_ranking(club):
    rep = get('https://lichess.org/api/team/{}/swiss'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df_list = []
    for id_tourn in df.id:
        rep = get("https://lichess.org/swiss/{}.trf".format(str(id_tourn)))
        lines = [line for line in rep.text.splitlines()]
        list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
        df_list.append(pd.DataFrame(list_df))
    df_final = pd.concat(df_list)
    df_final[4] = df_final[4].astype(float)
    gb = df_final.groupby(2)
    df_table = pd.DataFrame(gb[4].sum()).merge(pd.DataFrame(gb[4].count()), left_index=True, right_index=True)
    df_table['Joueur'] = df_table.index
    df_table.rename(columns={'4_x':'Score total', '4_y':'Nombre de tournois joués'}, inplace=True)
    df_table.sort_values('Score total', ascending=False, inplace=True)
    df_table['Classement Général'] = range(1,len(df_table)+1,1)
    columns_table=[{'name': col, 'id': col} for col in ['Classement Général', 'Joueur','Nombre de tournois joués','Score total' ]]
    return df_table.to_dict('records'), columns_table

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