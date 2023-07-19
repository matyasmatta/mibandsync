from os import link
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup #pip install beautifulsoup4
import PySimpleGUI as sg
import tkinter as tk
from tkinter import ttk
import sv_ttk
import csv
from tkinter import *
import tkinter.ttk as ttk
import csv
from datetime import datetime
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def kindle():
    # create runtime window
    options = Options()
    options.headless = False
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--allow-mixed-content")

    # since v0.0.2 no longer necessary to pass in chromedrive location, now it will install on its own! (about 8 MiB so no worries)
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except:
        tk.messagebox.showerror(title="Chrome version incompatible", message="Your version of Chrome might not be up-to-date, please visit Chrome settings to update.", **options)

    driver.get("https://www.amazon.com/kindle/reading/ap/insights")

kindle()

