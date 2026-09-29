import random
import threading
import math
import json
from pathlib import Path
from flask import Flask
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Setup Chrome driver automatically
print("[SETUP] Installing Chrome WebDriver...")

count = 1
ml = False
tf = False
val = 1
chrome_options = ChromeOptions()
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("--disable-infobars")
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
radio_options = "EcW08c"

app = Flask(__name__)

CONFIG_PATH = Path(__file__).with_name("config.json")
if not CONFIG_PATH.exists():
    raise SystemExit(f"Missing {CONFIG_PATH.name}. Copy config.example.json to config.json and fill in your values.")
with CONFIG_PATH.open(encoding="utf-8-sig") as f:
    config = json.load(f)

link = config["link"]  # Google form link
response = config["responses"]  # Number of times the form is submitted
percents = config["percents"]  # One list per question: percentage for each option
total = response  # One answer set per submission
persons = {}

for q_num, question_options in enumerate(percents, start=1):
    if sum(question_options) != 100:
        raise SystemExit(f"config.json: question {q_num} percentages add up to {sum(question_options)}, not 100")


def fillForm(link_):
    global tf
    global count
    global val
    global ml
    print(f"[fillForm] Starting form filling with link: {link_}")
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        driver = None
        try:
            print(f"[fillForm] Initializing Chrome WebDriver (attempt {retry_count + 1}/{max_retries})...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            if not ml:
                val = 1
            print(f"[fillForm] Multi-run mode: {ml}, iterations: {val}")
            
            for m in range(val):
                submission_driver = None
                try:
                    temp = count
                    count += 1
                    if temp > total:
                        break
                    print(f"[fillForm] Processing submission #{temp}")
                    
                    # Create a fresh driver for each submission to avoid connection issues
                    print(f"[fillForm] Creating new Chrome driver for submission #{temp}")
                    submission_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                    submission_driver.set_page_load_timeout(30)
                    
                    print(f"[fillForm] Loading form URL for submission #{temp}")
                    submission_driver.get(link_)
                    # Force English (Google ignores the browser language) so the aria-label='Submit'
                    # fallback matches if Google ever changes the submit button's jsname
                    form_url = submission_driver.current_url
                    if "hl=" not in form_url:
                        submission_driver.get(form_url + ("&" if "?" in form_url else "?") + "hl=en")
                    time.sleep(6)  # Increased wait time for page load
                    print(f"[fillForm] Page loaded for submission #{temp}")
                    
                    print(f"[fillForm] Current URL: {submission_driver.current_url}")
                    print(f"[fillForm] Page title: {submission_driver.title}")
                    
                    print(f"[fillForm] Waiting for questions to load...")
                    # Try multiple selectors for questions
                    questions = None
                    question_selectors = [
                        '[class="freebirdFormviewerViewNumberedItemContainer"]',
                        '.freebirdFormviewerViewNumberedItemContainer',
                        '[role="listitem"]',
                        'div[jsmodel]',
                        '.freebirdFormviewerViewItemsItemItem'
                    ]
                    
                    for selector in question_selectors:
                        try:
                            print(f"[fillForm] Trying question selector: {selector}")
                            questions = WebDriverWait(submission_driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                            )
                            if len(questions) > 0:
                                print(f"[fillForm] Found {len(questions)} questions with selector: {selector}")
                                break
                        except Exception as sel_error:
                            print(f"[fillForm] Selector {selector} failed: {str(sel_error)[:100]}")
                            continue
                    
                    if not questions or len(questions) == 0:
                        raise Exception("No questions found on the form with any selector")
                    
                    print(f"[fillForm] Successfully found {len(questions)} questions on form")
                    
                    for question_ in questions:
                        question_idx = questions.index(question_)
                        num = persons['{}'.format(temp)][question_idx]
                        print(f"[fillForm] Processing Question {question_idx + 1}: Need to select option #{num}")
                        
                        try:
                            # Use the working selector for radio buttons
                            choices = question_.find_elements(By.CSS_SELECTOR, '[role="radio"]')
                            
                            if not choices or len(choices) <= num:
                                print(f"[fillForm] Question {question_idx + 1}: Not enough options. Found {len(choices) if choices else 0}, need index {num}")
                                continue
                            
                            print(f"[fillForm] Question {question_idx + 1}: Found {len(choices)} options")
                            
                            # Click the option
                            print(f"[fillForm] Question {question_idx + 1}: Clicking option #{num}")
                            time.sleep(0.3)
                            try:
                                choices[num].click()
                            except:
                                # Try JavaScript click if regular click fails
                                submission_driver.execute_script("arguments[0].click();", choices[num])
                            
                            print(f"[fillForm] Question {question_idx + 1}: Successfully selected option #{num}")

                        except Exception as q_error:
                            import traceback
                            print(f"[fillForm] Question {question_idx + 1}: Error - {str(q_error)[:200]}")
                    
                    print(f"[fillForm] All questions filled. Submitting form for submission #{temp}")
                    try:
                        # Scroll to bottom to ensure submit button is visible
                        submission_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        
                        # Try to wait for submit button and click it with multiple selectors
                        # jsname="M2UYVd" is Google Forms' submit button in every language
                        submit_button = None
                        selectors = [
                            (By.CSS_SELECTOR, "div[role='button'][jsname='M2UYVd']"),
                            (By.CSS_SELECTOR, "div[role='button'][aria-label='Submit']"),
                        ]
                        
                        for idx, selector in enumerate(selectors):
                            try:
                                print(f"[fillForm] Trying selector {idx+1}/{len(selectors)}: {selector[0]} = {selector[1][:50]}")
                                submit_button = WebDriverWait(submission_driver, 8).until(EC.element_to_be_clickable(selector))
                                print(f"[fillForm] Found submit button with selector {idx+1}")
                                break
                            except Exception:
                                continue
                        
                        if submit_button is None:
                            print(f"[fillForm] ERROR: Could not find submit button with any selector")
                            raise Exception("Submit button not found after trying all selectors")
                        
                        time.sleep(0.5)
                        try:
                            submit_button.click()
                        except Exception:
                            submission_driver.execute_script("arguments[0].click();", submit_button)
                        
                        print(f"[fillForm] Waiting for submission confirmation...")
                        # Google redirects to .../formResponse once the response is recorded
                        WebDriverWait(submission_driver, 15).until(EC.url_contains("formResponse"))
                    except Exception as submit_error:
                        import traceback
                        print(f"[fillForm] ERROR submitting form #{temp}: {type(submit_error).__name__}: {str(submit_error)}")
                        print(f"[fillForm] Submit error traceback: {traceback.format_exc()}")
                        raise  # Re-raise to be caught by outer exception handler

                    print(f"[fillForm] Form #{temp} submitted successfully")
                    
                except Exception as sub_error:
                    import traceback
                    print(f"[fillForm] Error during submission #{temp}: {type(sub_error).__name__}: {str(sub_error)}")
                    print(f"[fillForm] Traceback: {traceback.format_exc()}")
                finally:
                    if submission_driver:
                        try:
                            submission_driver.quit()
                            print(f"[fillForm] Closed submission driver for #{temp}")
                        except:
                            pass
            
            tf = True
            ml = False
            val = 1
            print(f"[fillForm] Closing main WebDriver")
            if driver:
                driver.quit()
            print(f"[fillForm] Form filling completed successfully")
            break  # Exit retry loop on success
        except ConnectionError as ce:
            retry_count += 1
            print(f"[fillForm] Connection error (attempt {retry_count}/{max_retries}): {str(ce)}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if retry_count < max_retries:
                wait_time = 10 * retry_count  # Longer backoff: 10s, 20s, 30s
                print(f"[fillForm] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[fillForm] Max retries reached. Giving up.")
        except Exception as e:
            retry_count += 1
            print(f"[fillForm] Error occurred (attempt {retry_count}/{max_retries}): {str(e)}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if retry_count < max_retries:
                wait_time = 10 * retry_count
                print(f"[fillForm] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[fillForm] Max retries reached after error: {str(e)}")


def multiRun(key1, key2):
    global tf
    global ml
    global val
    print(f"[multiRun] Starting multi-run with {key2} threads")
    tf = False
    if int(key2) > 4:
        print(f"[multiRun] Requests ({key2}) exceed limit of 4, splitting into chunks")
        ml = True
        val = math.ceil(int(key2) / 4)
        key2 = 4
        print(f"[multiRun] Running {val} iterations with {key2} threads each")
    for i in range(int(key2)):
        print(f"[multiRun] Spawning thread {i + 1} of {int(key2)}")
        threading.Thread(target=fillForm, args=(key1,)).start()
        time.sleep(5)  # Increased delay between thread starts to reduce server load
    print(f"[multiRun] All threads spawned, waiting for completion...")
    time.sleep(10)  # Increased initial wait time


def formFill(key1, key2):
    print(f"[formFill] Initiating form fill process for {key2} responses")
    print(f"[formFill] Form link: {key1}")
    try:
        multiRun(key1, key2)
        print(f"[formFill] Waiting for all threads to complete...")
        timeout = 300  # 5 minutes timeout
        elapsed = 0
        while elapsed < timeout:
            if tf:
                print(f'[formFill] SUCCESS: {key2} form submissions completed successfully!')
                break
            time.sleep(1)
            elapsed += 1
        if elapsed >= timeout:
            print(f'[formFill] Timeout: Form submissions did not complete within {timeout} seconds')
    except Exception as e:
        print(f'[formFill] ERROR: {str(e)}')
        print('[formFill] Error in filling your form, your form might contain questions other than MCQ or have email verification')


for n in range(total):
    persons[f"{(n + 1)}"] = []

# Build the probability distribution correctly
print("[SETUP] Building probability distribution...")
print(f"[SETUP] Total persons: {total}")
print(f"[SETUP] Number of questions: {len(percents)}")
print(f"[SETUP] Percentages per question: {percents}")

# Create answer list for each question separately
all_question_answers = []

for question_idx, question_options in enumerate(percents):
    print(f"[SETUP] Question {question_idx + 1} has {len(question_options)} options")
    
    # Build answer list for this question based on percentages
    question_answers = []
    for option_idx, percentage in enumerate(question_options):
        count_for_option = math.floor(percentage * total / 100)
        print(f"[SETUP]   Option {option_idx}: {percentage}% = {count_for_option} selections")
        question_answers.extend([option_idx] * count_for_option)
    
    # Pad with random options if needed to reach total
    while len(question_answers) < total:
        question_answers.append(random.randint(0, len(question_options) - 1))
    
    # Shuffle this question's answers
    random.shuffle(question_answers)
    all_question_answers.append(question_answers[:total])
    print(f"[SETUP] Question {question_idx + 1} answer distribution: {question_answers[:10]}...")

# Assign answers to each person (one answer per question)
for person_idx in range(1, total + 1):
    for question_idx in range(len(percents)):
        persons[str(person_idx)].append(all_question_answers[question_idx][person_idx - 1])

print(f"[SETUP] Distribution built successfully!")
print(f"[SETUP] Person #1 selections: {persons.get('1', [])}")
print(f"[SETUP] Person #2 selections: {persons.get('2', [])}")
print(f"[SETUP] Person #10 selections: {persons.get('10', [])}")
print(f"[SETUP] Person #50 selections: {persons.get('50', [])}")

if __name__ == "__main__":
    formFill(link, response)