# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

# TODO - add utter_description --> DONE
# TODO - add utter_location (neighborhood, ...) --> DONE
# TODO - add utter_price (low price, mid price, high price, EXACT PRICE) --> DONE
# TODO - save POIs, filter those with low rating. Add flag to POIs already proposed to the user --> DONE

# TODO - add photo
# TODO - add action with SUBCATEGORY: e.g. museum modern art

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import random
import os, urllib.parse, requests
import logging
import json
import numpy as np
from langdetect import detect
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.FileHandler(filename=".//logs//log_actions.log")
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)

logger.debug(os.getcwd())

category_id_map = json.load(open(".\\data\\subcategory_map_fsq.json", "r"))
category_entity_map = json.load(open(".\\data\\category_map.json"))



def initialize_map():
    poi_by_category = {}
    for category in category_entity_map.keys():
        poi_by_category[category] = []
    poi_by_category['all'] = []
    poi_by_category['all_fsq_id'] = []
    poi_by_category['all_place_id'] = []
    return poi_by_category


poi_by_category = initialize_map()



class ActionAskCategory(Action):

    def name(self) -> Text:
        return "action_ask_category"

    def run(self, dispatcher, tracker, domain):
        city = tracker.get_slot('city')
        last_intent = tracker.get_intent_of_latest_message()
        buttons = []
        speeches_first_time = [
            "{}! Nice choice! What would you like to visit? Park, museum or cafe?",
            "What would you like to see in {}? Park, museum or cafe?"
        ]
        speeches_more_suggestions = [
            "What else would you like to see in {}? Another {} or something new?",
            "What could you like to visit in {}? Park, museum or cafe?"
        ]
        logger.debug(f"Previous user intent: {last_intent}")
        speeches = speeches_first_time if last_intent != 'ask_more_suggestions' else speeches_more_suggestions
        idx = random.randint(0, len(speeches) - 1)
        speech = speeches[idx].format(city)

        buttons.append({"title": "Museum", "payload": "museum"})
        buttons.append({"title": "Park", "payload": "park"})
        buttons.append({"title": "Cafe", "payload": "cafe"})

        dispatcher.utter_message(speech, buttons=buttons)

        return [SlotSet('referenced_category', tracker.get_slot("referenced_category")),
                SlotSet('category', None),
                SlotSet('city', city),
                SlotSet('subcategory', tracker.get_slot('subcategory'))]

#
# class ActionAskSomethingCLose(Action):
#
#     def name(self) -> Text:
#         return "action_ask_something_close"
#
#     def run(self, dispatcher, tracker, domain):
#         category = tracker.slots.get("category", None)
#         referenced_category = tracker.slots.get("referenced_category", last_category)
#         try:
#             ll = list(poi_by_category[referenced_category][-1]['geocodes']['main'].values())
#         except Exception as e:
#             logger.debug(f"Exception occured in customized action 'ask something close' + {e}")
#             dispatcher.utter_message("I'm sorry. I can't find anything that fits your request")
#             return [SlotSet('referenced_category', referenced_category),
#                     SlotSet('category', category),
#                     SlotSet('city', tracker.get_slot('city')),
#                     SlotSet('subcategory', tracker.get_slot('subcategory'))]
#         conversation_id = tracker.sender_id
#         place_info, has_description = foursquare_place_search(last_city, category, None, logger, conversation_id, ll=ll,
#                                                               use_old_search=False,
#                                                               exclude_fsq_ids=poi_by_category['all_fsq_id'])
#         if place_info is None:
#             dispatcher.utter_message("I'm sorry. I can't find anything that fits your request")
#             return [SlotSet('referenced_category', referenced_category),
#                     SlotSet('category', category),
#                     SlotSet('city', tracker.get_slot('city')),
#                     SlotSet('subcategory', tracker.get_slot('subcategory'))]
#         name = place_info['name']
#         neighborhood = get_neighborhood(place_info)
#         description = get_description(place_info, has_description)
#         speech = get_utterance(last_city, name, category, neighborhood, description, has_description)
#         photo_url = get_photo_url(place_info)
#         dispatcher.utter_message(speech, image=photo_url)
#         poi_by_category[category].append(place_info)
#         poi_by_category['all'].append(place_info)
#         poi_by_category['all_fsq_id'].append(place_info['fsq_id'])
#         return [SlotSet('referenced_category', referenced_category),
#                 SlotSet('category', category),
#                 SlotSet('city', tracker.get_slot('city')),
#                 SlotSet('subcategory', tracker.get_slot('subcategory'))]
#

