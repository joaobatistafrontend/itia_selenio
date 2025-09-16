# t3.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time

# ======= CONFIG =======
URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"
NOME_PARA_DIGITAR = "joao erik"

WAIT_DEFAULT = 20
ENTER_DELAY = 3.0        # <<<<<< espera de 3 segundos antes do Enter
TYPE_DELAY = 0.08        # digitação um pouco mais lenta

# ======= HELPERS =======
def W(driver, t=WAIT_DEFAULT): return WebDriverWait(driver, t)

def txt(el, xp):
    try: return el.find_element(By.XPATH, xp).get_attribute("textContent").strip()
    except: return ""

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def force_click(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
        ActionChains(driver).move_to_element(el).pause(0.05).click().perform(); return True
    except: pass
    try: el.click(); return True
    except: pass
    try: driver.execute_script("arguments[0].click();", el); return True
    except: pass
    return False

def login(driver):
    driver.get(URL)
    W(driver).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "password").send_keys(SENHA)
    driver.find_element(By.XPATH, "//button[normalize-space()='Entrar']").click()

def selecionar_clinica(driver, nome):
    cards = W(driver).until(EC.presence_of_all_elements_located(
        (By.XPATH, "//ul[contains(@class,'flex')]/li[contains(@class,'group')]")
    ))
    alvo = None
    for li in cards:
        titulo = txt(li, ".//span[contains(@class,'text-base') and contains(@class,'font-medium')]")
        if titulo == nome:
            alvo = li; break
    if not alvo:
        raise RuntimeError(f"Não achei a clínica: {nome}")
    try:
        area = alvo.find_element(By.XPATH, ".//div[contains(@class,'px-8') and contains(@class,'py-6')]")
    except:
        area = alvo
    js_click(driver, area)
    time.sleep(0.3)

def ir_para_recepcao(driver):
    link = W(driver).until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link)
    time.sleep(0.3)

def esperar_tabela(driver):
    W(driver).until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))

def encontrar_primeiro_tr_disponivel_td4_vazio(driver):
    """1º tr habilitado com status 'disponível' e TD4='-'."""
    xp = ("//tbody/tr[not(@data-disabled='true') and "
          "translate(normalize-space(.//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]),"
          " 'ÁÀÂÃÉÊÍÓÔÕÚÜÇABCDEFGHIJKLMNOPQRSTUVWXYZ',"
          " 'áàâãéêíóôõúüçabcdefghijklmnopqrstuvwxyz')='disponível' and "
          "normalize-space(.//td[4])='-'][1]")
    try:
        tr = W(driver, 12).until(EC.presence_of_element_located((By.XPATH, xp)))
        td4 = tr.find_element(By.XPATH, "./td[4]")
        hora = txt(tr, ".//td[3]//*[self::div or self::p or self::span][1]") or "?"
        return tr, td4, hora
    except TimeoutException:
        return None, None, None

def achar_campo_digitacao(driver):
    """Prioriza input em dialog/modal, senão pega o focado/global."""
    # focado
    try:
        active = driver.switch_to.active_element
        tag = (active.tag_name or "").lower()
        ce = (active.get_attribute("contenteditable") or "").lower() == "true"
        if tag in ("input", "textarea") or ce:
            return active
    except: pass
    # dialog/modal
    candidatos = [
        "//*[@role='dialog' or contains(@class,'Dialog') or contains(@class,'modal')]//input[not(@type) or @type='text' or @type='search']",
        "//*[@role='dialog']//div[@contenteditable='true']",
        "//div[contains(@class,'Dialog') or contains(@class,'modal')]//input[not(@type) or @type='text' or @type='search']",
    ]
    for xp in candidatos:
        try: return W(driver, 8).until(EC.visibility_of_element_located((By.XPATH, xp)))
        except TimeoutException: continue
    # global
    try: return W(driver, 6).until(EC.visibility_of_element_located((By.XPATH, "//input[not(@type) or @type='text' or @type='search']")))
    except TimeoutException: return None

def slow_type(el, text, per_char_delay=TYPE_DELAY):
    # limpa
    try:
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        time.sleep(0.15)
    except: pass
    for ch in text:
        el.send_keys(ch)
        time.sleep(per_char_delay)

