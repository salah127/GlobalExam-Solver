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
from bs4 import BeautifulSoup
from pymongo import MongoClient
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

def get_answer_Exercice_01(driver, ChatGPT, target, targets, h4):
    print("child:", h4) 
    question_wrapper = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "question-wrapper"))
            )
    try:
            div_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.bullet-list"))
                )
    except Exception as e:
        print(f"Error locating addsitional drop zones: {e}")
    question_text = question_wrapper.text

    try:
        try:
            div_html = div_element.get_attribute("innerHTML")
            soup = BeautifulSoup(div_html, "html.parser")
            print("soup:", soup)
            for span in soup.find_all("span", class_="drop-zone"):
                span.replace_with("...............")
            question_text = soup.get_text(separator=" ").strip()
        except Exception as e:
            print(f"Error while processing div element: {e}")

        # Get the modified text
            
        
        
        # question_text = question_wrapper.text
        question_text = f"""Question: 
        {question_text}"""
        print("Question:", question_text)
        # question_text = f"""Question: 
        # {question_text}"""
        # print("Question:", question_text)
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
    sleep(2)
    Response = Response_wrapper.text
    print("Response:", Response)
    sleep(2)
    print("Propositions:" , propositionsList)
    response_list = json.loads(Response)
    print("Response:", response_list)
    print("len(Response_wrapper):", len(response_list))
    print("len(propositionsList):", len(propositionsList))
    while not Response or (len(response_list) != len(response_list)):
        Prompt = f"""La longueur de la liste de ta réponse doit être égale à la longueur des propositions, dans cet exemple la longueur est {len(propositionsList)}.
        voila les proposition propositions :
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
    sleep(2)
    while not Response or not(all(item in propositionsList for item in response_list)):
        Prompt = f"""not """ + response_list[0] +"""
        tu reponse doit avoir les mêmes valeurs que les propositions suivants:
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
        # on doit stocké dans la base de donner
        ######################################################################
        try:
            client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB connection string if needed
            db = client["GlobalExamSolver"]  # Replace with your database name
            Certificat = db["Certificat"]  # Replace with your collection name
            Exercice = db["Exercice"]  # Replace with your collection name
            exercice_ids = [str(exercice["_id"]) for exercice in Exercice.find({}, {"_id": 1})]
            
            existing_certificat = Certificat.find_one({"nom": h4})
            if existing_certificat:
                # If the certificate exists, get its ID
                certif_id = existing_certificat["_id"]
                print(f"Certificate already exists with ID: {certif_id}")
            else:
                Certif = {
                    "nom": h4,
                    "question": [],
                }
                db_certif = Certificat.insert_one(Certif)
                certif_id = db_certif.inserted_id
            existing_exercise = Exercice.find_one({"question": question_text})
                
            if existing_exercise:
                # If the exercise exists, get its ID
                Exe_id = existing_exercise["_id"]
                print(f"Exercise already exists with ID: {Exe_id}")
            else:
                # If the exercise is new, insert it
                Exe = {
                    "question": question_text,
                    "response": response_list,
                }
                print("Exe:", Exe)
                db_Exercice = Exercice.insert_one(Exe)
                Exe_id = db_Exercice.inserted_id  # Get the inserted exercise ID
                print(f"New exercise inserted with ID: {Exe_id}")

                # Update the certificate with the exercise ID
                Certificat.update_one(
                    {"_id": certif_id},
                    {"$push": {"question": str(Exe_id)}}  # Add the exercise ID to the 'question' list
                )
                print(f"Certificate updated with exercise ID: {Exe_id}")
            
        except Exception as e:
            print(f"Error storing response in MongoDB: {e}")
        finally:
            client.close()
    else:
        print("Response n'est pas une liste valide ou est vide.")



