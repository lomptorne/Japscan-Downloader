import os 
import sys
import requests 
import psutil
import time
import csv 
import inquirer
import pandas as pd 
import string

from bs4 import *
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from browsermobproxy import Server
from tqdm import tqdm

class japscan_downloader:

	def __init__(self):
		pass

	def builder(self) :

		# Set the basics variables 
		base_url ="https://www.japscan.co"
		chap_returns = []
		self.urls_list = []
		name_results = []
		chap_results = []
		url_n = {"name" : "url"}
		url_c = {"chapter" : "url"}
		no_result = True
		search_results = []

		while( len(search_results) < 1 ) : 

			# Get the input from the user and convert it into a lowercase string
			search = input("Enter the manga title : ")
			str(search)
			search = search.lower()
			search = search.replace(" ", "-")
			
			# Query the link csv file to check for results 
			df = pd.read_csv('urls.csv')
			df_tolist= df[df['0'].str.contains(search)]
			search_results = df_tolist.values.tolist()

			if len(search_results) < 1 :
				print("No result")

		# add all the searchs results and excrat the name from the url 
		for search_result in search_results :

			name = search_result[0]
			name = name.split("/")[2]
			name = name.replace("-", " ")
			name = string.capwords(name)
			name_results.append(name)
			url_n[name] = '{}'.format(search_result)

		# Promt user to choose a manga
		questions = [
		  				inquirer.List('result',
		                message="Choose a result",
		                choices= name_results,
		            ),
		]
		answer = inquirer.prompt(questions)
		self.manga_name = answer["result"]
		end_url = url_n["{}".format(self.manga_name)]
		end_url = end_url.replace("[", "").replace("]","").replace("'", "")

		# Add the manga to the url 
		manga_url = base_url + end_url
		
		# Set the soup 
		page = requests.get(manga_url)
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
				url_c[name] = '{}'.format(chap_return)

		# Ask the user for the Chapter/Volume
		try :
			questions = [
							inquirer.List('chapter',
							message= "Choose a chapter",
							choices= chap_results,
							),
			]
			answer = inquirer.prompt(questions)
			self.chapter_name = answer["chapter"]
			chap_url = url_c["{}".format(answer["chapter"])]
			chap_url = chap_url.replace("[", "").replace("]","").replace("'", "")

		except :
			print("Error chapter")
			sys.exit()

		# Make the chapter/volume url
		basic_url = str(base_url + chap_url)
		
		
		# Update the soup 
		page = requests.get(basic_url)
		soup = BeautifulSoup(page.content, "html.parser")
		
		# Get the last page of the chapter
		last_page = soup.find('select', attrs={'id': 'pages'}).find_all('option')[-1].get_text()
		
		# Isolate the page number to an int
		pages_number = [int(word) for word in last_page.split() if word.isdigit()][0]

		# Build all the urls depending on the number of pages
		for i in range(pages_number) :

			if i == 0:

				self.urls_list.append(str(basic_url + str(i) + ".html"))

			at_page = str(i+ 1) 

			self.urls_list.append(str(basic_url + at_page + ".html"))
		
		# Return a list with all the chapter/volume urls
		return 

	def worker(self):

		# Set basic var for the function
		self.urls_down = []
		network_events = []
		URLS=self.urls_list 
		page_nbr =len(self.urls_list) -1
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

							self.urls_down.append(match)

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

								self.urls_down.append(match)

				break

			except TimeoutException as ex:
				print("Timeout, retry" + str(ex))
				driver.quit()
				continue

		# Remove duplicate		
		self.urls_down = list(dict.fromkeys(self.urls_down))

		# Stop the server and the driver
		server.stop()
		driver.quit()
		
		# Return image url list 
		return 

	def downloader(self):
		
		URLS = self.urls_down
		path = os.getcwd()
		count = 0
		dir_name = path + "/Mangas/" + self.manga_name + "/" + self.chapter_name
		
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

	def killer(self):

		for proc in psutil.process_iter():
			if proc.name() == "browsermob-proxy":
				proc.kill()
				
		for proc in psutil.process_iter():
			if proc.name() == "java":
				proc.kill()
		return 

if __name__ == "__main__":

	run = japscan_downloader()
	run.killer()
	run.builder()
	run.worker()
	run.killer()
	run.downloader()