class ActionPriceRange(Action):

    def name(self) -> Text:
        return "action_ask_price_range"

    def run(self, dispatcher, tracker, domain):
        if len(poi_by_category['all']) == 0:
            logger.debug("ACTION 'PRICE RANGE': there is no existing POI")
            dispatcher.utter_message(
                "I did not suggest any point of interest. I can't give you any price range information")
        else:
            utterance = self._generate_utterance_for_place_price(poi_by_category['all'][-1])
            dispatcher.utter_message(utterance)
        return [SlotSet('referenced_category', tracker.get_slot('referenced_category')),
                SlotSet('category', tracker.get_slot('category')),
                SlotSet('city', tracker.get_slot('city')),
                SlotSet('subcategory', tracker.get_slot('subcategory'))]

    def _generate_utterance_for_place_price(self, place_info):
        values_map = {
            0: "free",
            1: "cheap",
            2: "moderately expensive",
            3: "expensive",
            4: "very expensive"
        }
        utterances = [
            "{} should be {}",
            "I discovered that {} is {}",
            "According to what I found, {} is {}",
            "According to my sources, {} should be {}"
        ]
        name_place = place_info['name']
        price_range = place_info['price'] if 'price' in place_info.keys() else -1
        price_text = values_map[price_range] if price_range != -1 else None
        idx = random.randint(0, len(utterances) - 1)
        utterance = utterances[idx].format(place_info['name'], price_text) if price_range != -1 else \
            f"I'm sorry, I did not found any price information regarding {name_place}"
        return utterance


class ActionSearchPlace_w_Google(Action):
    def __init__(self):
        self.last_city = None
        self.last_category = None

    def name(self) -> Text:
        return "action_search_POI"

    def run(self, dispatcher, tracker, domain):
        # retrieve slot values
        city = tracker.get_slot('city')
        category = tracker.get_slot('category')
        use_old_search = True if self.last_city == city and self.last_category == category else False
        subcategory = tracker.get_slot('subcategory')
        category = category_entity_map[category]
        subcategory = "" if subcategory is None else subcategory
        logger.debug(f"city: {city}, category: {category}, subcategory: {subcategory}")

        conversation_id = tracker.sender_id

        # place_info, photo = google_search_wrapper(city, category, conversation_id)
        category_id = category_id_map[subcategory] if subcategory in category_id_map.keys() else \
            category_id_map[category]
        place_info, has_description = foursquare_place_search(city=city, category=category, subcategory=subcategory,
                                                              category_id=category_id, conversation_id=conversation_id,
                                                              logger=logger, use_old_search=False,
                                                              exclude_fsq_ids=poi_by_category['all_fsq_id'])
        if place_info is None:
            dispatcher.utter_message(f"Sorry, I didn't find anything in {city} that fits your request")
            return [SlotSet('location_match', 'none')]

        name = place_info['name']
        description = get_description(place_info, has_description)
        neighborhood = get_neighborhood(place_info)

        if category is not None:
            cat_name = category_entity_map[category]
            poi_by_category[cat_name].append(place_info)
            poi_by_category['all'].append(place_info)
            poi_by_category['all_fsq_id'].append(place_info['fsq_id'])
        speech = get_utterance(city, name, category, neighborhood, description, has_description)
        photo_url = get_photo_url(place_info)
        dispatcher.utter_message(speech, image=photo_url)  # send the response back to the user
        self.last_city = city
        self.last_category = category
        return [SlotSet('city', city), SlotSet('category', category),
                SlotSet('subcategory', subcategory)]  # set returned details as slots