def get_answer_Exercice_02(driver, ChatGPT, question_wrapper, h4):
    question_text = question_wrapper.text
    lines = question_text.strip().split("\n")
    Ask_ChatGPT(ChatGPT, lines)
    sleep(2)
    Response_wrapper = WebDriverWait(ChatGPT, 20).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.markdown.prose.dark\\:prose-invert.w-full.break-words.light > p"))
                        )[-1]
    print("Response_wrapper:", Response_wrapper)
    sleep(2)
    Response = Response_wrapper.text
    print("Response:", Response)
    sleep(2)
    response_list = json.loads(Response)
    if isinstance(response_list, list) and response_list:
        ######################################################################
        try:
            client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB connection string if needed
            db = client["GlobalExamSolver"]  # Replace with your database name
            Certificat = db["Certificat"]  # Replace with your collection name
            Exercice = db["Exercice"]  # Replace with your collection name
            exercice_ids = [str(exercice["_id"]) for exercice in Exercice.find({}, {"_id": 1})]
            
            existing_certificat = Certificat.find_one({"nom": h4})
            if existing_certificat:
                # If the certificate exists, get its ID
                certif_id = existing_certificat["_id"]
                print(f"Certificate already exists with ID: {certif_id}")
            else:
                Certif = {
                    "nom": h4,
                    "question": [],
                }
                db_certif = Certificat.insert_one(Certif)
                certif_id = db_certif.inserted_id
            existing_exercise = Exercice.find_one({"question": question_text})
            if existing_exercise:
                # If the exercise exists, get its ID
                Exe_id = existing_exercise["_id"]
                print(f"Exercise already exists with ID: {Exe_id}")
            else:
                # If the exercise is new, insert it
                Exe = {
                    "question": question_text,
                    "response": response_list,
                }
                print("Exe:", Exe)
                db_Exercice = Exercice.insert_one(Exe)
                Exe_id = db_Exercice.inserted_id  # Get the inserted exercise ID
                print(f"New exercise inserted with ID: {Exe_id}")

                # Update the certificate with the exercise ID
                Certificat.update_one(
                    {"_id": certif_id},
                    {"$push": {"question": str(Exe_id)}}  # Add the exercise ID to the 'question' list
                )
                print(f"Certificate updated with exercise ID: {Exe_id}")
            
        except Exception as e:
            print(f"Error storing response in MongoDB: {e}")
        finally:
            client.close()
        ##############################################################
        
        sleep(2)
        print("Response:", response_list)

def answer_Exercice_01(driver, ChatGPT, target, targets, h4):
    print("child:", h4) 
    question_wrapper = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "question-wrapper"))
            )
    try:
            div_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.bullet-list"))
                )
    except Exception as e:
        print(f"Error locating addsitional drop zones: {e}")
    question_text = question_wrapper.text

    try:
        try:
            div_html = div_element.get_attribute("innerHTML")
            soup = BeautifulSoup(div_html, "html.parser")
            print("soup:", soup)
            for span in soup.find_all("span", class_="drop-zone"):
                span.replace_with("...............")
            question_text = soup.get_text(separator=" ").strip()
        except Exception as e:
            print(f"Error while processing div element: {e}")
        # question_text = question_wrapper.text
        question_text = f"""Question: 
        {question_text}"""
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
    sleep(2)
    Response = Response_wrapper.text
    response_list = json.loads(Response)
    sleep(2)
        
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
        
        
def answer_Exercice_02(driver, ChatGPT, question_wrapper, h4):
    question_text = question_wrapper.text
    lines = question_text.strip().split("\n")
    Ask_ChatGPT(ChatGPT, lines)
    sleep(2)
    Response_wrapper = WebDriverWait(ChatGPT, 20).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.markdown.prose.dark\\:prose-invert.w-full.break-words.light > p"))
                        )[-1]
    print("Response_wrapper:", Response_wrapper)
    sleep(2)
    Response = Response_wrapper.text
    print("Response:", Response)
    sleep(2)
    response_list = json.loads(Response)
    if isinstance(response_list, list) and response_list:
        ######################################################################
        try:
            client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB connection string if needed
            db = client["GlobalExamSolver"]  # Replace with your database name
            Certificat = db["Certificat"]  # Replace with your collection name
            Exercice = db["Exercice"]  # Replace with your collection name
            exercice_ids = [str(exercice["_id"]) for exercice in Exercice.find({}, {"_id": 1})]
            
            existing_certificat = Certificat.find_one({"nom": h4})
            if existing_certificat:
                # If the certificate exists, get its ID
                certif_id = existing_certificat["_id"]
                print(f"Certificate already exists with ID: {certif_id}")
            else:
                Certif = {
                    "nom": h4,
                    "question": [],
                }
                db_certif = Certificat.insert_one(Certif)
                certif_id = db_certif.inserted_id
            existing_exercise = Exercice.find_one({"question": question_text})
            if existing_exercise:
                # If the exercise exists, get its ID
                Exe_id = existing_exercise["_id"]
                print(f"Exercise already exists with ID: {Exe_id}")
            else:
                # If the exercise is new, insert it
                Exe = {
                    "question": question_text,
                    "response": response_list,
                }
                print("Exe:", Exe)
                db_Exercice = Exercice.insert_one(Exe)
                Exe_id = db_Exercice.inserted_id  # Get the inserted exercise ID
                print(f"New exercise inserted with ID: {Exe_id}")

                # Update the certificate with the exercise ID
                Certificat.update_one(
                    {"_id": certif_id},
                    {"$push": {"question": str(Exe_id)}}  # Add the exercise ID to the 'question' list
                )
                print(f"Certificate updated with exercise ID: {Exe_id}")
            
        except Exception as e:
            print(f"Error storing response in MongoDB: {e}")
        finally:
            client.close()
        ##############################################################
        
        sleep(2)
        print("Response:", response_list)

