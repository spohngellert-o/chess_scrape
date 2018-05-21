import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from datetime import timedelta
import re
import os
import sys
import discord
import argparse
import asyncio
import os

parser = argparse.ArgumentParser(description='Input parser')

parser.add_argument('discord_channel', help="ID of the discord channel to post in.")
parser.add_argument('start_location', help="Location to start from for travel calculations.")
args = parser.parse_args()

discord_channel = args.discord_channel
start_location = args.start_location
discord_token = os.getenv('DiscordBotToken')

client = discord.Client()
bad_addr_dict = {'Best Western Royal Plaza Hotel, 181 Boston Post Rd. West, Marlboro, MA': '181 Boston Post Rd W, Marlborough, MA 01752'}
bad_transit_list = ['181 Boston Post Rd W, Marlborough, MA 01752']
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    channel = client.get_channel(discord_channel)
    for info_str in info_strs:
    	await client.send_message(channel, info_str)
    await client.send_message(channel, 'NOTE: This bot is stil in Beta. Time estimates may be incorrect, and there may be bugs. If you think something is wrong, or have any other feedback, please email the creator: ospohngellert@protonmail.com. Thank you.')
    client.logout()
    client.close()
    sys.exit(0)

@client.event
async def on_message(message):
    pass



base_url = 'http://masschess.org/'
bing_maps_key = os.getenv('BingMapsApiKey')
def dateFilter(date):
	as_dt = datetime.strptime(date, '%a, %m/%d/%y')
	return (as_dt - today).days < 7
page = requests.get(base_url)

# Create a BeautifulSoup object
soup = BeautifulSoup(page.text, 'html.parser')

# print(soup)


events = soup.find('table', {'id': 'gvEventsListHome'})
links = [os.path.join(base_url, l['href']) for l in soup.find_all('a', {'id': re.compile('gvEventsListHome.*EventDetails')})]
print(links)
print(len(links))

# print(events)
data = pd.read_html(str(events), skiprows=2, header=0)[0]
data['link'] = links
print(len(data))
# print(data[0])
today = datetime.today()
data_filtered = data[data.Date.map(dateFilter)]
data_filtered = data_filtered[data_filtered['Organizer'].map(lambda x: 'scholastic' not in x.lower() and 'kid' not in x.lower())]
data_filtered = data_filtered[data_filtered['Event Name'].map(lambda x: 'scholastic' not in x.lower() and 'kid' not in x.lower())]
# data_filtered['location'] = data_filtered['Event Name'].map(lambda x: x.split('-')[-1].strip())
locations = []
prices = []
for link in data_filtered.link:
	event_page = requests.get(link)
	# print(link)
	# import sys
	# sys.exit(0)
	# print(event_page.text)
	event_soup = BeautifulSoup(event_page.text, 'html.parser')
	location_ids = ['fmvEventFlyer_lbl_Venue_Name', 'fmvEventFlyer_lbl_Venue_Name_2', 'fmvEventFlyer_lbl_Venue_Street_1', 'fmvEventFlyer_lbl_Venue_Street_2', 'fmvEventFlyer_lbl_Venue_City', 'fmvEventFlyer_lbl_Venue_State', 'fmvEventFlyer_lbl_Venue_Zip']
	
	location_str = ''.join([event_soup.find('span', {'id': x}).text for x in location_ids])
	price_ids = ['fmvEventFlyer_lbl_ENTRY_FEE_ALL', 'fmvEventFlyer_lbl_ENTRY_FEE_SPECIAL']
	price_str = ''.join([event_soup.find('span', {'id': x}).text for x in price_ids])
	print(location_str)
	locations.append(location_str)
	prices.append(price_str)
	

data_filtered['location'] = locations
data_filtered['prices'] = prices

# sys.exit(0)
print(data_filtered)

info_strs = []
for line in data_filtered.iterrows():
	row = line[1]
	loc = bad_addr_dict.get(row['location'], row['location'])
	print(loc)
	url = 'https://dev.virtualearth.net/REST/v1/Routes/transit?key={}&o=json&c=en-US&&errorDetail=true&wp.0={}&wp.1={}&ig=true&ra=routepath,transitStops&du=mi&dt={}&tt=departure&maxSolns=3&rpo=Points'
	url = url.format(bing_maps_key, start_location, loc, datetime.today())
	if loc not in bad_transit_list:
		print(url)
		r = requests.get(url)
		
		transit_data = r.json()
		try:
			estimated_transit_time = transit_data['resourceSets'][0]['resources'][0]['travelDuration']
		except:
			estimated_transit_time = -1
	else:
		estimated_transit_time = -1
	url = 'https://dev.virtualearth.net/REST/v1/Routes?key={}&o=json&c=en-US&&errorDetail=true&wp.0={}&wp.1={}&ig=true&ra=routepath,transitStops&du=mi&dt={}&tt=departure&maxSolns=3&rpo=Points'
	url = url.format(bing_maps_key, start_location, loc, datetime.today())
	r = requests.get(url)
	drive_data = r.json()
	estimated_drive_time = drive_data['resourceSets'][0]['resources'][0]['travelDuration']
	estimated_distance = drive_data['resourceSets'][0]['resources'][0]['travelDistance']
	print("{}, {}, {}".format(estimated_transit_time, estimated_drive_time, estimated_distance))
	info_strs.append('Event: {}, Location: {}, Price (if listed): {}, Estimated drive time: {}, Estimated transit time: {}, Distance: {} miles, link: {}'.format(row['Event Name'].partition('-')[0].strip(), row['location'], row['prices'], timedelta(seconds=estimated_drive_time), timedelta(seconds=estimated_transit_time) if estimated_transit_time > 0 else "Not accessible via public transportation", int(estimated_distance), row['link']))
	
	# sys.exit(0)
print(info_strs)

client.run(discord_token)