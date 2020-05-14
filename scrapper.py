import os 
import sys
import csv
import requests
from time import sleep

from bs4 import *


import pandas as pd 

# Set the basics variable for the scrapper
baseurls = []
url_loop = 0

# Loop through the manga index
while(True):
	try :
		
		# Loop incrementation 
		if url_loop == 0:
			URL = "https://www.japscan.co/mangas/1"
		else:
			URL = "https://www.japscan.co/mangas/{}".format(url_loop)

		# Set the soup 
		page = requests.get(URL)
		soup = BeautifulSoup(page.content, 'html.parser')

		# Set the breakpoint at the url redirection on end 
		if page.status_code != 200:
			break
		elif page.url == "https://www.japscan.co/mangas/":
			break

		# Collect Urls from the correct element on the page 
		for div in soup.find_all('div', attrs={'class': 'd-flex flex-wrap'}):

			for a in div.find_all('a', href=True):
				
				# Add the urls to the list
				baseurls.append(a['href'])

			# Remove Duplicate from the URl list 
			baseurls = list(set(baseurls))
			

		# Progress
		print("Page %d Scrapped." % (url_loop))
		#Increment the url
		url_loop += 1

	except :
		break

# Convert the urls list into a csv file 
df = pd.DataFrame(baseurls)
df.to_csv('urls.csv', index=False)