def anwer_exercice(driver, ChatGPT):
    driver.get("https://general.global-exam.com/levels/content/9584")
    specific_element = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'flex items-center justify-between p-6 cursor-pointer') and .//p[contains(text(),'Certification')]]"))
)
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", specific_element)
    specific_element.click()
    print("Clicked on the 'Certification' element.")
    sleep(1)
    
    certification_element = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='group flex flex-col items-center cursor-pointer' and .//p[text()='Certification']]"))
    )
    certification_element.click()
    for i in range(30):
        try:
            question_wrapper = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "question-wrapper"))
            )
            # Locate the primary target drop zone
            target = driver.find_element(By.CSS_SELECTOR, "div[role='textbox'], .drop-zone, .dashed-border-box:not(:has(*))")
            # Locate all potential drop zones
            targets = question_wrapper.find_elements(By.CSS_SELECTOR, "span.drop-zone")
        except Exception as e:
            print(f"Error locating additional drop zones: {e}")
            targets = []
            target = None
        if target or targets:
            answer_Exercice_01(driver, ChatGPT, target, targets)
            try:
                validate_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'relative overflow-hidden group inline-flex justify-center font-bold rounded-full') and .//span[text()='Valider']]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", validate_button)
                validate_button.click()
                print("Clicked on 'Valider' button.")
                sleep(2)
            except Exception as e:
                print(f"Error clicking 'Valider' button: {e}")
        else:
            answer_Exercice_02(driver, ChatGPT, question_wrapper)
            try:
                validate_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'relative overflow-hidden group inline-flex justify-center font-bold rounded-full') and .//span[text()='Valider']]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", validate_button)
                validate_button.click()
                print("Clicked on 'Valider' button.")
                sleep(2)
            except Exception as e:
                print(f"Error clicking 'Valider' button: {e}")

