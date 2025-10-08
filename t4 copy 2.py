# t3_fix_last_option.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import re

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

    try:
        ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
        return True
    except Exception:
        pass

    try:
        el.click()
        return True
    except Exception:
        pass

    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass

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

    try:
        ActionChains(driver).move_to_element(el).double_click().perform()
        return True
    except Exception:
        pass

    return False

# =================== fluxo original (mantido) ===================

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

    for tentativa in range(3):
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
            try:
                W(driver, 5).until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[@role='dialog' or contains(@class,'Dialog') or contains(@class,'modal')]")),
                    EC.text_to_be_present_in_element((By.XPATH, "//tbody/tr[not(@data-disabled='true')][1]/td[4]"), "")
                ))
            except TimeoutException:
                pass
            return True

        try:
            btn_status = tr.find_element(By.XPATH, ".//td[6]//button")
            highlight(driver, btn_status, "blue")
            print("Clique direto falhou. Tentando primeiro clicar no botão de status 'disponível'...")
            js_click(driver, btn_status)
            time.sleep(0.3)
        except Exception:
            pass

    print("Não consegui acionar o clique na TD4 após múltiplas tentativas.")
    return False

# =================== Paginação "Exibir:" ===================

def abrir_dropdown_exibir(driver):
    """
    Abre o seletor 'Exibir:' na paginação do grid.
    """
    try:
        pag = W(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'sc-hknOHE')]//div[contains(@class,'px-6')]")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pag)
        time.sleep(0.2)
    except TimeoutException:
        print("Paginação não encontrada (seguindo).")
        return None, None

    try:
        btn = pag.find_element(By.XPATH, ".//p[normalize-space()='Exibir:']/following-sibling::button[1]")
    except Exception:
        try:
            btn = pag.find_element(By.XPATH, ".//button[@aria-haspopup='menu']")
        except Exception:
            print("Botão 'Exibir:' não encontrado (seguindo).")
            return pag, None

    highlight(driver, btn, "green")

    for _ in range(4):
        if force_click_sequence(driver, btn):
            time.sleep(0.2)
            try:
                if btn.get_attribute("aria-expanded") == "true":
                    print("Dropdown 'Exibir:' aberto (aria-expanded=true).")
                    return pag, btn
            except StaleElementReferenceException:
                pass
            menus_abertos = driver.find_elements(By.XPATH, "//*[@role='menu' and (not(@hidden) or @data-state='open')]")
            if menus_abertos:
                print("Dropdown 'Exibir:' aberto (role=menu visível).")
                return pag, btn
        # re-localiza
        try:
            btn = pag.find_element(By.XPATH, ".//p[normalize-space()='Exibir:']/following-sibling::button[1]")
        except Exception:
            try:
                btn = pag.find_element(By.XPATH, ".//button[@aria-haspopup='menu']")
            except Exception:
                pass
        time.sleep(0.15)

    print("Não consegui abrir o dropdown 'Exibir:'.")
    return pag, btn

def selecionar_ultima_opcao_exibir(driver):
    """
    Seleciona a ÚLTIMA opção disponível do menu 'Exibir:' (sem número fixo).
    Robusto para Radix UI: procura qualquer menu aberto e pega o último item clicável.
    """
    # garante que o menu está aberto
    pag, btn = abrir_dropdown_exibir(driver)
    if btn is None:
        return False

    # pega qualquer menu aberto (Radix geralmente cria portal com role="menu")
    try:
        menu = W(driver, 5).until(EC.presence_of_element_located(
            (By.XPATH, "//*[@role='menu' and (not(@hidden) or @data-state='open')]")
        ))
    except TimeoutException:
        print("Menu 'Exibir:' não apareceu.")
        return False

    # candidatos a itens clicáveis dentro do menu
    # 1) qualquer <button> visível
    # 2) qualquer [role='menuitem'] visível
    candidates = menu.find_elements(By.XPATH, ".//button[not(@disabled)] | .//*[@role='menuitem']")
    # filtra por visibilidade real via JS (offsetParent) para evitar itens escondidos
    visibles = []
    for el in candidates:
        try:
            visible = driver.execute_script(
                "const e=arguments[0]; return !!(e.offsetParent || e.getClientRects().length);", el
            )
            if visible:
                txt = el.get_attribute("textContent").strip()
                # ignorar itens vazios
                if txt:
                    visibles.append((el, txt))
        except StaleElementReferenceException:
            continue

    if not visibles:
        print("Nenhum item visível no menu 'Exibir:'.")
        return False

    # escolhe o ÚLTIMO (sem assumir número)
    el, label = visibles[-1]
    print(f"Selecionando última opção do 'Exibir:': {label!r}")
    highlight(driver, el, "purple")

    if not force_click_sequence(driver, el):
        print("Falha ao clicar na última opção do 'Exibir:'.")
        return False

    # aguarda fechamento do menu e/ou mudança no botão
    try:
        W(driver, 5).until(lambda d: btn.get_attribute("aria-expanded") != "true")
    except Exception:
        pass

    # pequena espera para a tabela recarregar (se houver paginação por page size)
    time.sleep(0.5)

    # valida: texto do botão deve refletir o novo valor (se ele renderiza o valor dentro do botão)
    try:
        btn_txt = btn.get_attribute("textContent").strip()
        # alguns temas mantêm ícone junto; garantimos que o número da opção está contido
        num_in_label = re.search(r"\d+", label)
        if num_in_label and num_in_label.group(0) in btn_txt:
            print("Confirmação: botão 'Exibir:' atualizou para", btn_txt)
    except Exception:
        pass

    return True

# =================== fluxo principal ===================

def main():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    # opts.add_argument("--headless=new")  # opcional
    driver = webdriver.Chrome(options=opts)

    try:
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        # fluxo original
        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)

        # abrir dropdown e escolher a ÚLTIMA opção
        selecionar_ultima_opcao_exibir(driver)

        # segue o seu teste de clicar TD4 '-'
        sucesso = tentar_fluxo_click_td4(driver)
        print("RESULTADO:", "SUCESSO" if sucesso else "FALHOU")

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
