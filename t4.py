# t3.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time

URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"

# =================== helpers ===================

def W(driver, t=20):
    return WebDriverWait(driver, t)

def text(el, xp):
    try:
        return el.find_element(By.XPATH, xp).get_attribute("textContent").strip()
    except Exception:
        return ""

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def highlight(driver, el, color="red"):
    try:
        driver.execute_script("arguments[0].style.outline='3px solid %s';" % color, el)
    except Exception:
        pass

def force_click_sequence(driver, el):
    """Tenta várias formas de clicar no elemento. Retorna True se algum método 'pegar'."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    except Exception:
        pass

    # 1) Actions move+click (mais 'humano')
    try:
        ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
        return True
    except Exception:
        pass

    # 2) element.click()
    try:
        el.click()
        return True
    except Exception:
        pass

    # 3) JS click direto
    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass

    # 4) MouseEvents encadeados (para frameworks que ouvem eventos em bubbling)
    try:
        driver.execute_script("""
            const el = arguments[0];
            for (const type of ['pointerdown','mousedown','mouseup','click']) {
                const evt = new MouseEvent(type, {bubbles:true, cancelable:true, view:window});
                el.dispatchEvent(evt);
            }
        """, el)
        return True
    except Exception:
        pass

    # 5) Double click
    try:
        ActionChains(driver).move_to_element(el).double_click().perform()
        return True
    except Exception:
        pass

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
        titulo = text(li, ".//span[contains(@class,'text-base') and contains(@class,'font-medium')]")
        if titulo == nome:
            alvo = li; break

    if not alvo:
        raise RuntimeError(f"Não achei a clínica: {nome}")

    # clicar na área interna do card (robusto contra overlay/hover)
    try:
        area = alvo.find_element(By.XPATH, ".//div[contains(@class,'px-8') and contains(@class,'py-6')]")
    except Exception:
        area = alvo
    highlight(driver, area, "orange")
    js_click(driver, area)

def ir_para_recepcao(driver):
    link = W(driver).until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link)

def esperar_tabela(driver):
    W(driver).until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))

def encontrar_primeiro_tr_disponivel_td4_vazio(driver):
    """Retorna (tr, td4) do primeiro disponível com TD4='-'. Caso não exista, retorna (None, None)."""
    xp_row = ("//tbody/tr[not(@data-disabled='true') and "
              "normalize-space(.//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')])='disponível' and "
              "normalize-space(.//td[4])='-'][1]")
    try:
        tr = W(driver, 10).until(EC.presence_of_element_located((By.XPATH, xp_row)))
        td4 = tr.find_element(By.XPATH, "./td[4]")
        return tr, td4
    except TimeoutException:
        return None, None

def tentar_fluxo_click_td4(driver):
    """Executa o teste: clica na TD4 do primeiro disponível com '-', com várias estratégias e fallback."""
    esperar_tabela(driver)

    for tentativa in range(3):  # reforça contra re-render da UI
        tr, td4 = encontrar_primeiro_tr_disponivel_td4_vazio(driver)
        if not tr:
            print("Nenhuma linha disponível com TD4 = '-' foi encontrada.")
            return False

        hora = text(tr, ".//td[3]//*[self::div or self::p or self::span][1]") or "?"
        status = text(tr, ".//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]") or "?"
        print(f"Tentando clicar na TD4 da linha {hora} (status={status})...")

        highlight(driver, td4, "red")
        ok = force_click_sequence(driver, td4)
        if ok:
            print("Clique na TD4 disparado. Aguardando reação da UI...")
            # aguarde algum efeito (dialog/modal) OU mudança do conteúdo da TD4
            try:
                # aguarda modal/dialog OU mudança de conteúdo
                W(driver, 5).until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[@role='dialog' or contains(@class,'Dialog') or contains(@class,'modal')]")),
                    EC.text_to_be_present_in_element((By.XPATH, "//tbody/tr[not(@data-disabled='true')][1]/td[4]"), "")  # qualquer mudança quebra '-'
                ))
            except TimeoutException:
                pass
            return True

        # se falhou o clique direto na TD4, tenta clicar o botão de status e repetir
        try:
            btn_status = tr.find_element(By.XPATH, ".//td[6]//button")
            highlight(driver, btn_status, "blue")
            print("Clique direto falhou. Tentando primeiro clicar no botão de status 'disponível'...")
            js_click(driver, btn_status)
            time.sleep(0.3)  # pequena pausa para a UI reagir
        except Exception:
            pass

        # reitera para re-capturar os elementos (evita stale)
    print("Não consegui acionar o clique na TD4 após múltiplas tentativas.")
    return False

# =================== fluxo principal ===================

def main():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # opts.add_argument("--headless=new")  # opcional para rodar sem UI
    driver = webdriver.Chrome(options=opts)

    try:
        # limpar possíveis seleções antigas de unidade (sem deslogar)
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)

        sucesso = tentar_fluxo_click_td4(driver)
        print("RESULTADO:", "SUCESSO" if sucesso else "FALHOU")

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