def solve_next_exercice(driver, ChatGPT):
    parent_div = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.grid.gap-6.grid-cols-1.sm\\:grid-cols-2.md\\:grid-cols-3.lg\\:grid-cols-4"))
    )

    # Get all child div elements
    child_divs = parent_div.find_elements(By.CSS_SELECTOR, "div.card")
    

    for child in child_divs:
        h4_elements = child.find_element(By.TAG_NAME, "h4")
        h4 = h4_elements.text
        
        # ChatGPT.get("https://chatgpt.com/c/681368bb-23c8-8002-a76b-678d4b789960")
        print("Redirected driver to the specified URL.")
        sleep(1)
        print("child:", child.text)
        
        child.click()
        print("Clicked on a child element.")
        sleep(1)
        specific_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'flex items-center justify-between p-6 cursor-pointer') and .//p[contains(text(),'Certification')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", specific_element)
        specific_element.click()
        print("Clicked on the 'Certification' element.")
        sleep(1)
        
        certification_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='group flex flex-col items-center cursor-pointer' and .//p[text()='Certification']]"))
        )
        certification_element.click()
        print("Clicked on the 'Certification' element with the specified class.")
        
        sleep(1)
        for i in range(30):
            driver.get("https://general.global-exam.com/levels/content/9584")
            specific_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'flex items-center justify-between p-6 cursor-pointer') and .//p[contains(text(),'Certification')]]"))
        )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", specific_element)
            specific_element.click()
            print("Clicked on the 'Certification' element.")
            sleep(1)
            
            certification_element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='group flex flex-col items-center cursor-pointer' and .//p[text()='Certification']]"))
            )
            certification_element.click()
            try:
                question_wrapper = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "question-wrapper"))
                )
                # Locate the primary target drop zone
                target = driver.find_element(By.CSS_SELECTOR, "div[role='textbox'], .drop-zone, .dashed-border-box:not(:has(*))")
                # Locate all potential drop zones
                targets = question_wrapper.find_elements(By.CSS_SELECTOR, "span.drop-zone")
            except Exception as e:
                print(f"Error locating additional drop zones: {e}")
                targets = []
                target = None
            if target or targets:
                get_answer_Exercice_01(driver, ChatGPT, target, targets)
                # try:
                #     validate_button = WebDriverWait(driver, 20).until(
                #     EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'relative overflow-hidden group inline-flex justify-center font-bold rounded-full') and .//span[text()='Valider']]"))
                #     )
                #     driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", validate_button)
                #     validate_button.click()
                #     print("Clicked on 'Valider' button.")
                #     sleep(2)
                # except Exception as e:
                #     print(f"Error clicking 'Valider' button: {e}")
            else:
                get_answer_Exercice_02(driver, ChatGPT, question_wrapper)
                # try:
                #     validate_button = WebDriverWait(driver, 20).until(
                #         EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'relative overflow-hidden group inline-flex justify-center font-bold rounded-full') and .//span[text()='Valider']]"))
                #     )
                #     driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", validate_button)
                #     validate_button.click()
                #     print("Clicked on 'Valider' button.")
                #     sleep(2)
                # except Exception as e:
                #     print(f"Error clicking 'Valider' button: {e}")
    print("done!!!")



# Create the main window
window = tk.Tk()
window.title("GlobalExam Solver")
window.geometry("1200x620")

# ==== Add a solve for exercice tab ====

# Add title
title_label = tk.Label(window, text="Solve every exercice possible on GlobalExam !", font=("Arial", "12", "bold"))
title_label.pack()
title_label.place(x=350, y=20)

# Add prompt for the user and the password
GlobalEx = tk.Label(window, text="GlobalExam:", font=("Arial", "12", "bold"))
GlobalEx.pack()
GlobalEx.place(x=80, y=70)
username_label = tk.Label(window, text="Username:")
username_label.pack()
username_entry = tk.Entry(window)
username_entry.pack()
password_label = tk.Label(window, text="Password:")
password_label.pack()
password_entry = tk.Entry(window, show="*")
password_entry.pack()
username_label.place(x=100, y=100)
username_entry.place(x=100, y=130)
password_label.place(x=100, y=160)
password_entry.place(x=100, y=190)

ChatGPT = tk.Label(window, text="Gmail related to ChatGPT:", font=("Arial", "12", "bold"))
ChatGPT.pack()
ChatGPT.place(x=880, y=70)
username_label_chat = tk.Label(window, text="Username:")
username_label_chat.pack()
username_entry_chat = tk.Entry(window)
username_entry_chat.pack()
password_label_chat = tk.Label(window, text="Password:")
password_label_chat.pack()
password_entry_chat = tk.Entry(window, show="*")
password_entry_chat.pack()
username_label_chat.place(x=900, y=100)
username_entry_chat.place(x=900, y=130)
password_label_chat.place(x=900, y=160)
password_entry_chat.place(x=900, y=190)


# Create the subdomain label and entry
subdomain_label = tk.Label(window, text="Choisissez soit :")
subdomain_label1 = tk.Label(window, text="grammar - subdomain_entry - vocabulary", font=("Arial", "10", "bold"))
subdomain_label.pack()
subdomain_label1.pack()
subdomain_entry = tk.Entry(window)
subdomain_entry.insert(0, "grammar")
subdomain_entry.pack()
subdomain_label.place(x=350, y=140)
subdomain_label1.place(x=350, y=155)
subdomain_entry.place(x=350, y=180)



