# t3.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time

# ======= CONFIG =======
URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"

# Ciclo de pacientes: na ordem, recomeçando após o 4º
PACIENTES = [
    {
        "nome": "TESTE NOVO PESSOA 1",
        "convenio": "particular",
        "procedimentos": ["consulta gratuita", "consulta geral", "consulta com medico"],
    },
    {
        "nome": "JOAO PAULO ARCANJO MEDEIROS",
        "convenio": "publico geral",
        "procedimentos": ["confirmação de cadastro", "consulta com clinico", "caixa alta procedimento"],
    },
    {
        "nome": "TESTE ERRO CADASTRO CPF",
        "convenio": "empresario",
        "procedimentos": ["teste de desconto", "caixa alta procedimento teste", "consulta geral oficial"],
    },
    {
        "nome": "joao erik",
        "convenio": "convenio",
        "procedimentos": ["proc", "123", "12", "1"],
    },
]

ESPERA_APOS_PACIENTE = 7.0   # espera antes de tabular
N_TABS = 8                   # quantidade de TABs até o campo de convênio
ESPERA_APOS_TEXTO = 1.0      # espera antes do Enter no convênio

WAIT_DEFAULT = 20
TYPE_DELAY = 0.08

# Retentativas para o dropdown da linha
RETRIES_MENU = 3

# Tempo entre digitar no Procedimento e confirmar
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
            body.send_keys(k)
            time.sleep(0.05)
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
    js_click(driver, area)
    time.sleep(0.35)

def ir_para_recepcao(driver):
    link = W(driver).until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link)
    time.sleep(0.45)

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

def encontrar_primeiro_tr_disponivel_td4_vazio(driver):
    try:
        tr = W(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_TR_DISPONIVEL_TD4_VAZIO + "[1]")))
        td4 = tr.find_element(By.XPATH, "./td[4]")
        return tr, td4
    except TimeoutException:
        return None, None

def existem_linhas_disponiveis(driver):
    try:
        linhas = driver.find_elements(By.XPATH, XPATH_TR_DISPONIVEL_TD4_VAZIO)
        return any(l.is_displayed() for l in linhas)
    except Exception:
        return False

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

def linha_deixou_de_atender_criterio(tr):
    try:
        td4 = tr.find_element(By.XPATH, "./td[4]")
        if td4.text.strip() != "-":
            return True
        status = tr.find_element(By.XPATH, ".//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]").text.strip().lower()
        if status != "disponível":
            return True
        return False
    except StaleElementReferenceException:
        return True
    except Exception:
        return False

# ======= TABLIST > PROCEDIMENTOS (1ª OPÇÃO) =======
def clicar_aba_procedimentos_tablist(driver):
    try:
        tablist_xp = ("//div[@role='tablist' and .//button[@role='tab' and "
                      "(contains(normalize-space(.),'Procedimentos') "
                      " or contains(@id,'trigger-procedures') "
                      " or contains(@aria-controls,'content-procedures'))]]")
        tablist = W(driver, 3).until(EC.presence_of_element_located((By.XPATH, tablist_xp)))
    except TimeoutException:
        return False

    driver.execute_script("arguments[0].scrollIntoView({block:'nearest', inline:'start'});", tablist)
    time.sleep(0.08)

    btn = tablist.find_element(By.XPATH, ".//button[@role='tab' and (contains(normalize-space(.),'Procedimentos') or contains(@id,'trigger-procedures') or contains(@aria-controls,'content-procedures'))]")
    state = (btn.get_attribute("aria-selected") or "").lower()
    if state == "true" or (btn.get_attribute("data-state") or "").lower() == "active":
        print("Aba 'Procedimentos' já ativa (tablist).")
        return True

    if not force_click(driver, btn):
        js_click(driver, btn)

    W(driver, 5).until(lambda d: (btn.get_attribute("aria-selected") == "true") or ((btn.get_attribute("data-state") or "").lower() == "active"))
    print("Aba 'Procedimentos' ativada (tablist).")
    return True

