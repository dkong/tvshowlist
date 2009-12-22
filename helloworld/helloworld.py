import cgi
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template

from tvdb_api import tvdb_api 
from tvdb_api import tvdb_ui

t = tvdb_api.Tvdb(cache=False, custom_ui=tvdb_ui.ClassUI)

class Greeting(db.Model):
	author = db.UserProperty()
	content = db.StringProperty(multiline=True)
	date = db.DateTimeProperty(auto_now_add=True)

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

class MovieResults(webapp.RequestHandler):
	def post(self):
		page = self.response.out
		movie_name = cgi.escape(self.request.get('movie'))

		try:
			series_results = t._getSeries(movie_name)
		except:
			series_results = []
		#print episode['episodename'] # Print episode name

		"""page.write('<html><body>You wrote:<pre>')
		for series in series_results:
			page.write(series['seriesname']+'\n')
		page.write('</pre></body></html>')
		"""

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
		 ('/results', MovieResults)],
		debug=True)

def main():
	run_wsgi_app(application)

if __name__ == '__main__':
	main()

