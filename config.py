import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TOKEN = os.environ.get("TOKEN")
API_KEY = os.environ.get("API_KEY")
DEVELOPER_CHAT_ID = os.environ.get("DEVELOPER_CHAT_ID")
DEVELOPER_USER_ID = os.environ.get("DEVELOPER_USER_ID")

URL = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

BOT_LEAGUES = {
    39: "🏴󠁧󠁢󠁥󠁮󠁧󠁿󠁢 Premier League",
    140: "🇪🇸 La Liga",
    61: '🇫🇷 Ligue 1',
    242: "🇮🇹 Serie A",
    78: '🇩🇪 Bundesliga',
    2: '✨ UEFA Champions League',
    3: '🇪🇺 UEFA Europa League',
    333: '🇺🇦 UPL',
    848: '🥉 UEFA Europa Conference League',
    94: '🇵🇹 Primeira Liga',
    88: '🇳🇱 Eredivisie',
    180: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 󠁢󠁥󠁮󠁧󠁿󠁢󠁥󠁮󠁧󠁿Championship',
    144: '🇧🇪 Jupiler Pro League',
    203: '🇹🇷 Super Lig',
}

HEADERS = {
    'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
    'x-rapidapi-key': API_KEY
}
