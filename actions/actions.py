# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions



from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import random
import os, urllib.parse, requests
import logging

logger = logging.getLogger(__name__)

# dumb db, key: POI value: description
POI_db = {
    'stockholm':{'museum':{'vasa':'Vasa is actually a good museum! And the code is working smoothly now.'},'park':{'Kungsträdgården':'description for kung'}, 'caffe':{'Café Saturnus':'desc for cafe'},'shopping':{'NK Stockholm':'description for NK'}},
    'rome':{'museum':{},'park':{}, 'caffe':{},'shopping':{}},
    'paris':{'museum':{},'park':{}, 'caffe':{},'shopping':{}},
    'amsterdam':{'museum':{},'park':{}, 'caffe':{},'shopping':{}},

}


class ActionSearchPlace_w_Google(Action):

    def name(self) -> Text:
        return "action_search_POI"

    def run(self, dispatcher, tracker, domain):
        # retrieve slot values
        city = tracker.get_slot('city')
        category = tracker.get_slot('category')
        print(f"city: {city}, category: {category}")
        # retrieve google api key
        # with open("./ga_credentials.yml", 'r') as ymlfile:
        #     cfg = yaml.load(ymlfile)
        key = os.getenv('GOOGLE_PLACES_API')
        if key is None:
            raise KeyError("Google API not found. Set it as environment variable")

        # TODO - uncomment if you want to use geolocation
        # get user's current location
        # get_origin = requests.post(
        #     "https://www.googleapis.com/geolocation/v1/geolocate?key={}".format(key)).json()
        # print(get_origin)
        # origin_lat = get_origin['location']['lat']
        # origin_lng = get_origin['location']['lng']

        # look for a place using all the details
        # see:
        # https://developers.google.com/maps/documentation/places/web-service/search-text#maps_http_places_textsearch-py
        # additional parameters can be found here:
        # https://developers.google.com/maps/documentation/places/web-service/search-text#required-parameters
        params = {"query": city +" " + category, "key": key}
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?"
        url += urllib.parse.urlencode(params)

        payload = {}
        headers = {}

        place = requests.request("GET", url, headers=headers, data=payload)

        print(place.text)
        print(place)

        data = place.json()
        # TODO - change the code from here.
        # TODO - redirect output to log file

        if len(data['results']) == 0:
            dispatcher.utter_message("Sorry, I didn't find anything")
            return [SlotSet('location_match', 'none')]
        else:
            idx = random.randint(0, len(data['results']))
            name = data['results'][idx]['name']
            # rating = i['rating']
            # address = i['vicinity']

        speech = "I found a {} in {} called {} based on your specified parameters.".format(category, city, name)
        dispatcher.utter_message(speech)  # send the response back to the user
        return [SlotSet('city', city), SlotSet('category', category)]  # set returned details as slots


class ActionSerchPOI(Action):

    def name(self) -> Text:
        return "action_search_POI_old"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # retrieve category from last message (city should be already saved in a slotsss)
        current_category = next(tracker.get_latest_entity_values('category'), None)
        
        # if we already saved the city in the slot, use that as current city for the POI query
        city_in_slot = tracker.get_slot("city")
        if city_in_slot != None:
            current_city = city_in_slot
        
        if not current_city:
            msg = f"You want to visit {current_category}, but I need to know in which city 🤔"
            dispatcher.utter_message(text=msg)
        

        # display a sentence to feedback about what the bot understood
        msg = f'I will select the best {current_category} in {current_city} , give me few seconds! 🚏'
        dispatcher.utter_message(text=msg)

        # build the output message by querying the DB
        # check if the city is in the DB by retrieving the key
        dispatcher.utter_message(text=msg)
        city_POI = POI_db[str(current_city)]
        
        if not city_POI:            
            msg = f"sorry, I can't suggest anything about that city 😅"
            dispatcher.utter_message(text=msg)
            return []


        # retrieve category
        category_POI = city_POI[str(current_category)]
        if not city_POI:            
            msg = f"sorry, I don't know any good {current_category} in {current_city} 😅"
            dispatcher.utter_message(text=msg)
            return [SlotSet("city",current_city)]

        # extract the POI (here randomly, can use some policies to extract it)
        suggested_POI_name= random.choice(list(category_POI.keys()))
        suggested_POI_desc = category_POI[suggested_POI_name]

        # construct the message to display if we want to suggest a POI
        msg = "look at what I found! \n"
        msg += "you can visit "+suggested_POI_name
        msg += ", it seems interesting for you! \n"
        msg += "Here a brief description: \n"
        msg += suggested_POI_desc
        msg += "\nHope this was helpful! "
        
        dispatcher.utter_message(text=msg)

        # we set as current slot the city, in order to remember it if more POI are asked. 
        return [SlotSet("city",current_city)]

class ActionRememberCity(Action):
    def name(self) -> Text:
        return "action_remember_city"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:


        # retrieve entity values
        current_city = next(tracker.get_latest_entity_values('city'), None)
       
       # display a feedback (randomized between 2 sentences)
        rand = random.random()
        if rand > 0.5:
            msg = f"Nice choice! I would like to ask you more about what you want to visit in {current_city}  🤔"
        else:
            msg = f'{current_city} , nice one! First I need to ask you more info  🤔 '
        
        dispatcher.utter_message(text=msg)
        
        # we save the city in a slot      
        return [SlotSet("city",current_city)]




# hello world example
# class ActionSearchPOI(Action):

#     def name(self) -> Text:
#         return "action_search"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

#         dispatcher.utter_message(text="Hello World!")

#         return []
