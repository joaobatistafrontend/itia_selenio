from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://qa.app.saudehd.com.br/apps/reception/home")

wait = WebDriverWait(driver, 20)  # aumentei o tempo de espera

# Login
username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
password_input = driver.find_element(By.NAME, "password")
username_input.send_keys("estagiarios1@healthdev.io")
password_input.send_keys("123456")
login_button = driver.find_element(By.XPATH, "//button[text()='Entrar']")
login_button.click()

# Espera até a lista de clínicas aparecer
clinica_li = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//span[text()='CLINICA MÉDICA DO CEARÁ']/ancestor::li")
))

# Clica usando ActionChains
actions = ActionChains(driver)
actions.move_to_element(clinica_li).click().perform()

recepcao_link = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//p[text()='Recepção']/ancestor::a")
))
recepcao_link.click()
botao_2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='2' and @data-state='closed']")))
botao_2.click()
elementos = driver.find_elements(By.CSS_SELECTOR, ".sc-gEvEer.ghGoya.max-w-\\[125px\\].false")


linhas = driver.find_elements(By.XPATH, "//tr[@data-disabled='false']")

linhas_habilitadas = driver.find_elements(By.XPATH, "//tr[@data-disabled='false']")

print(f"Total de linhas habilitadas: {len(linhas_habilitadas)}")
botao = wait.until(EC.element_to_be_clickable((
    By.XPATH,
    "//tr[@data-disabled='false']//td//span[contains(text(),'disponível')]/ancestor::button"
)))

botao.click()





saida = input("Pressione Enter para fechar o navegador...")
if saida == "":
    driver.quit()
