import tkinter as tk
from time import sleep
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
import undetected_chromedriver as uc
import json 
from selenium.common.exceptions import StaleElementReferenceException
# from builtins import print


PROMPT_MESSAGE1 = """
Je vais te donner 30 questions. Tu dois bien réfléchir avant de répondre, car la réponse doit impérativement être correcte.

tu dois me renvoyer que la response, sans explication, sans rien d'autre. Tu dois me renvoyer la réponse sous forme de liste python, avec les mots entre guillemets et séparés par des virgules. Par exemple : ["headache", "weakness", "sensitivity", "coordination"].
Tu dois respecter la syntaxe python, et ne pas mettre d'espace entre les virgules et les mots. Tu dois aussi respecter l'ordre des mots dans la question, et ne pas changer la syntaxe de la question.
si les proposition sont dans la question, tu dois les mettre dans la réponse, sans rien rajouter.
si la list des propositions eguale a n, tu dois mettre n réponses dans ta réponse, sinon si il n'ya pas des propositions, tu dois mettre n réponses ou moins dans ta réponse.
les majuscule restent majuscule, et les minuscules restent minuscules.


Les questions seront du type suivant :

Question 01:
Remplis les blancs avec les mots suivants : coordination, headache, weakness, sensitivity.
Les symptômes neurologiques peuvent inclure toutes les formes de douleur, y compris la 'blank', les douleurs dorsales, la 'blank' musculaire et la 'blank' cutanée, un manque de 'blank', etc.
Propositions :
["coordination", "headache", "weakness", "sensitivity"]
Réponse attendue :
["headache", "weakness", "sensitivity", "coordination"]

Question 02:
When a bag is missing, an airline agent invites the passenger to the Baggage Service Office to file a report.

True
False
Réponse attendue :
["True"]

Question 03: 
Place the words in the correct order to form a sentence:
Propositions:
["your audience","you need to","eager to follow","yourself in a","way, and make","introduce","the tour","very engaging"]

Réponse attendue :
["you need to", "introduce", "yourself in a", "way, and make", "the tour", "very engaging", "your audience", "eager to follow"]
Réponse deteter (à éviter) :
["You need to introduce yourself in a way, and make the tour very engaging for your audience, eager to follow."]
(mets pas tout dans une phrase, mais mets les mots dans le bon ordre, sans rien rajouter)

Question 04: 
Match the beginnings of the sentences with their endings:

Could you tell us
You could easily
You can visit the museum online
Propositions:
["in an e-book for only 10$","more about The Banner Project?","spend two or three days here"]

Réponse attendue :
["more about The Banner Project?", "spend two or three days here", "in an e-book for only 10$"]
Réponse deteter (à éviter) :
["Could you tell us", "more about The Banner Project?", "You could easily", "spend two or three days here", "You can visit the museum online", "in an e-book for only 10$"]
"""

PROMPT_MESSAGE2 = """

"""



def Ask_ChatGPT(ChatGPT, Prompt):
    WebDriverWait(ChatGPT, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='prompt-textarea']"))
        )
    chat_input = ChatGPT.find_element(By.XPATH, "//div[@id='prompt-textarea']")
    for i, line in enumerate(Prompt):
        chat_input.send_keys(line)
        if i < len(Prompt):
            chat_input.send_keys(Keys.SHIFT, Keys.ENTER)
    chat_input.send_keys(PROMPT_MESSAGE2)


