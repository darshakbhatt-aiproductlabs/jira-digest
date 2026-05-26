from . import gmail, smtp, slack, teams

CHANNELS = {
    "gmail": gmail.send,
    "smtp": smtp.send,
    "slack": slack.send,
    "teams": teams.send,
}
