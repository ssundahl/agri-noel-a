#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

import jinja2
import webapp2

from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.api import images
from google.appengine.ext.webapp import blobstore_handlers

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class Card(ndb.Model):
    ID = ndb.IntegerProperty()
    CardName = ndb.StringProperty()
    CardNameNormalized = ndb.StringProperty()
    CardType = ndb.StringProperty()
    CardText = ndb.StringProperty()
    Difficulty = ndb.StringProperty()
    MinPlayers = ndb.IntegerProperty()
    Rulings = ndb.TextProperty()
    CardImage = ndb.BlobKeyProperty()
    CardImageURL = ndb.StringProperty()

class Player(ndb.Model):
    ID = ndb.IntegerProperty()
    PlayerName = ndb.StringProperty()
    PlayerEmail = ndb.StringProperty()

class Game(ndb.Model):
    ID = ndb.IntegerProperty()
    CreatedDate = ndb.DateTimeProperty(auto_now_add=True)

class Hand(ndb.Model):
    ID = ndb.IntegerProperty()

class AddCard(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/SubmitCard')
        template_values = {
            "upload": upload_url
        }
        template = JINJA_ENVIRONMENT.get_template('templates/add-card.html')
        self.response.write(template.render(template_values))

class SubmitCard(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        card = Card()
        card.CardName = self.request.get("CardName")
        card.CardNameNormalized = card.CardName.replace(" ", "").lower()
        card.CardType = self.request.get("CardType")
        card.CardText = self.request.get("CardText")
        card.Difficulty = self.request.get("Difficulty")
        card.MinPlayers = int(self.request.get("MinPlayers"))
        card.Rulings = self.request.get("Rulings")
        upload_files = self.get_uploads("CardImage")
        blob_info = None
        if len(upload_files) > 0:
            blob_info = upload_files[0]
        if blob_info is not None:
            card.CardImage = blob_info.key()
            card.CardImageURL = images.get_serving_url(blob_info.key())
        else:
            card.CardImage = None
            card.CardImageURL = "lose"
        card.put()
        self.redirect('/AddCard?Success=True&CardName=' + card.CardName)

class EditCard(webapp2.RequestHandler):
    def get(self, cardID):
        upload_url = blobstore.create_upload_url('/SubmitEdit')
        card = Card.get_by_id(int(cardID))
        card.ID = card.key.id()
        template_values = {
            "upload": upload_url,
            "card": card
        }
        template = JINJA_ENVIRONMENT.get_template('templates/edit-card.html')
        self.response.write(template.render(template_values))

class GetCards(webapp2.RequestHandler):
    def get(self):
        card_query = Card.query().order(Card.CardName)
        cards = card_query.fetch()
        for card in cards:
            card.ID = card.key.id()
            card.TrimmedName = card.CardName.replace(" ", "")
            rulings = card.Rulings
            rulings = rulings.rsplit("* ")
            if (len(rulings) > 1):
                rulings.pop(0)
                card.RulingsSplit = rulings	
        PostData = {
            "CardName": None,
            "CardType": None,
            "Difficulty": None, 
            "MinPlayers": None
        }
        template_values = {
            "Cards": cards,
            "PostData": PostData,
            "length": len(cards)
        }
        template = JINJA_ENVIRONMENT.get_template('templates/card-list.html')
        self.response.write(template.render(template_values))

    def post(self):
        cardName = self.request.get("CardNameLetter")
        cardType = self.request.get("CardType")
        cardDifficulty = self.request.get("CardDifficulty")
        cardMinPlayers = self.request.get("CardMinPlayers")

        PostData = {
            "CardName": cardName,
            "CardType": cardType,
            "Difficulty": cardDifficulty, 
            "MinPlayers": cardMinPlayers
        }

        filters = ""
        if cardName != "All":
            #self.response.write("cardName: " + cardName)
            last = unicode(cardName) + u"\ufffd"
            filters = filters + "where CardName >= '" + cardName + "' AND CardName < '" + last  + "'"
        query = "Select * from Card " + filters + " order by CardName asc"
        #self.response.write("query: " + query)
        card_query = ndb.gql(query)

        #cards = []
        cards = card_query.fetch()
        keep = []
        for card in cards:
            #self.response.write("length: " + str(len(cards)))
            #self.response.write("<br/> " + card.CardName)
            # filter cards
            if cardType != "All":
                if card.CardType != cardType:
                    continue
            if cardDifficulty != "All":
                if card.Difficulty != cardDifficulty:
                    continue
            if cardMinPlayers != "All":
                if card.MinPlayers != int(cardMinPlayers):
                    continue
            # update properties
            card.ID = card.key.id()
            card.TrimmedName = card.CardName.replace(" ", "")
            rulings = card.Rulings
            rulings = rulings.rsplit("* ")
            if (len(rulings) > 1):
                rulings.pop(0)
                card.RulingsSplit = rulings
            keep.append(card)

        template_values = {
            "Cards": keep,
            "PostData": PostData,
            "length": len(keep)
        }
        template = JINJA_ENVIRONMENT.get_template('templates/card-list.html')
        self.response.write(template.render(template_values))

class SubmitEdit(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        cardID = self.request.get("CardID")
        card = Card.get_by_id(int(cardID))
        card.CardName = self.request.get("CardName")
        card.TrimmedName = card.CardName.replace(" ", "")
        card.CardType = self.request.get("CardType")
        card.CardText = self.request.get("CardText")
        card.Difficulty = self.request.get("Difficulty")
        card.MinPlayers = int(self.request.get("MinPlayers"))
        card.Rulings = self.request.get("Rulings")
        upload_files = self.get_uploads("CardImage")
        blob_info = None
        if len(upload_files) > 0:
            blob_info = upload_files[0]
        if blob_info is not None:
            card.CardImage = blob_info.key()
            card.CardImageURL = images.get_serving_url(blob_info.key())
        card.put()
        self.redirect('/GetCards#' + card.TrimmedName)

class AddGame(webapp2.RequestHandler):
    def get(self):
        players = []
        player1 = { "PlayerName": "Scott"}
        player2 = { "PlayerName": "Noel"}
        players.append(player1)
        players.append(player2)
        template_values = {
            "players": players
        }
        template = JINJA_ENVIRONMENT.get_template('templates/add-game.html')
        self.response.write(template.render(template_values))

class GetGames(webapp2.RequestHandler):
	def get(self):
		self.response.write("Get Games")

class AddPlayer(webapp2.RequestHandler):
    def get(self, playerID):
        player = None
        try:
            player = Player.get_by_id(int(playerID))
        except Exception:
            player = None
        if player is None:
            player = Player()
            player.PlayerID = 0
            player.PlayerName = ""
            player.PlayerEmail = ""
        template_values = { 
            "PlayerID": playerID,
            "PlayerName": player.PlayerName,
            "PlayerEmail": player.PlayerEmail
        }
        template = JINJA_ENVIRONMENT.get_template('templates/add-player.html')
        self.response.write(template.render(template_values))

    def post(self):
        player = Player()
        edit = 'false'
        playerID = int(self.request.get("PlayerID"))
        if (playerID != 0):
            player = Player.get_by_id(int(playerID))
            edit = 'true'
        player.PlayerName = self.request.get("PlayerName")
        player.PlayerEmail = self.request.get("PlayerEmail")
        player.put()
        self.redirect('/AddPlayer/' + str(player.key.id()) + '?Success=true&Edit=' + edit + '&PlayerName=' + player.PlayerName)

class GetPlayers(webapp2.RequestHandler):
    def get(self):
        players = Player.query().fetch()
        for player in players:
            player.PlayerID = player.key.id()
        template_values = { 
            "Players": players
        }
        template = JINJA_ENVIRONMENT.get_template('templates/player-list.html')
        self.response.write(template.render(template_values))	


class MainHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {
          
        }
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        
        self.response.write(template.render(template_values))

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/AddCard', AddCard),
    ('/EditCard/(\d+)', EditCard),
    ('/GetCards', GetCards),
    ('/GetCards/.*', GetCards),
    ('/AddPlayer/(\d+)', AddPlayer),
    ('/AddPlayer', AddPlayer),
    ('/GetPlayers', GetPlayers),
    ('/AddGame', AddGame),
    ('/GetGames', GetGames),
    ('/SubmitCard', SubmitCard),
    ('/SubmitEdit', SubmitEdit),
    ('/.*', MainHandler)
], debug=True)
