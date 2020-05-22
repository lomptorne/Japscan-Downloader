import sys
import os
import time 
import traceback
import pandas as pd 
import string
import collections
import requests
import psutil
from pathlib import Path, PureWindowsPath

from bs4 import * 
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from browsermobproxy import Server

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# Set some signlas from the worker for later 
class WorkerSignals(QObject):

	start = pyqtSignal()
	finished = pyqtSignal()
	error = pyqtSignal(tuple)
	result = pyqtSignal(object)
	progress = pyqtSignal(str, int, int)

# Set the worker for multi-threading 
class Worker(QRunnable):

	def __init__(self, fn, *args, **kwargs):
		super(Worker, self).__init__()

		# Store constructor arguments (re-used for processing)
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignals()    

		# Add the callback to our kwargs
		self.kwargs['progress_callback'] = self.signals.progress        

	@pyqtSlot()
	def run(self):
         
		try:
			self.signals.start.emit()
			result = self.fn(*self.args, **self.kwargs)
		except:
			traceback.print_exc()
			exctype, value = sys.exc_info()[:2]
			self.signals.error.emit((exctype, value, traceback.format_exc()))
		else:
			self.signals.result.emit(result)  
		finally:
			self.signals.finished.emit()  

# Main QTWindows
class Windows(QWidget):

	def __init__(self):

		super().__init__()
		self.initUI()

	def initUI(self):
		
		# Set the labels elements
		label_input = QLabel()
		label_manga = QLabel()
		label_chapter = QLabel()
		self.label_progress = QLabel()
		label_input.setText("Mangas Search :")
		label_manga.setText("Mangas :")
		label_chapter.setText("Chapters :")
		

		# Set the buttons elements
		self.btn_download = QPushButton("Download")
		btn_exit = QPushButton("Exit")
		self.btn_search = QPushButton("Search")

		# Set the lists elements
		self.list_manga = QListWidget()
		self.list_chapter = QListWidget()
		
		# Set the searchbar
		self.input_search = QLineEdit(self)

		# Set the progress bar
		self.bar_progress = QProgressBar(self)
		self.bar_progress.setGeometry(30, 40, 200, 25)
		self.bar_progress.setAlignment(Qt.AlignCenter)

		# Set the threadpool
		self.threadpool = QThreadPool()
		self.threadpool.setMaxThreadCount(1)
		
		# Set the list layouts
		box_list_m = QHBoxLayout()
		box_list_m.setAlignment(Qt.AlignCenter)
		box_list_v1 = QVBoxLayout()
		box_list_v2 = QVBoxLayout()
		box_list_v1.addWidget(label_manga)
		box_list_v1.addWidget(self.list_manga)
		box_list_v2.addWidget(label_chapter)
		box_list_v2.addWidget(self.list_chapter)
		box_list_m.addLayout(box_list_v1)
		box_list_m.addLayout(box_list_v2)
		
		# Set the search box
		box_search_m = QVBoxLayout()
		box_search_h = QHBoxLayout()
		box_search_h.addWidget(self.input_search)
		box_search_h.addWidget(self.btn_search)
		box_search_m.addWidget(label_input)
		box_search_m.addLayout(box_search_h)

		# Set the bottom buttons layout
		box_button = QHBoxLayout()
		box_button.addWidget(self.btn_download)
		box_button.addWidget(btn_exit)

		# Set the main windows box 
		box_main = QVBoxLayout()
		box_main.addLayout(box_search_m)
		box_main.addLayout(box_list_m)
		box_main.addWidget(self.bar_progress)
		box_main.addWidget(self.label_progress)
		box_main.addLayout(box_button)

		# Set the windows 
		self.setLayout(box_main)
		self.setGeometry(300, 300, 500, 400)
		self.setWindowTitle('Japscan Downloader')
		self.show()

		#Set the buttons and their action
		btn_exit.clicked.connect(self.close)
		self.btn_search.clicked.connect(self.function_search)
		self.list_manga.clicked.connect(self.function_chapter)
		self.list_chapter.clicked.connect(self.enabler)
		self.btn_download.clicked.connect(self.launcher)
		self.btn_download.setEnabled(False)

	# Function searching mangas in the urls list and returning them to list element 
	def function_search(self):

		# Clear chapter and manga list
		self.list_manga.clear()
		self.list_chapter.clear()

		# Set the request var 
		request_search = self.input_search.text()

		#self.search_results = search(request_search)
		# Set the basics variables 
		search_results = []
		self.mangas = {}

		# Get the input from the user and convert it into a lowercase string
		search = str(request_search)
		search = search.lower()
		search = search.replace(" ", "-")

		if search is "":
			return self.list_manga.addItem("No Results")

		# Query the link csv file to check for results 
		df = pd.read_csv('urls.csv')
		df_tolist= df[df['0'].str.contains(search)]
		search_results = df_tolist.values.tolist()

		if len(search_results) < 1 :
		 return self.list_manga.addItem("No Results")

		for search_result in search_results :

			# Extract the name in the url
			name = search_result[0]
			name = name.split("/")[2]
			name = name.replace("-", " ")
			name = string.capwords(name)
			
			# Set a dict with name and url 
			self.mangas[name] = []
			self.mangas[name].append(search_result[0])
			self.mangas = collections.OrderedDict(sorted(self.mangas.items()))
			
		if self.mangas != None :
			for manga in self.mangas :
				self.list_manga.addItem(manga)
		else:
			self.list_manga.addItem("No Results")

	# searching for the chapter of each manga with beuatifulsoup
	def function_chapter(self):
		
		# Clear chapter list
		self.list_chapter.clear()

		self.name_manga = self.list_manga.currentItem().text()
		self.url_manga = self.mangas["{}".format(self.name_manga)][0]
		#self.request_chapters = chapters(self.name_manga, self.url_manga)

		url = "https://www.japscan.co" + self.url_manga
		chap_returns = []
		chap_results = []
		self.chapters = {}

		# Set the soup 
		page = requests.get(url)
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
					self.chapters[name] = []
					self.chapters[name].append(chap_return)

		# Reverse order the list
		list_tmp = [ values for values in self.chapters.keys() ]

		for list_item in reversed(list_tmp) :
			self.list_chapter.addItem(list_item)

	# Building the complete urls list for the downloader 
	def function_url(self, progress_callback):

		self.name_chapter = self.list_chapter.currentItem().text()

		url_chapter = self.chapters["{}".format(self.name_chapter)][0]

		url_semi = "https://www.japscan.co" + url_chapter
		self.urls_list = []
		
		# Set the soup 
		page = requests.get(url_semi)
		soup = BeautifulSoup(page.content, "html.parser")

		# Get the last page of the chapter
		last_page = soup.find('select', attrs={'id': 'pages'}).find_all('option')[-1].get_text()
		
		# Isolate the page number to an int
		pages_number = [int(word) for word in last_page.split() if word.isdigit()][0]

		# Build all the urls depending on the number of pages
		for i in range(pages_number) :

			if i == 0:

				self.urls_list.append(str(url_semi + str(i) + ".html"))

			at_page = str(i+ 1) 

			self.urls_list.append(str(url_semi + at_page + ".html"))

		self.btn_download.setEnabled(True)

	# fetching and downloading all the page with selenium browsermob and beautifulsoup
	def function_downloader(self, progress_callback):

		# Set basic var for the function
		urls_list = []
		network_events = []
		URLS= self.urls_list
		page_nbr =len(URLS) - 1
		path = os.getcwd()
		counter_urls = 0
		counter_pages = 0
		path_proxy = "{}/browsermob/bin/browsermob-proxy".format(path) 
		path_driver = "{}/chromedriver".format(path)
		dir_name = Path("{}/Mangas/{}/{}".format(path, self.name_manga, self.name_chapter))

		# Dapt the path for windows
		if os.name == 'nt':
			dir_name = PureWindowsPath(dir_name)
			path_proxy = r"{}\browsermob\bin\browsermob-proxy".format(path) 
			path_driver = r"{}\chromedriver.exe".format(path)
		
		# Start browsermob server
		server = Server(path_proxy)
		server.start()
		time.sleep(1)
		proxy = server.create_proxy()
		time.sleep(1)

		# Set option for the webdriver, automation detection from japscan, certificate, and headless 
		chrome_path = path_driver
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
		
		# Do a while loop in case of timeout it happen sometimes 
		while True:

			try:
				# Initiate the driver with low consumption website
				driver.set_page_load_timeout(30)
				driver.get('http://perdu.com/')
				
				# if the page number is even scrap only even page, since we can scrap the current page and the next page it's shorter
				if page_nbr % 2 == 0 :
					
					for URL in URLS[::2] :

						# Set defaults var
						network_events = []
						proxy.new_har("urls")
						driver.get(URL)
						
						# Progressbar signal
						bar_length = len(URLS)
						progress_callback.emit("Fetching Urls ", counter_urls, bar_length)
						
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

						counter_urls += 2 


				# Same operation if page number is odd 
				if page_nbr % 2 != 0 :
						
						for URL in URLS[1::2] :
							network_events = []
							proxy.new_har("urls")
							driver.get(URL)

							# Progressbar signal
							bar_length = len(URLS)
							progress_callback.emit("Fetching Urls ", counter_urls, bar_length)

							entries = proxy.har['log']["entries"]
							for entry in entries:
							    if 'request' in entry.keys():
							        network_events.append(entry['request']['url'])
							
							matches = [s for s in network_events if ".jpg" in s and  "japscan.co" in s or ".png" in s and "japscan.co" in s]
							matches = [ x for x in matches if "bg." not in x ]

							for match in matches :

								urls_list.append(match)

							counter_urls += 2 

				break

			except TimeoutException as ex:
				print("Timeout, retry" + str(ex))
				driver.quit()
				pass

		# Remove duplicate		
		urls_list = list(dict.fromkeys(urls_list))

		# Stop the server and the driver
		server.stop()
		driver.quit()
	
		# Set pages URLS
		URLS = urls_list
		
		# Create the folder 
		try:
			os.makedirs(dir_name)
			os.chdir(dir_name)
		except OSError:
			os.chdir(dir_name)
			
		# Downloading all the fetched urls 		
		for URL in URLS :

			# Progressbar signal
			bar_length = len(URLS)
			progress_callback.emit("Fetching Urls ", counter_pages, bar_length)
			counter_pages += 1
			response = requests.get(URL)

			try:
				file = open("{}.png".format(counter_pages), "wb")			
				file.write(response.content)
				file.close()
			except :
				continue

		os.chdir(path)

	# Killing shitty process that browsermob left behind
	def killer(self, progress_callback):
		
		# kill brosermob leftover prov
		for proc in psutil.process_iter():
			if proc.name() == "browsermob-proxy":
				proc.kill()

		# kill java leftover proc
		for proc in psutil.process_iter():
			if proc.name() == "java":
				proc.kill()
		return 

	# Enable download button when everything is checked
	def enabler(self):

		self.btn_download.setEnabled(True)

	# Multi thread caller for the downloader
	def launcher(self, progress_callback):

		# Set the workers
		worker = Worker(self.function_downloader)
		worker_second = Worker(self.function_url)
		worker_third = Worker(self.killer)

		# Set the threads 
		self.threadpool.start(worker_second)

		if os.name != 'nt':
			self.threadpool.start(worker_third)

		self.threadpool.start(worker) 

		if os.name != 'nt':
			self.threadpool.start(worker_third)

		# Set the signals 
		worker.signals.start.connect(self.function_start)
		worker.signals.progress.connect(self.function_progress)
		worker.signals.result.connect(self.function_return)
		worker.signals.finished.connect(self.function_end)

		self.btn_download.setEnabled(False)

	# Event on the start of the main function
	def function_start(self):

		# Block the buttons and lists 
		self.list_chapter.setEnabled(False)
		self.list_manga.setEnabled(False)
		self.btn_download.setEnabled(False)
		self.btn_search.setEnabled(False)

		# Set the progress bar to infinite
		self.bar_progress.setRange(0,0)
		self.label_progress.setText('Proxy initialization')

	# ProgressBar Events 
	def function_progress(self, title, counter, length):

		# Reset the bar label
		self.label_progress.setText('')

		# Change bar aspect depending on scraper progress
		self.bar_progress.setRange(0, length)
		self.bar_progress.setVisible(True)
		self.bar_progress.setValue(counter)
		self.bar_progress.setFormat("{}: {}/{}".format(title, counter, length))

	# return Value 
	def function_return(self, output):

		print(output)
		
	# Event on the end of the main function 
	def function_end(self):

		self.label_progress.setText(None)
		self.bar_progress.setRange(0, 1)
		self.btn_search.setEnabled(True)
		self.list_chapter.setEnabled(True)
		self.list_manga.setEnabled(True)

if __name__ == '__main__':

    app = QApplication([])
    ex = Windows()
    sys.exit(app.exec_())
    