# ======= DROPDOWN DA LINHA (2ª OPÇÃO) =======
def abrir_menu_da_linha(driver, tr):
    cand_xps = [
        ".//td[2]//button[@aria-haspopup='menu']",
        ".//button[@aria-haspopup='menu']",
        ".//button[contains(@id,'radix-') and @aria-haspopup='menu']",
        ".//button[.//svg[contains(@class,'lucide-ellipsis-vertical')]]",
    ]
    for xp in cand_xps:
        try:
            btn = tr.find_element(By.XPATH, xp)
            if btn.is_displayed():
                try:
                    js_click(driver, btn)
                except:
                    force_click(driver, btn)
                return True
        except Exception:
            continue
    return False

def esperar_menu_visivel(driver, timeout=4.0):
    end = time.time() + timeout
    ultimo_count = -1
    while time.time() < end:
        menus = [m for m in driver.find_elements(By.XPATH, "//*[@role='menu']") if m.is_displayed()]
        if menus:
            if len(menus) == ultimo_count:
                return menus[0]
            ultimo_count = len(menus)
        time.sleep(0.08)
    return None

def tentar_click_procedimentos_sem_mouse(driver):
    item_xps = [
        "//*[@role='menu']//*[self::div or self::a or self::button or self::span][contains(normalize-space(translate(., 'PROCEDIMENTOS', 'procedimentos')),'procedimentos')]",
        "//*[contains(@data-radix-portal,'') or contains(@id,'radix-')][//*[@role='menu']]//*[@role='menu']//*[self::div or self::a or self::button or self::span][contains(normalize-space(translate(., 'PROCEDIMENTOS', 'procedimentos')),'procedimentos')]",
        "//*[@role='menu']//*[@role='menuitem' and contains(normalize-space(translate(., 'PROCEDIMENTOS', 'procedimentos')),'procedimentos')]",
    ]
    for xp in item_xps:
        try:
            itens = [e for e in driver.find_elements(By.XPATH, xp) if e.is_displayed()]
            for el in itens:
                try:
                    driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    return False

def tentar_selecionar_por_teclado(driver):
    try:
        menu = [m for m in driver.find_elements(By.XPATH, "//*[@role='menu']") if m.is_displayed()][0]
    except IndexError:
        return False
    try:
        driver.execute_script("arguments[0].focus();", menu)
    except:
        try: menu.click()
        except: pass
    time.sleep(0.05)

    itens = [e for e in menu.find_elements(By.XPATH, ".//*[@role='menuitem' or self::button or self::a or self::div]") if e.is_displayed()]
    alvo_idx = None
    for i, e in enumerate(itens):
        try:
            txt = (e.text or "").strip().lower()
            if "procedimentos" in txt:
                alvo_idx = i; break
        except:
            continue

    if alvo_idx is None:
        return False

    body_send(driver, Keys.HOME)
    for _ in range(alvo_idx):
        body_send(driver, Keys.ARROW_DOWN)
    body_send(driver, Keys.ENTER)
    return True

def abrir_dropdown_e_clicar_procedimentos(driver, tr):
    for tentativa in range(1, RETRIES_MENU + 1):
        close_popovers(driver, 1)
        tr_ok = reobter_tr(driver, tr)
        if tr_ok is None:
            print("TR sumiu; não consigo abrir o menu.")
            return False

        if not abrir_menu_da_linha(driver, tr_ok):
            print("Não achei o botão de menu da linha.")
            return False

        menu = esperar_menu_visivel(driver, timeout=4.0)
        if not menu:
            print(f"Menu não estabilizou (tentativa {tentativa}). Reabrindo…")
            continue

        if tentar_click_procedimentos_sem_mouse(driver):
            print("‘Procedimentos’ clicado via JS dentro do dropdown.")
            return True

        if tentar_selecionar_por_teclado(driver):
            print("‘Procedimentos’ selecionado via teclado no dropdown.")
            return True

        print(f"Falha ao acionar ‘Procedimentos’ (tentativa {tentativa}). Tentando reabrir…")
        time.sleep(0.15)

    print("Não consegui acionar ‘Procedimentos’ pelo dropdown após várias tentativas.")
    return False

