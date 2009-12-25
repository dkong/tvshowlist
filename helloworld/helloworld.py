import cgi
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template

from tvdb_api import tvdb_api 
from tvdb_api import tvdb_ui

t = tvdb_api.Tvdb(cache=False, debug=True, custom_ui=tvdb_ui.ClassUI, language='en')

class Greeting(db.Model):
    author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)

class MyShowData(db.Model):
    series_id = db.IntegerProperty()
    season_number = db.IntegerProperty()
    episode_number = db.IntegerProperty()
    user = db.UserProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class PersistentData(db.Model):
    """Data that nees to be accessible from multiple pages
    """
    series_id = db.IntegerProperty()

class EpisodeTemplate:
    season = -1
    episode = -1
    name = "None"
    series = "None"
    key = "None"
    exists = False

    def __init__(self, series_name, season_num, episode_num, episode_name, key=None, already_exists=False):
        self.season = season_num
        self.episode = episode_num
        self.name = episode_name
        self.series = series_name
        self.key = key
        self.exists = already_exists

class MyListPage(webapp.RequestHandler):
    def get(self):
        myshowdata_query = MyShowData.all()
        myshowdata_query.filter("user =", users.get_current_user())
        myshowdata_query.order("-series_id")
        myshowdatas = myshowdata_query.fetch(1000)

        episodes_list = []
        for episode in myshowdatas:
            episodeTemplate = EpisodeTemplate(t[episode.series_id]['seriesname'], episode.season_number, episode.episode_number, t[episode.series_id][episode.season_number][episode.episode_number]['episodename'], str(episode.key()))
            episodes_list.append(episodeTemplate)

        template_values = {
                'episodes': episodes_list,
                }

        path = os.path.join(os.path.dirname(__file__), 'my_list.html')
        self.response.out.write(template.render(path, template_values))

class MainPage(webapp.RequestHandler):
    def get(self):
        greetings_query = Greeting.all().order('-date')
        greetings = greetings_query.fetch(10)

        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = "Logout"
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = "Login"

        url_mylist = '/my_list'

        template_values = {
                'greetings': greetings,
                'url': url,
                'url_linktext': url_linktext,
                'url_mylist': url_mylist,
                'user': user
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

            myshowdata = MyShowData()
            myshowdata.series_id = persistentData.series_id
            myshowdata.season_number = int(episode_data[0])
            myshowdata.episode_number = int(episode_data[1])
            myshowdata.user = users.get_current_user()
            myshowdata.put()

            page.write("S%02dE%02d : %s" % (int(episode_data[0]), int(episode_data[1]), episode_data[2]))
            page.write('<br>')

class EpisodeDelete(webapp.RequestHandler):
    def post(self):
        page = self.response.out
        episodes = self.request.get_all('episode')

        for episode_key in episodes: 
            episode = db.get(db.Key(episode_key))
            page.write("Deleting %d %d %d<br>" % (episode.series_id, episode.season_number, episode.episode_number))
            episode.delete()

class SeriesAdd(webapp.RequestHandler):
    def post(self):
        page = self.response.out
        series_name = cgi.escape(self.request.get('series'))

        t.config['custom_ui'] = None
        series = t[series_name]
        series_name = series['seriesname']

        persistentData = PersistentData.all().get()
        if not persistentData:
            persistentData = PersistentData()
        persistentData.series_id = int(series['sid'])
        persistentData.put()

        episodes_list = []
        for season in series:
            for episode in series[season]:
                # Does this episode already exist in our personal list?
                myshowdata_query = MyShowData.all()
                myshowdata_query.filter("series_id =", persistentData.series_id)
                myshowdata_query.filter("season_number =", season)
                myshowdata_query.filter("episode_number =", episode)
                myshowdata = myshowdata_query.fetch(1000)
                exists = len(myshowdata) != 0

                episodeTemplate = EpisodeTemplate(series_name, season, episode, series[season][episode]['episodename'], already_exists=exists)
                episodes_list.append(episodeTemplate)

        template_values = {
                'series_name': series_name,
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
         ('/episode_add', EpisodeAdd),
         ('/my_list', MyListPage),
         ('/episode_delete', EpisodeDelete)],
        debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