def google_search_wrapper(city, category, conversation_id, use_old_search=True, ll=None, exclude_place_ids=[]):
    data_file_folder = f".\\conversations\\{conversation_id}"
    try:
        os.makedirs(data_file_folder)
    except:
        pass
    key = os.getenv("GOOGLE_PLACES_API")
    if key is None:
        logger.error("GOOGLE_PLACES_API not found. Set it as environment variable")
        exit(1)
    poi = google_place_search(city, category, key, os.path.join(data_file_folder, "places_google.json"), use_old_search, ll, exclude_place_ids)
    place_id = poi['place_id']
    poi_details = google_place_details(place_id, key, os.path.join(data_file_folder, "place_details_google.json"))
    photo_reference = poi_details['photos'][0]['photo_reference'] if isinstance(poi['photos'], list) else \
            None
    google_maps_url = poi_details['url'] if 'url' in poi_details.keys() else None
    # description = google_extract_description(google_maps_url)
    photo = google_photo_search(photo_reference=photo_reference, key=key)
    add_poi_to_category(poi_details, category, "GOOGLE")
    return poi_details, photo

def google_place_search(city, category, key, data_file_path, use_old_search=True, ll=None, exclude_place_ids=[]):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json?"
    params = {
        "query": f"{category} in {city}",
        "key": key
    }
    if ll is not None:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
        location_params = {
            "location": ll[0] + "," + ll[1]
        }
        params = params.update(location_params)
    url += urllib.parse.urlencode(params)
    if os.path.exists(data_file_path) and use_old_search:
        with open(data_file_path) as json_file:
            data = json.load(json_file)
    else:
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200 or 'results' not in data.keys() or len(data['results']) == 0:
            logger.error("GOOGLE REQUEST DID NOT PROVIDE ANY RESULT")
            logger.debug(f"Response json: {response.json()}\n\nUrl: {response.url}\n\nHeaders: {response.headers}")
            return None
        json.dump(data, open(data_file_path, "w"), indent=4, sort_keys=True)
    results = list(filter(lambda x: x['place_id'] not in exclude_place_ids, data['results']))
    if len(results) == 0:
        logger.error("NO MORE LEFT RESULTS. AFTER FILTERING OUT exclude_place_ids PLACES, THERE IS NO POI LEFT")
        return None

    return results[0]

def google_photo_search(photo_reference, key):
    if photo_reference is None:
        return None
    url = "https://maps.googleapis.com/maps/api/place/photo?parameters"
    params = {
        "key": key,
        "photo_reference": photo_reference,
    }
    url += urllib.parse.urlencode(params)
    response = requests.get(url)
    img = response.json()
    #  len(data['result'])!=1 since this api request must return the details of ONE POI (the one specified by place_id)
    if response.status_code != 200:
        logger.error("GOOGLE DID NOT PROVIDE ANY PHOTO FOR THE SPECIFIED PLACE")
        logger.debug(f"Photo reference: {photo_reference}"
                     f"Response json: {img}"
                     f"Response status code: {response.status_code}")
        return None
    return img

def google_place_details(place_id, key, data_file_path):
    url = "https://maps.googleapis.com/maps/api/place/details/json?"
    params = {
        "key": key,
        "place_id": place_id,
        "fields": "address_component,geometry,place_id,name,photos,opening_hours"
    }
    url += urllib.parse.urlencode(params)
    response = requests.get(url)
    data = response.json()
    #  len(data['result'])!=1 since this api request must return the details of ONE POI (the one specified by place_id)
    if response.status_code != 200 or len(data['result'])!=1:
        logger.error("GOOGLE DID NOT PROVIDE ANY DETAILS FOR THE SPECIFIED PLACE")
        logger.debug(f"Place id: {place_id}"
                     f"Response json: {data}"
                     f"Response status code: {response.status_code}")
        return None
    json.dump(data, open(data_file_path, "w"), indent=4, sort_keys=True)
    return data['result']

