# t3_last_option_agendamento.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time, re

# ======= CONFIG =======
URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"

# Ciclo de pacientes: na ordem, recomeçando após o 4º


ESPERA_APOS_PACIENTE = 7.0
N_TABS = 8
ESPERA_APOS_TEXTO = 1.0

WAIT_DEFAULT = 20
TYPE_DELAY = 0.08
RETRIES_MENU = 3
ENTER_APOS_PROC = 1.0

# ======= HELPERS =======
def W(driver, t=WAIT_DEFAULT):
    return WebDriverWait(driver, t)

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

def press_tab_n_times(driver, n, delay=0.2):
    for _ in range(n):
        try:
            ActionChains(driver).send_keys(Keys.TAB).perform()
        except:
            try:
                driver.switch_to.active_element.send_keys(Keys.TAB)
            except:
                pass
        time.sleep(delay)

def slow_type(el, text, per_char_delay=TYPE_DELAY, clear_first=True):
    try:
        if clear_first:
            el.send_keys(Keys.CONTROL, "a"); el.send_keys(Keys.DELETE); time.sleep(0.15)
    except:
        pass
    for ch in text:
        el.send_keys(ch); time.sleep(per_char_delay)

def type_no_clear(el, text, per_char_delay=TYPE_DELAY):
    for ch in text:
        el.send_keys(ch); time.sleep(per_char_delay)

def close_popovers(driver, times=2):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(times):
            body.send_keys(Keys.ESCAPE); time.sleep(0.12)
    except:
        pass

def body_send(driver, *keys):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for k in keys:
            body.send_keys(k); time.sleep(0.05)
        return True
    except:
        return False

# ======= LOGIN / NAVEGAÇÃO =======
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
        titulo = li.find_element(By.XPATH, ".//span[contains(@class,'text-base') and contains(@class,'font-medium')]").text.strip()
        if titulo == nome:
            alvo = li; break
    if not alvo:
        raise RuntimeError(f"Não achei a clínica: {nome}")
    try:
        area = alvo.find_element(By.XPATH, ".//div[contains(@class,'px-8') and contains(@class,'py-6')]")
    except:
        area = alvo
    js_click(driver, area); time.sleep(0.35)

def ir_para_recepcao(driver):
    link = W(driver).until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link); time.sleep(0.45)

def esperar_tabela(driver):
    W(driver).until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))


# ======= BUSCA DAS LINHAS =======
XPATH_TR_DISPONIVEL_TD4_VAZIO = (
    "//tbody/tr[not(@data-disabled='true') and "
    "translate(normalize-space(.//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]),"
    " 'ÁÀÂÃÉÊÍÓÔÕÚÜÇABCDEFGHIJKLMNOPQRSTUVWXYZ',"
    " 'áàâãéêíóôõúüçabcdefghijklmnopqrstuvwxyz')='disponível' and "
    "normalize-space(.//td[4])='-']"
)

def reobter_tr(driver, antigo_tr=None):
    if antigo_tr is not None:
        try:
            _ = antigo_tr.is_displayed()
            return antigo_tr
        except StaleElementReferenceException:
            pass
        except Exception:
            pass
    try:
        return driver.find_element(By.XPATH, XPATH_TR_DISPONIVEL_TD4_VAZIO + "[1]")
    except Exception:
        return None

# Terceiro botão dentro do flex (Filtrar=1, Atualizar=2, Opções=3, Agendar=4)
def abrir_dropdown_opcoes(driver):
    """
    Abre o dropdown 'Opções'.
    Retorna (container, botao) ou (None, None) se não achou.
    """
    try:
        # encontra o botão pelo texto visível "Opções"
        btn = W(driver, 8).until(EC.presence_of_element_located((
            By.XPATH,
            "//button[contains(normalize-space(.), 'Opções') and @aria-haspopup='menu']"
        )))
    except TimeoutException:
        return None, None

    # tenta clicar até abrir
    for _ in range(4):
        if force_click(driver, btn):
            time.sleep(0.2)
            try:
                if (btn.get_attribute("aria-expanded") or "").lower() == "true":
                    return None, btn
            except StaleElementReferenceException:
                pass
            menus = driver.find_elements(By.XPATH, "//*[@role='menu' and (not(@hidden) or @data-state='open')]")
            if any(m.is_displayed() for m in menus):
                return None, btn
        time.sleep(0.15)

    return None, btn


def selecionar_opcao_menu_opcoes(driver, indice=5):
    """
    Seleciona a N-ésima opção (default=5ª) do dropdown 'Opções'.
    """
    cont, btn = abrir_dropdown_opcoes(driver)
    if btn is None:
        print("Não encontrei o botão 'Opções'.")
        return False

    # pega o menu aberto
    try:
        menu = W(driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, "//*[@role='menu' and (not(@hidden) or @data-state='open')]")
        ))
    except TimeoutException:
        print("Menu 'Opções' não apareceu.")
        return False

    # coleta itens visíveis clicáveis
    candidates = menu.find_elements(By.XPATH, ".//button[not(@disabled)] | .//*[@role='menuitem']")
    visibles = []
    for el in candidates:
        try:
            if driver.execute_script("const e=arguments[0]; return !!(e.offsetParent || e.getClientRects().length);", el):
                txt = (el.get_attribute("textContent") or "").strip()
                if txt:
                    visibles.append((el, txt))
        except StaleElementReferenceException:
            continue

    if not visibles:
        print("Nenhum item visível no menu 'Opções'.")
        return False

    if indice > len(visibles):
        print(f"O menu 'Opções' só tem {len(visibles)} opções, não existe a opção {indice}.")
        return False

    el, label = visibles[indice-1]
    if not force_click(driver, el):
        try:
            js_click(driver, el)
        except:
            pass

    # aguarda o menu fechar
    try:
        W(driver, 5).until(lambda d: (btn.get_attribute("aria-expanded") or "").lower() != "true")
    except Exception:
        pass

    print(f"Selecionado: {label}")
    return True



# ======= MAIN =======
def main():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # opts.add_argument("--headless=new")
    driver = webdriver.Chrome(options=opts)

    try:
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)
        # Abre Opções e seleciona a 5ª opção
        selecionar_opcao_menu_opcoes(driver, 5)

        # NOVO: abrir “Exibir:” e selecionar a ÚLTIMA opção antes de começar o fluxo
        
        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