# ======= SUPORTE: Procedimento (React-Select) =======
def localizar_input_procedimento(driver):
    preferidos = [
        "//*[@id='react-select-10-input']",
        "//div[contains(@class,'css-7x0oty')]//input[@role='combobox' and starts-with(@id,'react-select-') and contains(@id,'-input')]",
        "//span[normalize-space()='Procedimento']/ancestor::div[contains(@class,'flex')][1]//input[starts-with(@id,'react-select-') and contains(@id,'-input')]",
        "//input[starts-with(@id,'react-select-') and contains(@id,'-input')]",
    ]
    for xp in preferidos:
        try:
            el = driver.find_element(By.XPATH, xp)
            if el.is_displayed():
                return el
        except Exception:
            continue
    try:
        return driver.switch_to.active_element
    except Exception:
        return None

def _proc_root_from_input(inp):
    try:
        return inp.find_element(By.XPATH, "./ancestor::div[contains(@class,'css-1dyz3mf') or contains(@class,'css-1ki6ao3-control')][1]")
    except Exception:
        return inp

def contar_chips_procedimento(inp):
    try:
        root = _proc_root_from_input(inp)
        chips = root.find_elements(By.XPATH, ".//*[@aria-label and starts-with(@aria-label,'Remove ')]")
        return len([c for c in chips if c.is_displayed()])
    except Exception:
        return 0

def listbox_visivel(driver):
    try:
        els = driver.find_elements(By.XPATH, "//*[@role='listbox' or contains(@id,'-listbox')]")
        return any(e.is_displayed() for e in els)
    except Exception:
        return False

def selecionar_opcao_por_click(driver, texto):
    try:
        W(driver, 3).until(EC.visibility_of_element_located(
            (By.XPATH, "//*[@role='listbox']//*[contains(@id,'-option-')][1]")))
        candidatos = [e for e in driver.find_elements(By.XPATH, "//*[@role='listbox']//*[contains(@id,'-option-')]") if e.is_displayed()]
        if not candidatos:
            return False
        alvo = candidatos[0]
        for e in candidatos:
            try:
                if texto.strip().lower() in (e.text or "").strip().lower():
                    alvo = e; break
            except:
                continue
        js_click(driver, alvo)
        return True
    except TimeoutException:
        return False
    except Exception:
        return False

def confirmar_opcao_sem_duplicar(driver, inp, texto, count_antes, timeout=3.5):
    end = time.time() + 1.0
    while time.time() < end and not listbox_visivel(driver):
        time.sleep(0.05)

    clicou = False
    if listbox_visivel(driver):
        clicou = selecionar_opcao_por_click(driver, texto)

    if not clicou:
        try:
            inp.send_keys(Keys.ENTER)
        except: 
            pass

    limite = time.time() + timeout
    while time.time() < limite:
        if contar_chips_procedimento(inp) >= count_antes + 1:
            return True
        time.sleep(0.1)
    return contar_chips_procedimento(inp) >= count_antes + 1

def agendamento_modal_visivel(driver):
    try:
        header = driver.find_element(By.XPATH, "//h1[.//span[normalize-space()='Agendamento']]")
        return header.is_displayed()
    except Exception:
        return False

