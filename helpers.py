import os 
import sys
import requests 
import psutil
import time
import csv 
import inquirer
import pandas as pd 
import string
import collections

from bs4 import *
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from browsermobproxy import Server
from tqdm import tqdm


def search(search_request):
	
	# Set the basics variables 
	search_results = []
	mangas = {}

	# Get the input from the user and convert it into a lowercase string
	search = str(search_request)
	search = search.lower()
	search = search.replace(" ", "-")

	if search is "":
		return None

	# Query the link csv file to check for results 
	df = pd.read_csv('urls.csv')
	df_tolist= df[df['0'].str.contains(search)]
	search_results = df_tolist.values.tolist()

	if len(search_results) < 1 :
	 return None

	for search_result in search_results :

		# Extract the name in the url
		name = search_result[0]
		name = name.split("/")[2]
		name = name.replace("-", " ")
		name = string.capwords(name)
		
		# Set a dict with name and url 
		mangas[name] = []
		mangas[name].append(search_result[0])
		mangas = collections.OrderedDict(sorted(mangas.items()))

	# return the dict with mangas and urls 	
	return mangas

def chapters(name_manga, url_manga) :

	url_base ="https://www.japscan.co"
	url_short = url_base + url_manga
	chap_returns = []
	chap_results = []
	chapters = {}
	# Set the soup 
	page = requests.get(url_short)
	soup = BeautifulSoup(page.content, 'html.parser')

	# Collect Urls from the correct element on the page 
	for div in soup.find_all('div', attrs={'id': 'chapters_list'}):

		for a in div.find_all('a', href=True):
					chap_returns.append(a['href'])

		for chap_return in chap_returns :
				name = chap_return.split("/")[3]
				name = name.replace("-", " ")
				name = string.capwords(name)
				chap_results.append(name)
				chapters[name] = []
				chapters[name].append(chap_return)
		
	return chapters

def urlMaker(url_manga, url_chapter) :

	url_base ="https://www.japscan.co"
	url_semi = url_base + url_chapter
	urls_list = []
	
	page = requests.get(url_semi)
	soup = BeautifulSoup(page.content, "html.parser")

	# Get the last page of the chapter
	last_page = soup.find('select', attrs={'id': 'pages'}).find_all('option')[-1].get_text()
	
	# Isolate the page number to an int
	pages_number = [int(word) for word in last_page.split() if word.isdigit()][0]

	# Build all the urls depending on the number of pages
	for i in range(pages_number) :

		if i == 0:

			urls_list.append(str(url_semi + str(i) + ".html"))

		at_page = str(i+ 1) 

		urls_list.append(str(url_semi + at_page + ".html"))
	
	# Return a list with all the chapter/volume urls
	return urls_list
def downloader(urls):
	# Set basic var for the function
	urls_list = []
	network_events = []
	URLS=urls
	page_nbr =len(urls) - 1
	path = os.getcwd()
	# Browsermob binaries location
	browsermobproxy_location = "{}/browsermob/browsermob-proxy".format(path) 
	
	# Start browsermob server
	print("Proxy init...")
	server = Server(browsermobproxy_location)
	server.start()
	time.sleep(1)
	proxy = server.create_proxy()
	time.sleep(1)

	# Set option for the webdriver, automation detection from japscan, certificate, and headless 
	chrome_path = "{}/chromedriver".format(path)
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_experimental_option("useAutomationExtension", False)
	chrome_options.add_experimental_option("excludeSwitches",["enable-automation"])
	chrome_options.set_capability("acceptInsecureCerts", True)        
	chrome_options.add_argument("--log-level=3")
	chrome_options.add_argument('--proxy-server=%s' % proxy.proxy)
	chrome_options.add_argument("--disable-blink-features")
	chrome_options.add_argument("--disable-blink-features=AutomationControlled")
	chrome_options.add_argument("--headless")  
	caps = DesiredCapabilities.CHROME
	driver = webdriver.Chrome(chrome_path, desired_capabilities=caps, options=chrome_options)
	print("Driver init...")

	# Do a while loop in case of timeout it happen sometimes 
	while True:

		print("Fetch :")
		try:
			# Initiate the driver with low consumption website
			driver.set_page_load_timeout(30)
			driver.get('http://perdu.com/')
			
			# if the page number is even scrap only even page, since we can scrap the current page and the next page it's shorter
			if page_nbr % 2 == 0 :
				
				for URL in tqdm(URLS[::2]) :
					network_events = []
					proxy.new_har("urls")
					driver.get(URL)
					
					# Get the page logs
					entries = proxy.har['log']["entries"]
					for entry in entries:
					    if 'request' in entry.keys():
					        network_events.append(entry['request']['url'])
					
					# Extract only the imges 
					matches = [s for s in network_events if ".jpg" in s and  "japscan.co" in s or ".png" in s and "japscan.co" in s]
					matches = [ x for x in matches if "bg." not in x ]
					
					# Add images Urls to a list
					for match in matches :

						urls_list.append(match)

			# Same operation if page number is odd 
			if page_nbr % 2 != 0 :
					
					for URL in tqdm(URLS[1::2]) :
						network_events = []
						proxy.new_har("urls")
						driver.get(URL)

						entries = proxy.har['log']["entries"]
						for entry in entries:
						    if 'request' in entry.keys():
						        network_events.append(entry['request']['url'])
						
						matches = [s for s in network_events if ".jpg" in s and  "japscan.co" in s or ".png" in s and "japscan.co" in s]
						matches = [ x for x in matches if "bg." not in x ]

						for match in matches :

							urls_list.append(match)

			break

		except TimeoutException as ex:
			print("Timeout, retry" + str(ex))
			driver.quit()
			continue

	# Remove duplicate		
	urls_list = list(dict.fromkeys(urls_list))

	# Stop the server and the driver
	server.stop()
	driver.quit()
	
	# Return image url list 
	return urls_list

def saver(urls_list, name_manga, name_chapter):

	URLS = urls_list
	path = os.getcwd()
	count = 0
	dir_name = path + "/Mangas/" + name_manga + "/" + name_chapter
	
	# Create the folder 
	try :
		os.makedirs(dir_name)
		os.chdir(dir_name)
	except :
		print("Folder already exist")
		os.chdir(dir_name)
	print("Download :")

	# Downloading all the fetched urls 		
	for URL in tqdm(URLS) :
		
		count += 1
		response = requests.get(URL)

		try :

			file = open("{}.png".format(count), "wb")			
			file.write(response.content)
			file.close()
		except : 
			print("File already exist")
	
	os.chdir(path)

	return print("Done !")

def killer():

	for proc in psutil.process_iter():
		if proc.name() == "browsermob-proxy":
			proc.kill()
			
	for proc in psutil.process_iter():
		if proc.name() == "java":
			proc.kill()
	return 