def add_poi_to_category(poi, category, api="GOOGLE"):
    api.upper()
    if api not in ['GOOGLE', 'FOURSQUARE']:
        logger.error(f"API ARGUMENT NOT VALID: should be one between GOOGLE or FOURSQUARE, FOUND: {api}")
        logger.error("The returned entity has not been formatted")
        return poi
    if api == 'GOOGLE':
        photo_reference = poi['photos'][0]['photo_reference'] if isinstance(poi['photos'], list) else \
            None
        neighborhood = get_neighborhood(poi, "GOOGLE")
        poi_formatted = {
            "format": api,
            "id": poi['place_id'],
            "name": poi['name'],
            "location": poi['geometry']['location'], # dictionary: {"lat": <value>, "lng": <value>}
            "photo_reference": photo_reference,
            "opening_hours": poi['opening_hours'],
            "neighborhood": neighborhood,
            "price_level": poi['price_level']
        }
        poi_by_category[category].append(poi_formatted)
        poi_by_category['all'].append(poi_formatted)
        poi_by_category['all_place_id'].append(poi['place_id'])
    else:
        lat_lng = {
            "lat": poi['geocodes']['main']['latitude'],
            "lng": poi['geocodes']['main']['longitude']
        }
        photo_reference = poi['photos'][0]['prefix']+"original"+poi['photos'][0]['suffix'] if \
            'photos' in poi.keys() and (poi['photos'])>0 else None
        neighborhood = poi['location']['neighborhood'][0] if 'location' in poi.keys() and \
            'neighborhoood' in poi['location'].keys() and len(poi['location']['neighrborhood'])>0 else None
        poi_formatted = {
            "format": api,
            "id": poi['fsq_id'],
            "name": poi['name'],
            "location": lat_lng,  # dictionary: {"lat": <value>, "lng": <value>}
            "photo_reference": photo_reference,
            "opening_hours": poi['opening_hours'],
            "neighborhood": neighborhood,
            "price_level": poi['price']
        }
        poi_by_category[category].append(poi_formatted)
        poi_by_category['all'].append(poi_formatted)
        poi_by_category['all_fsq_id'].append(poi['placfsq_id'])
    return poi_formatted

def foursquare_place_search(city, category, subcategory, logger,
                            conversation_id, category_id=None, sort='rating', ll=None, use_old_search=True,
                            exclude_fsq_ids=[]):
    if str.lower(sort) not in ['relevance', 'rating', "distance"]:
        sort = 'rating'
    data_file_path = f".\\conversations\\{conversation_id}\\data_fsq.json"
    try:
        os.makedirs(f".\\conversations\\{conversation_id}")
    except:
        pass

    key = os.getenv("FOURSQUARE_PLACES_API")
    if key is None:
        logger.error("FOURSQUARE_PLACES_API not found. Set it as environment variable")
        exit(1)

    url = "https://api.foursquare.com/v3/places/search?"
    params = {
        "near": city,
        "query": category + " " + subcategory,
        "sort": sort,
        "categories": category_id if category_id is not None else "",
        "limit": 50,
        "fields": "fsq_id,name,location,related_places,description,rating,popularity,price,tastes,tips,geocodes,photos"
    }
    if ll is not None:
        params.update({
            'll': ll[0] + "," + ll[1],
            'radius': 1000,
            'sort': 'distance'
        })
    headers = {
        "Accept": "application/json",
        "Authorization": key,
    }
    url += urllib.parse.urlencode(params)
    if os.path.exists(data_file_path) and use_old_search:
        with open(data_file_path) as json_file:
            data = json.load(json_file)
    else:
        response = requests.request("GET", url, headers=headers)
        logger.debug(f"FOURSQUARE RESPONSE STATUS: {response.status_code}")
        data = response.json()
        with open(data_file_path, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)

    logger.debug(f"BEFORE FILTERING - Number of results retrieved by FSQ: {len(data['results'])}")
    keep_idx = [idx if res['fsq_id'] not in exclude_fsq_ids else -1 for idx, res in enumerate(data['results'])]
    keep_idx = list(filter(lambda x: x != -1, keep_idx))
    data['results'] = np.array(data['results'])[keep_idx]
    logger.debug(f"AFTER FILTERING - Number of results retrieved by FSQ: {len(data['results'])}")
    logger.debug(f"Filtered FSQ pois: {exclude_fsq_ids}")
    if 'results' not in data.keys() or len(data['results']) == 0:
        logger.error("FOURSQUARE DID NOT PROVIDE ANY RESULT")
        return None, None
    else:
        data_w_neig = list(filter(lambda x:
                                  ('neighborhood' in x['location'].keys())
                                  and
                                  (len(x['location']['neighborhood']) > 0),
                                  data['results']))
        if len(data_w_neig) == 0:
            has_neighborhood = False
            logger.debug("FOURSQUARE PLACES API DID NOT RETURN ANY PLACE WITH NEIGHBORHOOD INFORMATION")
            data = data['results']
        else:
            has_neighborhood = True
            data = data_w_neig
        data_w_desc = list(filter(lambda x:
                                  ('description' in x.keys())
                                  and
                                  (x['description'] is not None)
                                  and
                                  (x['description'].strip() != ''),
                                  data))
        if len(data_w_desc) == 0:
            has_description = False
            results = data
            logger.debug("FOURSQUARE PLACES API DID NOT RETURN ANY PLACE WITH DESCRIPTION")
        else:
            has_description = True
            results = data_w_desc
        # idx = random.randint(0, len(results) - 1)
        # name = results[idx]['name']
        # description = None if has_description else \
        #     results[idx]['description']
        # neighborhood = results[idx]['location']['neighborhood'] if \
        #     'neighborhood' in data['results'][idx]['location'].keys() \
        #     and \
        #     len(data['results'][idx]['location']['neighborhood'])>0 else None
    return results[0], has_description


