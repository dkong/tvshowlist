import cgi
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template

from tvdb_api import tvdb_api 
from tvdb_api import tvdb_ui

t = tvdb_api.Tvdb(cache=False, debug=True, custom_ui=tvdb_ui.ClassUI)

class Greeting(db.Model):
    author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)

class MyShowData(db.Model):
    series_id = db.IntegerProperty()
    season_number = db.IntegerProperty()
    episode_number = db.IntegerProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class PersistentData(db.Model):
    """Data that nees to be accessible from multiple pages
    """
    series_id = db.IntegerProperty()

class MainPage(webapp.RequestHandler):
    def get(self):
        greetings_query = Greeting.all().order('-date')
        greetings = greetings_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = "Logout"
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Login"

        template_values = {
                'greetings': greetings,
                'url': url,
                'url_linktext': url_linktext
                }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class Guestbook(webapp.RequestHandler):
    def post(self):
        greeting = Greeting()

        if users.get_current_user():
            greeting.author = users.get_current_user()

        greeting.content = self.request.get('content')
        greeting.put()
        self.redirect('/')

class EpisodeAdd(webapp.RequestHandler):
    def post(self):
        page = self.response.out
        episodes = self.request.get_all('episode')
        persistentData = PersistentData.all().get()
        page.write(str(persistentData.series_id))
        page.write('<br>')
        for episode in episodes: 
            episode_data = episode.split('`')
            page.write("%s x %s : %s" % (episode_data[0], episode_data[1], episode_data[2]))
            page.write('<br>')


class EpisodeTemplate:
    season = -1
    episode = -1
    name = "None"

    def __init__(self, season_num, episode_num, episode_name):
        self.season = season_num
        self.episode = episode_num
        self.name = episode_name
    
class SeriesAdd(webapp.RequestHandler):
    def post(self):
        page = self.response.out
        series_name = cgi.escape(self.request.get('series'))

        t.config['custom_ui'] = None
        series = t[series_name]

        persistentData = PersistentData.all().get()
        if not persistentData:
            persistentData = PersistentData()
        persistentData.series_id = int(series['sid'])
        persistentData.put()

        episodes_list = []
        for season in series:
            for episode in series[season]:
                episodeTemplate = EpisodeTemplate(season, episode, series[season][episode]['episodename'])
                episodes_list.append(episodeTemplate)

        template_values = {
                'episodes': episodes_list,
                }

        path = os.path.join(os.path.dirname(__file__), 'series_add.html')
        self.response.out.write(template.render(path, template_values))

        t.config['custom_ui'] = tvdb_ui.ClassUI

class MovieResults(webapp.RequestHandler):
    def post(self):
        page = self.response.out
        movie_name = cgi.escape(self.request.get('movie'))

        t.config['custom_ui'] = tvdb_ui.ClassUI
        try:
            series_results = t._getSeries(movie_name)
        except:
            series_results = []

        series_names = []
        for series in series_results:
            series_names.append(series['seriesname'])

        template_values = {
                'series_results': series_names,
                }

        path = os.path.join(os.path.dirname(__file__), 'results.html')
        self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication(
        [('/', MainPage),
         ('/sign', Guestbook),
         ('/results', MovieResults),
         ('/series_add', SeriesAdd),
         ('/episode_add', EpisodeAdd)],
        debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