def fechar_preparo_obs_se_aparecer(driver, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            popup = driver.find_element(
                By.XPATH,
                "//*[contains(@class,'fixed') and .//h2[normalize-space()='Preparo/Obs']]"
            )
            if popup.is_displayed():
                header = popup.find_element(
                    By.XPATH,
                    ".//div[contains(@class,'border-b')][.//h2[normalize-space()='Preparo/Obs']]"
                )
                try:
                    btn_close = header.find_element(By.XPATH, ".//button[.//svg[contains(@class,'lucide-x')]]")
                except Exception:
                    btn_close = header.find_element(By.XPATH, ".//button")
                driver.execute_script("arguments[0].click();", btn_close)
                W(driver, 3).until(EC.invisibility_of_element(popup))
                time.sleep(0.15)
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False

def adicionar_itens_procedimento(driver, itens):
    for idx, texto in enumerate(itens, start=1):
        proc_input = localizar_input_procedimento(driver)
        if not proc_input:
            print("Não localizei o input do 'Procedimento'.")
            return False
        try: js_click(driver, proc_input)
        except: force_click(driver, proc_input)
        time.sleep(0.10)

        chips_antes = contar_chips_procedimento(proc_input)
        type_no_clear(proc_input, str(texto), per_char_delay=TYPE_DELAY)
        time.sleep(ENTER_APOS_PROC)

        ok = confirmar_opcao_sem_duplicar(driver, proc_input, str(texto), chips_antes, timeout=3.5)
        if not ok:
            print(f"Não consegui confirmar o item '{texto}' (sem duplicar).")
            return False

        time.sleep(1.0)
        _ = fechar_preparo_obs_se_aparecer(driver, timeout=1.0)

        print(f"Item {idx}/{len(itens)} adicionado: {texto}")
    return True

def clicar_botao_adicionar_no_modal(driver):
    try:
        btn_add = W(driver, 6).until(EC.element_to_be_clickable((
            By.XPATH,
            "//h1[.//span[normalize-space()='Agendamento']]/ancestor::form[1]//button[normalize-space()='Adicionar']"
        )))
        js_click(driver, btn_add)
    except TimeoutException:
        print("Botão 'Adicionar' do modal não encontrado/clicável.")
        return False
    except Exception:
        try:
            btn_add = driver.find_element(By.XPATH, "//h1[.//span[normalize-space()='Agendamento']]/ancestor::form[1]//button[normalize-space()='Adicionar']")
            force_click(driver, btn_add)
        except Exception:
            print("Falhou ao clicar em 'Adicionar'.")
            return False

    try:
        W(driver, 5).until(EC.presence_of_element_located((
            By.XPATH,
            "//h1[.//span[normalize-space()='Agendamento']]/ancestor::form[1]//table//tbody/tr"
        )))
    except TimeoutException:
        print("Aviso: não observei linhas na tabela após 'Adicionar'. Seguindo…")
    return True

def clicar_botao_confirmar_no_modal(driver):
    try:
        btn_confirm = W(driver, 6).until(EC.element_to_be_clickable((
            By.XPATH,
            "//h1[.//span[normalize-space()='Agendamento']]/ancestor::form[1]//button[@type='submit' and normalize-space()='Confirmar']"
        )))
        js_click(driver, btn_confirm)
    except TimeoutException:
        print("Botão 'Confirmar' do modal não encontrado/clicável.")
        return False
    except Exception:
        try:
            btn_confirm = driver.find_element(By.XPATH, "//h1[.//span[normalize-space()='Agendamento']]/ancestor::form[1]//button[@type='submit' and normalize-space()='Confirmar']")
            force_click(driver, btn_confirm)
        except Exception:
            print("Falhou ao clicar em 'Confirmar'.")
            return False

    try:
        header = driver.find_element(By.XPATH, "//h1[.//span[normalize-space()='Agendamento']]")
        W(driver, 8).until(EC.invisibility_of_element(header))
    except Exception:
        pass

    return True

# ======= PROCESSAR UMA LINHA (com paciente específico) =======
def processar_linha(driver, tr, td4, paciente):
    # 1) clicar TD4
    if not force_click(driver, td4):
        try:
            btn_status = tr.find_element(By.XPATH, ".//td[6]//button")
            js_click(driver, btn_status); time.sleep(0.22)
            if not force_click(driver, td4):
                print("Não consegui clicar na TD4.")
                return False
        except Exception:
            print("Não consegui preparar a linha para clique.")
            return False

    time.sleep(0.30)

    # 2) digitar paciente
    try:
        campo = driver.switch_to.active_element
    except Exception:
        campo = None
    if not campo or (campo.tag_name.lower() not in ("input","textarea") and (campo.get_attribute("contenteditable") or "").lower() != "true"):
        try:
            campo = W(driver, 8).until(EC.visibility_of_element_located((By.XPATH, "//input[not(@type) or @type='text' or @type='search']")))
        except TimeoutException:
            print("Não encontrei campo para digitar o paciente.")
            return False
    try: js_click(driver, campo)
    except: pass
    slow_type(campo, paciente["nome"])

    # 3) espera 7s
    time.sleep(ESPERA_APOS_PACIENTE)

    # 4) TABs até convênio
    press_tab_n_times(driver, N_TABS, delay=0.25)

    # 5) digita convênio do paciente e Enter
    try:
        alvo = driver.switch_to.active_element
        alvo.send_keys(paciente["convenio"])
        time.sleep(ESPERA_APOS_TEXTO)
        alvo.send_keys(Keys.ENTER)
    except Exception:
        print("Falha ao enviar convênio + Enter.")
        return False

    print(f"Base ok ({paciente['nome']} / convênio: {paciente['convenio']}). Abrindo Procedimentos…")

    # 6) Abre Procedimentos (tablist preferencial, senão dropdown da linha)
    time.sleep(0.35)
    if not clicar_aba_procedimentos_tablist(driver):
        if not abrir_dropdown_e_clicar_procedimentos(driver, tr):
            return False

    # 7) Adiciona itens no campo Procedimento conforme o paciente
    if not adicionar_itens_procedimento(driver, paciente["procedimentos"]):
        print("Falha ao adicionar itens de Procedimento.")
        return False

    # 8) Adicionar -> (fecha Preparo/Obs se abrir) -> Confirmar
    if not clicar_botao_adicionar_no_modal(driver):
        print("Falha no botão 'Adicionar' do modal.")
        return False
    _ = fechar_preparo_obs_se_aparecer(driver, timeout=2.0)
    if not clicar_botao_confirmar_no_modal(driver):
        print("Falha no botão 'Confirmar' do modal.")
        return False

    # 9) Aguarda esta linha deixar de ser “disponível / '-'”
    try:
        W(driver, 8).until(lambda d: linha_deixou_de_atender_criterio(tr))
    except Exception:
        pass

    print(f"Linha processada com sucesso para: {paciente['nome']}.")
    return True

# ======= FLUXO PRINCIPAL (TODAS AS LINHAS) =======
def fluxo(driver):
    esperar_tabela(driver)
    processadas = 0
    tentativas_vazias = 0

    while True:
        tr, td4 = encontrar_primeiro_tr_disponivel_td4_vazio(driver)
        if not tr:
            tentativas_vazias += 1
            if tentativas_vazias >= 2:
                print("Sem mais linhas disponíveis com TD4='-'. Encerrando.")
                break
            time.sleep(0.8)
            continue

        tentativas_vazias = 0  # reset

        # Seleciona o paciente respeitando a ordem e repetição
        paciente = PACIENTES[processadas % len(PACIENTES)]
        print(f"==> Próximo agendamento será de: {paciente['nome']}")

        ok = processar_linha(driver, tr, td4, paciente)
        if ok:
            processadas += 1
            # pequena folga pra UI
            time.sleep(0.5)
        else:
            # Se falhar, tenta seguir pra próxima linha (evitar loop infinito)
            print("Falha ao processar uma linha; tentando a próxima.")
            time.sleep(0.8)

        # Se ainda existem linhas, o loop continua; senão sai
        if not existem_linhas_disponiveis(driver):
            print("Todas as linhas elegíveis foram processadas.")
            break

    print(f"Total de linhas processadas: {processadas}")
    return processadas > 0

# ======= MAIN =======
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

        login(driver)
        selecionar_clinica(driver, CLINICA)
        ir_para_recepcao(driver)

        fluxo(driver)

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