def get_utterance(city, name, category, neighborhood, description, has_description):
    file_name = ".\\data\\utterances_action_search_POI.json"
    with open(file_name, "r") as fp:
        data = json.load(fp)
        app = data['with_description'] if has_description else data['without_description']
        utterances = app['with_neigh'] if neighborhood is not None else app['without_neigh']
    idx = random.randint(0, len(utterances) - 1)
    sorted_fields = []
    field_map_value = {
        'city': city,
        'name': name,
        'category': category,
        'neighborhood': neighborhood,
        'description': description
    }
    for idx_field, field in enumerate(utterances[idx]):
        if field not in field_map_value.keys():
            continue
        current_field_value = field_map_value[field]
        sorted_fields.append(current_field_value)

    return utterances[idx][-1].format(*sorted_fields)


def get_neighborhood(place_info, api='FOURSQUARE'):
    if api=='GOOGLE':
        app = list(filter(lambda x: 'locality' in x['types'], place_info['address_components']))
        if len(app) == 0:
            neighborhood = None
        else:
            neighborhood = app[0]
        return neighborhood
    else:
        neighborhood = place_info['location']['neighborhood'] if \
            'neighborhood' in place_info['location'].keys() \
            and \
            len(place_info['location']['neighborhood']) > 0 else None
        return neighborhood[0] if isinstance(neighborhood, list) else neighborhood


def get_description(place_info, has_description):
    if not has_description:
        return None
    description = place_info['description']
    end_sentence = [i for i, ch in enumerate(description) if ch == '.']
    last_char_idx = end_sentence[1] if len(end_sentence) > 1 else -1
    description = description[:last_char_idx]
    lang_desc = detect(description)
    logger.debug(f"Description written in {lang_desc}")
    if lang_desc != 'en':
        logger.debug("The description is going to be translated in english")
        # logger.debug(f"Original description: \n \t{description}")
        description = GoogleTranslator(source=lang_desc, target='en').translate(description)
        logger.debug(f"Translated description: \n \t{description}")
    return description


def get_photo_url(place_info):
    if 'photos' not in place_info.keys() or len(place_info['photos']) == 0:
        logger.debug("The current place does not contain any photo")
        return None
    prefix = place_info['photos'][0]['prefix']
    suffix = place_info['photos'][0]['suffix']
    return prefix + "original" + suffix


# class ActionRememberCity(Action):
#     def name(self) -> Text:
#         return "action_remember_city"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#
#         # retrieve entity values
#         current_city = next(tracker.get_latest_entity_values('city'), None)
#
#        # display a feedback (randomized between 2 sentences)
#         rand = random.random()
#         if rand > 0.5:
#             msg = f"Nice choice! I would like to ask you more about what you want to visit in {current_city}  🤔"
#         else:
#             msg = f'{current_city} , nice one! First I need to ask you more info  🤔 '
#
#         dispatcher.utter_message(text=msg)
#
#         # we save the city in a slot
#         return [SlotSet("city",current_city)]