def on_solve_next_exercice():
    try:
        username = username_entry.get()
        password = password_entry.get()
        googlelogin = username_entry_chat.get()
        googlepassword = password_entry_chat.get()



        
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()

        # Définir demi-largeur
        half_width = screen_width // 2

        driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install())
        driver.set_page_load_timeout(3000)
        driver.implicitly_wait(10)
        driver.get("https://auth.global-exam.com/login")
        driver.set_window_size(half_width, screen_height)
        driver.set_window_position(0, 0)
        sleep(1)
        
        ChatGPT = uc.Chrome(driver_executable_path=ChromeDriverManager().install())
        ChatGPT.set_page_load_timeout(3000)
        ChatGPT.implicitly_wait(10)
        ChatGPT.set_window_size(half_width, screen_height)
        ChatGPT.set_window_position(half_width, 0)
        # ChatGPT.get("https://chatgpt.com/)")
        ChatGPT.get("https://chatgpt.com/)")
        sleep(2)
        
        # Locate and click the "Se connecter" button
        try:
            login_butto = WebDriverWait(ChatGPT, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and contains(@class, 'btn-large') and .//div[text()='Se connecter']]"))
            )
            login_butto.click()
            sleep(2)
            login_button = WebDriverWait(ChatGPT, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and @data-testid='login-button']"))
            )
            login_button.click()
            print("Clicked on 'Se connecter' button.")
        except Exception as e:
            print(f"Error: 'Se connecter' button not found or not clickable. Details: {e}")
        try:
            google_button = WebDriverWait(ChatGPT, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@name='intent' and @value='google' and .//div[contains(@class, '_logoPositioner_gdh4y_1')]]"))
            )
            google_button.click()
            print("Clicked on 'Continuer avec Google' button.")
        except Exception as e:
            print(f"Error: 'Continuer avec Google' button not found or not clickable. Details: {e}")

        # Type the username in the email input field
        email_input = WebDriverWait(ChatGPT, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_input.send_keys(googlelogin)
        
        next_button = WebDriverWait(ChatGPT, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'VfPpkd-LgbsSe') and .//span[text()='Suivant']]"))
        )
        next_button.click()
        sleep(3)
        
        password_input = WebDriverWait(ChatGPT, 10).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_input.send_keys(googlepassword)
        next_button = WebDriverWait(ChatGPT, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'VfPpkd-LgbsSe') and .//span[text()='Suivant']]"))
        )
        next_button.click()
        sleep(2)
        try:
            login_button = WebDriverWait(ChatGPT, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and @data-testid='login-button']"))
            )
            login_button.click()
            google_button = WebDriverWait(ChatGPT, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'social-btn') and .//span[text()='Continuer avec Google']]"))
        )
            google_button.click()
            print("Clicked on 'Se connecter' button.")
        except Exception as e:
            print(f"Error: 'Se connecter' button not found or not clickable. Details: {e}")
        
        ChatGPT.get("https://chatgpt.com/c/68187314-b408-8004-a82a-49c5ae53d291")
        print("Clicked on 'Suivant' button.")
        sleep(3)

        print(r"/!\ Do not close this window ! /!\ " + "\n\n")
        
        # lines = PROMPT_MESSAGE1.strip().split("\n")
        # Ask_ChatGPT(ChatGPT, lines)
        login_globalexam(driver, username, password)
        try:
            try:
                continue_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Continuer sans accepter']"))
                )
                continue_button.click()
                print("Clicked on 'Continuer sans accepter'.")
            except Exception as e:
                pass
        except:
            pass
        while True:
            solve_next_exercice(driver, ChatGPT)


    except Exception as e:
        print(f"Une erreur s'est produite : {e}")
        
# Create the solve next exercice button
solve_next_exercice_button = tk.Button(window, text="Solve exercice", command=on_solve_next_exercice)
solve_next_exercice_button.pack()
solve_next_exercice_button.place(x=350, y=410)

# add a quit button
quit_button = tk.Button(window, text="Exit", command=window.quit)
quit_button.pack()
quit_button.place(x=600, y=500)

# Print a message to the user to not close the window
print("/!\\ Do not close this window ! /!\\ \n\n")

# Start the main loop
window.mainloop()
