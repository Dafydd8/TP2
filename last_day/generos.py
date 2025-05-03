#BUSQUEDA AUTOMATICA DE GENEROS DE ALBUMES EN GOOGLE

from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
import time
import csv


def get_rta_1(driver):
    class_names = ["FozYP", "FLP8od", "IZ6rdc"]
    estilos = []
    for class_name in class_names:
        try:
            estilos = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, class_name)))
            break
        except:
            continue
    rv = []
    for estilo in estilos:
        rv.append(estilo.text)
    return rv
        
def buscar(driver, busqueda):
    driver.get("https://www.google.com")
    search_box = driver.find_element("name", "q")
    search_box.send_keys(busqueda)
    search_box.send_keys(Keys.ENTER)
