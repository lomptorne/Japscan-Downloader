import sys
import os
import time 
import traceback

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from helpers import search, chapters, urlMaker, killer, downloader, saver

# Set some signlas from the worker for later 
class WorkerSignals(QObject):

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

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
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  
        finally:
            self.signals.finished.emit()  


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
		self.label_progress.setText("Download : ")

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
		self.list_manga.itemActivated.connect(self.function_chapter)
		self.list_chapter.clicked.connect(self.builder)
		self.btn_download.clicked.connect(self.launcher)
		self.btn_download.setEnabled(False)

	# Function searching mangas in the urls list and returning them to list element 
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

	# searching for the chapter of each manga with beuatifulsoup
	def function_chapter(self):
		
		self.list_chapter.clear()
		self.name_manga = self.list_manga.currentItem().text()
		self.url_manga = self.search_results["{}".format(self.name_manga)][0]
		self.request_chapters = chapters(self.name_manga, self.url_manga)
		list_tmp = [ values for values in self.request_chapters.keys() ]

		for list_item in reversed(list_tmp) :
			self.list_chapter.addItem(list_item)

	# Building the complete urls list for the downloader 
	def function_url(self, progress_callback):
		self.name_chapter = self.list_chapter.currentItem().text()
		self.label_progress.setText("Download : {} {}".format(self.name_manga, self.name_chapter))
		self.url_chapter = self.request_chapters["{}".format(self.name_chapter)][0]
		self.urls = urlMaker(self.url_manga, self.url_chapter)
		self.btn_download.setEnabled(True)

	# fetching and downloading all the page with selenium browsermob and beautifulsoup
	def function_downloader(self, progress_callback):

		self.list_chapter.setEnabled(False)
		self.list_manga.setEnabled(False)
		self.btn_download.setEnabled(False)
		self.btn_search.setEnabled(False)
		self.bar_progress.setRange(0,0)
		self.label_progress.setText('Fetching... (It may take some time...)')

		killer()
		urls_list = downloader(self.urls)
		killer()

		self.label_progress.setText('Downloading...')
		saver(urls_list, self.name_manga, self.name_chapter)

		self.label_progress.setText(None)
		self.bar_progress.setRange(0, 1)
		self.btn_search.setEnabled(True)
		self.list_chapter.setEnabled(True)
		self.list_manga.setEnabled(True)

	# Multithread caller for the url builder
	def builder(self):
		
		worker = Worker(self.function_url)
		self.threadpool.start(worker)

	# Multi thread caller for the downloader
	def launcher(self):
		worker = Worker(self.function_downloader)
		self.threadpool.start(worker) 
		self.btn_download.setEnabled(False)

if __name__ == '__main__':

    app = QApplication([])
    ex = Windows()
    sys.exit(app.exec_())
    