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



# Login to the global exam website with the user and password
def login_globalexam(driver, username, password):
    try:
        # Locate the email input field and enter the username
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "email"))
        ) if driver.find_elements(By.NAME, "email") else None
        if not email_field:
            raise Exception("Email input field not found.")
        email_field.send_keys(username)

        # Locate the password input field and enter the password
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_field.send_keys(password)

        # Locate the login button and click it
        login_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()

        # Wait for the dashboard to load after login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "bg-default-gradient"))
        )
        print("Login successful, redirected to the dashboard.")
    except Exception as e:
        print(f"Error during login: {e}")
    sleep(2)
    
    

def Exercice_01(driver, ChatGPT, target, targets):
    question_wrapper = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "question-wrapper"))
            )
    try:
        question_text = question_wrapper.text
        question_text = f"""Question: 
        {question_text}"""
        print("Question:", question_text)
        proposition_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-name='exam-answer-container']"))
        )
        propositionsList = [
            button.text for button in proposition_container.find_elements(By.CSS_SELECTOR, "button[data-draggable-item-id]")
        ]
        print("Propositions:", propositionsList)
        if len(propositionsList) > 0:
            propositions = f"""[{','.join(f'"{p}"' for p in propositionsList)}]"""
            print("Propositions:", propositions)
            Prompt = question_text + "\n" + "Propositions:" + "\n" + "`"+"`"+"`" + propositions + "\n" + "Reflichis bien avant de me donner la reponse, car la réponse doit impérativement être correcte."
            print("Prompt:", Prompt)
        else:
            propositionsList = []
            Prompt = question_text
            print("Prompt:", Prompt)
    except Exception as e:
        print(f"Error while processing propositions: {e}")
        Prompt = question_text
        print("Prompt:", Prompt)
    lines = Prompt.strip().split("\n")
    Ask_ChatGPT(ChatGPT, lines)
    sleep(2)
    Response_wrapper = WebDriverWait(ChatGPT, 20).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.markdown.prose.dark\\:prose-invert.w-full.break-words.light > p"))
                        )[-1]
    print("Response_wrapper:", Response_wrapper)
    Response = Response_wrapper.text
    print("Response:", Response)
    sleep(2)
    print("Propositions:" , propositionsList)
    response_list = json.loads(Response)
    print("Response:", response_list)
    print("len(Response_wrapper):", len(response_list))
    print("len(propositionsList):", len(propositionsList))
    while (len(response_list) != len(propositionsList)) or not(all(item in propositionsList for item in response_list)):
        Prompt = f"""La longueur de la liste de ta réponse doit être égale à la longueur des propositions, dans cet exemple la longueur est {len(propositionsList)}. Elle doit aussi avoir les mêmes valeurs, c'est juste que tu les mets dans le bon ordre.
        De ces propositions :
        """ + propositions + "\n" + "Reflichis bien avant de me donner la reponse, car la réponse doit impérativement être correcte."
        lines = Prompt.strip().split("\n")
        Ask_ChatGPT(ChatGPT, lines)
        sleep(2)
        Response_w = WebDriverWait(ChatGPT, 30).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.markdown.prose.dark\\:prose-invert.w-full.break-words.light > p"))
                        )[-1]
        print("Response_wrapper:", Response_w)
        Response = Response_w.text
        try:
            response_list = json.loads(Response)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            response_list = []
        print("response_list:")
    if isinstance(response_list, list) and response_list:
        for item in response_list:
            try:
                buttons = proposition_container.find_elements(By.CSS_SELECTOR, "button[data-draggable-item-id]")
                for button in buttons:
                    print(f"Button : {button}")
                    print(f"Button et item: {button.text.strip()} == {item}")
                    if button.text.strip().lower() == item.lower():
                        if len(targets) > 1:
                            for target in targets:
                                print(f"target: {target}")
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target)
                                actions = ActionChains(driver)
                                actions.click_and_hold(button).pause(0.3).release().perform()
                                sleep(1)
                                break
                        else:
                            target = driver.find_element(By.CSS_SELECTOR, "div[role='textbox'], .drop-zone, .dashed-border-box:not(:has(*))")
                            print(f"target: {target}")
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target)
                            sleep(0.5)
                            actions = ActionChains(driver)
                            # Get the target's dimensions and calculate the bottom-right corner
                            target_location = target.location
                            target_size = target.size
                            end_x = target_location['x'] + target_size['width'] - (target_size['width'] / 4)
                            end_y = target_location['y'] + target_size['height'] - (target_size['height'] / 4)
                            # Move the element to the bottom-right corner of the drop zone
                            actions.click_and_hold(button).pause(0.3).move_by_offset(end_x - button.location['x'], end_y - button.location['y']).pause(0.3).release().perform()
                            print(f"click: done")
                            break
                    else:
                        continue
            except StaleElementReferenceException:
                print("Stale element detected. Re-locating the button...")
            except Exception as e:
                print(f"An error occurred: {e}")
    else:
        print("Response n'est pas une liste valide ou est vide.")