def esperar_td4_preenchida(driver, hora, esperado=NOME_PARA_DIGITAR, timeout=10):
    """Espera a TD4 da linha 'hora' sair de '-' ou conter parte do esperado."""
    esperado_low = esperado.lower().split()[0]
    xp_td4 = ("//tbody/tr[td[3]//*[self::div or self::p or self::span]"
              f"[normalize-space()='{hora}']]/td[4]")
    try:
        # conter parte do nome
        W(driver, timeout).until(
            EC.text_to_be_present_in_element((By.XPATH, xp_td4), esperado_low)
        )
        return True
    except TimeoutException:
        pass
    try:
        # qualquer valor diferente de '-'
        W(driver, max(3, timeout//2)).until(
            lambda d: d.find_element(By.XPATH, xp_td4).get_attribute("textContent").strip() != "-"
        )
        return True
    except Exception:
        return False

def clicar_td4_digitar_esperar_enter(driver):
    """Clica TD4 (primeiro disponível '-'), digita nome, espera 3s e dá Enter."""
    esperar_tabela(driver)

    tr, td4, hora = encontrar_primeiro_tr_disponivel_td4_vazio(driver)
    if not tr:
        print("Nenhuma linha disponível com TD4 = '-' encontrada.")
        return False

    # clique na TD4 (e arma a linha se necessário)
    if not force_click(driver, td4):
        try:
            btn_status = tr.find_element(By.XPATH, ".//td[6]//button")
            js_click(driver, btn_status); time.sleep(0.25)
            if not force_click(driver, td4):
                print("Não consegui clicar na TD4.")
                return False
        except Exception:
            print("Não consegui preparar a linha para clique.")
            return False

    time.sleep(0.3)  # deixa o campo abrir

    # achar campo e digitar
    campo = achar_campo_digitacao(driver)
    if not campo:
        print("Não encontrei campo para digitar.")
        return False

    try: js_click(driver, campo)
    except: pass

    slow_type(campo, NOME_PARA_DIGITAR, TYPE_DELAY)

    # >>>>>>> ESPERA EXIGIDA (3s) ANTES DO ENTER <<<<<<<
    time.sleep(ENTER_DELAY)

    # Enter
    campo.send_keys(Keys.ENTER)

    # valida que a TD4 foi preenchida
    ok = esperar_td4_preenchida(driver, hora, NOME_PARA_DIGITAR, timeout=12)
    print("RESULTADO:", "SUCESSO" if ok else "FALHOU (TD4 não mudou após Enter)")
    return ok

# ======= MAIN =======
def main():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # opts.add_argument("--headless=new")  # opcional
    driver = webdriver.Chrome(options=opts)

    try:
        # limpa possíveis seleções antigas
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)

        clicar_td4_digitar_esperar_enter(driver)

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
# t3.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time

# ======= CONFIG =======
URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"
NOME_PARA_DIGITAR = "joao erik"

WAIT_DEFAULT = 20
ENTER_DELAY = 3.0        # <<<<<< espera de 3 segundos antes do Enter
TYPE_DELAY = 0.08        # digitação um pouco mais lenta

# ======= HELPERS =======
def W(driver, t=WAIT_DEFAULT): return WebDriverWait(driver, t)

def txt(el, xp):
    try: return el.find_element(By.XPATH, xp).get_attribute("textContent").strip()
    except: return ""

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def force_click(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
        ActionChains(driver).move_to_element(el).pause(0.05).click().perform(); return True
    except: pass
    try: el.click(); return True
    except: pass
    try: driver.execute_script("arguments[0].click();", el); return True
    except: pass
    return False

def login(driver):
    driver.get(URL)
    W(driver).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO)
    driver.find_element(By.NAME, "password").send_keys(SENHA)
    driver.find_element(By.XPATH, "//button[normalize-space()='Entrar']").click()

def selecionar_clinica(driver, nome):
    cards = W(driver).until(EC.presence_of_all_elements_located(
        (By.XPATH, "//ul[contains(@class,'flex')]/li[contains(@class,'group')]")
    ))
    alvo = None
    for li in cards:
        titulo = txt(li, ".//span[contains(@class,'text-base') and contains(@class,'font-medium')]")
        if titulo == nome:
            alvo = li; break
    if not alvo:
        raise RuntimeError(f"Não achei a clínica: {nome}")
    try:
        area = alvo.find_element(By.XPATH, ".//div[contains(@class,'px-8') and contains(@class,'py-6')]")
    except:
        area = alvo
    js_click(driver, area)
    time.sleep(0.3)

def ir_para_recepcao(driver):
    link = W(driver).until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link)
    time.sleep(0.3)

def esperar_tabela(driver):
    W(driver).until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))

