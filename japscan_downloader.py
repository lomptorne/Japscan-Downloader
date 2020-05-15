import sys
import os
import time 
import traceback

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from helpers import search, chapters, urlMaker, killer, downloader, saver
from bs4 import *
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from browsermobproxy import Server
from tqdm import tqdm
class WorkerSignals(QObject):

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

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
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

# Init the main windows
class Windows(QWidget):

	def __init__(self):

		super().__init__()
		self.initUI()


	def initUI(self):
		self.step = 0
		# Set the labels elements
		label_input = QLabel()
		label_manga = QLabel()
		label_chapter = QLabel()
		label_progress = QLabel()
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
		box_main.addLayout(box_button)

		# Set the windows 
		self.setLayout(box_main)
		self.setGeometry(500, 300, 300, 200)
		self.setWindowTitle('Japscan Downloader')
		self.show()

		#Set the buttons and their action
		btn_exit.clicked.connect(self.close)
		self.btn_search.clicked.connect(self.function_search)
		self.list_manga.itemClicked.connect(self.function_chapter)
		self.list_chapter.itemClicked.connect(self.builder)
		self.btn_download.clicked.connect(self.launcher)
		self.btn_download.setEnabled(False)



	# When convert button is clicked call the convert function
	def function_search(self):

		self.list_manga.clear()
		self.list_chapter.clear()
		request_search = self.input_search.text()
		self.search_results = search(request_search)
		
		if self.search_results != None :
			for search_result in self.search_results :
				self.list_manga.addItem(search_result)
		else:
			self.list_manga.addItem("No Results")

	def function_chapter(self):
		
		self.list_chapter.clear()
		self.name_manga = self.list_manga.currentItem().text()
		self.url_manga = self.search_results["{}".format(self.name_manga)][0]
		self.request_chapters = chapters(self.name_manga, self.url_manga)
		
		for request_chapter in self.request_chapters :
			self.list_chapter.addItem(request_chapter)
		
	def function_url(self, progress_callback):
		
		self.name_chapter = self.list_chapter.currentItem().text()
		self.url_chapter = self.request_chapters["{}".format(self.name_chapter)][0]
		self.urls = urlMaker(self.url_manga, self.url_chapter)
		self.btn_download.setEnabled(True)	
		
	def function_downloader(self, progress_callback):

		self.list_chapter.setEnabled(False)
		self.list_manga.setEnabled(False)
		self.btn_download.setEnabled(False)
		self.btn_search.setEnabled(False)
		
		self.bar_progress.setRange(0,0)

		killer()
		urls_list = downloader(self.urls)
		killer()

		saver(urls_list, self.name_manga, self.name_chapter)

		self.bar_progress.setRange(0, 1)

		self.btn_search.setEnabled(True)
		self.btn_download.setEnabled(True)
		self.list_chapter.setEnabled(True)
		self.list_manga.setEnabled(True)

	def builder(self):
		worker = Worker(self.function_url)
		
		self.threadpool.start(worker)
		

	def launcher(self):
		worker = Worker(self.function_downloader)
		self.threadpool.start(worker) 

if __name__ == '__main__':

    app = QApplication([])
    ex = Windows()
    sys.exit(app.exec_())