def encontrar_primeiro_tr_disponivel_td4_vazio(driver):
    """1º tr habilitado com status 'disponível' e TD4='-'."""
    xp = ("//tbody/tr[not(@data-disabled='true') and "
          "translate(normalize-space(.//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]),"
          " 'ÁÀÂÃÉÊÍÓÔÕÚÜÇABCDEFGHIJKLMNOPQRSTUVWXYZ',"
          " 'áàâãéêíóôõúüçabcdefghijklmnopqrstuvwxyz')='disponível' and "
          "normalize-space(.//td[4])='-'][1]")
    try:
        tr = W(driver, 12).until(EC.presence_of_element_located((By.XPATH, xp)))
        td4 = tr.find_element(By.XPATH, "./td[4]")
        hora = txt(tr, ".//td[3]//*[self::div or self::p or self::span][1]") or "?"
        return tr, td4, hora
    except TimeoutException:
        return None, None, None

def achar_campo_digitacao(driver):
    """Prioriza input em dialog/modal, senão pega o focado/global."""
    # focado
    try:
        active = driver.switch_to.active_element
        tag = (active.tag_name or "").lower()
        ce = (active.get_attribute("contenteditable") or "").lower() == "true"
        if tag in ("input", "textarea") or ce:
            return active
    except: pass
    # dialog/modal
    candidatos = [
        "//*[@role='dialog' or contains(@class,'Dialog') or contains(@class,'modal')]//input[not(@type) or @type='text' or @type='search']",
        "//*[@role='dialog']//div[@contenteditable='true']",
        "//div[contains(@class,'Dialog') or contains(@class,'modal')]//input[not(@type) or @type='text' or @type='search']",
    ]
    for xp in candidatos:
        try: return W(driver, 8).until(EC.visibility_of_element_located((By.XPATH, xp)))
        except TimeoutException: continue
    # global
    try: return W(driver, 6).until(EC.visibility_of_element_located((By.XPATH, "//input[not(@type) or @type='text' or @type='search']")))
    except TimeoutException: return None

def slow_type(el, text, per_char_delay=TYPE_DELAY):
    # limpa
    try:
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        time.sleep(0.15)
    except: pass
    for ch in text:
        el.send_keys(ch)
        time.sleep(per_char_delay)

def esperar_td4_preenchida(driver, hora, esperado=NOME_PARA_DIGITAR, timeout=10):
    """Espera a TD4 da linha 'hora' sair de '-' ou conter parte do esperado."""
    esperado_low = esperado.lower().split()[0]
    xp_td4 = ("//tbody/tr[td[3]//*[self::div or self::p or self::span]"
              f"[normalize-space()='{hora}']]/td[4]")
    try:
        # conter parte do nome
        W(driver, timeout).until(
            EC.text_to_be_present_in_element((By.XPATH, xp_td4), esperado_low)
        )
        return True
    except TimeoutException:
        pass
    try:
        # qualquer valor diferente de '-'
        W(driver, max(3, timeout//2)).until(
            lambda d: d.find_element(By.XPATH, xp_td4).get_attribute("textContent").strip() != "-"
        )
        return True
    except Exception:
        return False

def clicar_td4_digitar_esperar_enter(driver):
    """Clica TD4 (primeiro disponível '-'), digita nome, espera 3s e dá Enter."""
    esperar_tabela(driver)

    tr, td4, hora = encontrar_primeiro_tr_disponivel_td4_vazio(driver)
    if not tr:
        print("Nenhuma linha disponível com TD4 = '-' encontrada.")
        return False

    # clique na TD4 (e arma a linha se necessário)
    if not force_click(driver, td4):
        try:
            btn_status = tr.find_element(By.XPATH, ".//td[6]//button")
            js_click(driver, btn_status); time.sleep(0.25)
            if not force_click(driver, td4):
                print("Não consegui clicar na TD4.")
                return False
        except Exception:
            print("Não consegui preparar a linha para clique.")
            return False

    time.sleep(0.3)  # deixa o campo abrir

    # achar campo e digitar
    campo = achar_campo_digitacao(driver)
    if not campo:
        print("Não encontrei campo para digitar.")
        return False

    try: js_click(driver, campo)
    except: pass

    slow_type(campo, NOME_PARA_DIGITAR, TYPE_DELAY)

    # >>>>>>> ESPERA EXIGIDA (3s) ANTES DO ENTER <<<<<<<
    time.sleep(ENTER_DELAY)

    # Enter
    campo.send_keys(Keys.ENTER)

    # valida que a TD4 foi preenchida
    ok = esperar_td4_preenchida(driver, hora, NOME_PARA_DIGITAR, timeout=12)
    print("RESULTADO:", "SUCESSO" if ok else "FALHOU (TD4 não mudou após Enter)")
    return ok

# ======= MAIN =======
def main():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # opts.add_argument("--headless=new")  # opcional
    driver = webdriver.Chrome(options=opts)

    try:
        # limpa possíveis seleções antigas
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)

        clicar_td4_digitar_esperar_enter(driver)

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
