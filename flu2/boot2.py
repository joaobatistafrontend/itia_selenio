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

def fechar_toasts(driver, timeout=6):
    """
    Fecha toasts do Toastify que possam atrapalhar cliques (ex.: 'Sucesso / Seja bem-vindo').
    1) Tenta clicar no botão de fechar.
    2) Se não der, envia ESC algumas vezes.
    3) Como último recurso, remove via JS.
    Aguarda sumirem para continuar.
    """
    fim = time.time() + timeout
    fechou_algum = False

    while time.time() < fim:
        try:
            # pega todos os toasts visíveis
            toasts = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'Toastify__toast') and not(contains(@style,'display: none'))]"
            )

            if not toasts:
                # nada visível, sucesso
                break

            # tenta fechar cada um
            for t in toasts:
                try:
                    close_btn = t.find_element(By.XPATH, ".//button[contains(@class,'Toastify__close-button')]")
                    if driver.execute_script(
                        "const e=arguments[0];return !!(e.offsetParent||e.getClientRects().length);", close_btn
                    ):
                        if not force_click(driver, close_btn):
                            js_click(driver, close_btn)
                        fechou_algum = True
                        time.sleep(0.1)
                except Exception:
                    # fallback: ESC
                    body_send(driver, Keys.ESCAPE)
                    time.sleep(0.1)

            # espera desaparecerem
            try:
                WebDriverWait(driver, 2).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".Toastify__toast"))
                )
                break
            except Exception:
                # último recurso: remover via JS (caso travem)
                try:
                    driver.execute_script("""
                        document.querySelectorAll('.Toastify__toast').forEach(t => t.remove());
                    """)
                except Exception:
                    pass

        except Exception:
            pass

        time.sleep(0.1)

    if fechou_algum:
        print("Toasts fechados.")


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
def clicar_primeiro_item_tabela(driver, timeout=10):
    """
    Clica no primeiro link (<a>) da primeira linha visível da tabela.
    Retorna o texto do link clicado (útil para log) ou None se não encontrar.
    """
    try:
        # espera ter ao menos uma linha na tabela
        W(driver, timeout).until(EC.presence_of_element_located((By.XPATH, "//tbody/tr")))
        # pega a primeira linha visível
        primeira_tr = W(driver, timeout).until(
            EC.presence_of_element_located((
                By.XPATH,
                "(//tbody/tr[not(@data-disabled='true')])[1]"
            ))
        )

        # dentro da linha, procura Âncoras visíveis; prioriza as que apontam para /apps/settings/schedule/
        anchors = primeira_tr.find_elements(By.XPATH, ".//a")
        visiveis = []
        for a in anchors:
            try:
                if driver.execute_script("const e=arguments[0];return !!(e.offsetParent||e.getClientRects().length);", a):
                    visiveis.append(a)
            except Exception:
                continue

        if not visiveis:
            print("Nenhum link visível na primeira linha da tabela.")
            return None

        # tenta ancoras que parecem ser o destino certo
        alvo = None
        for a in visiveis:
            href = (a.get_attribute("href") or "")
            if "/apps/settings/schedule/" in href:
                alvo = a
                break

        # se não achou por filtro, vai no primeiro link visível mesmo
        if alvo is None:
            alvo = visiveis[0]

        texto = (alvo.text or "").strip()
        if not force_click(driver, alvo):
            js_click(driver, alvo)

        print(f"Cliquei no primeiro item da tabela: {texto or '[sem texto]'}")
        return texto or None

    except TimeoutException:
        print("Tabela não apareceu a tempo.")
        return None
    except Exception as e:
        print(f"Falha ao clicar no primeiro item da tabela: {e}")
        return None

# def cadastrar_nova_entrada(driver, dia_semana, timeout=10):
#     """
#     Fluxo:
#       - Clica no botão 'Cadastrar nova'
#       - Preenche: dia da semana, clínica, 0800, 1700, 10
#       - Confirma com Enter
#     """
#     try:
#         # 1. Clicar no botão "Cadastrar nova"
#         btn = W(driver, timeout).until(EC.element_to_be_clickable((
#             By.XPATH,
#             "//button[.//span[normalize-space()='Cadastrar nova']]"
#         )))
#         if not force_click(driver, btn):
#             js_click(driver, btn)
#         time.sleep(0.5)

#         # 2. Dia da semana
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         time.sleep(0.2)
#         ActionChains(driver).send_keys(dia_semana).perform()
#         time.sleep(0.3)

#         # 3. Clínica
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         time.sleep(0.2)
#         ActionChains(driver).send_keys(CLINICA).perform()
#         time.sleep(0.3)

#         # 4. Horário inicial (0800)
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         time.sleep(0.2)
#         ActionChains(driver).send_keys("0800").perform()
#         time.sleep(0.3)

#         # 5. Horário final (1700)
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         time.sleep(0.2)
#         ActionChains(driver).send_keys("1700").perform()
#         time.sleep(0.3)

#         # 6. Quantidade (10)
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         ActionChains(driver).send_keys(Keys.TAB).perform()
#         time.sleep(0.2)
#         ActionChains(driver).send_keys("10").perform()
#         time.sleep(0.3)

#         # 7. Enter para confirmar
#         ActionChains(driver).send_keys(Keys.ENTER).perform()
#         print("Cadastro feito com sucesso!")

#     except Exception as e:
#         print(f"Erro ao cadastrar nova entrada: {e}")

DIAS_PT = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}
def fluxo_cadastrar_nova(driver, dia_semana=None, timeout=12):
    """
    Fecha toasts -> clica 'Cadastrar nova' -> preenche (TABs):
      [Dia da semana] -> [CLINICA] -> [0800] -> [1700] -> [10] -> ENTER
    Tudo em UMA função.
    """
    # -------- helpers internos --------
    def _wait_click_cadastrar():
        xpaths = [
            "//button[.//span[normalize-space()='Cadastrar nova'] and not(@disabled)]",
            "(//span[normalize-space()='Cadastrar nova']/ancestor::button[1][not(@disabled)])[1]",
            "//div[contains(@class,'sc-jBqsNv')]//button[.//span[normalize-space()='Cadastrar nova'] and not(@disabled)]",
            "//button[normalize-space()='Cadastrar nova' and not(@disabled)]",
        ]
        btn = None; last_err = None
        for xp in xpaths:
            try:
                btn = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                ); break
            except Exception as e:
                last_err = e; continue
        if not btn:
            raise TimeoutException(f"Não achei botão 'Cadastrar nova' clicável. Detalhe: {last_err}")
        if not force_click(driver, btn):
            js_click(driver, btn)
        time.sleep(0.35)

    def _ensure_form_focus():
        """Garante que estamos com foco em algum input. Dá TAB até cair num input/textarea/select."""
        for _ in range(6):
            active = driver.switch_to.active_element
            tag = (active.tag_name or "").lower()
            if tag in ("input", "textarea", "select"):
                return True
            ActionChains(driver).send_keys(Keys.TAB).perform()
            time.sleep(0.15)
        return False

    def _type(text):
        ActionChains(driver).send_keys(text).perform()
        time.sleep(0.25)

    # -------- execução --------
    try:
        # 0) Fecha toasts que possam atrapalhar
        try:
            fechar_toasts(driver, timeout=3)
        except Exception:
            pass

        # 1) Espera a página do item carregar algo típico (a própria barra de ações com os botões)
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'sc-jBqsNv')]"))
            )
        except Exception:
            pass  # segue mesmo assim

        # 2) Clica no 'Cadastrar nova'
        _wait_click_cadastrar()

        # 3) Dia da semana (default: dia atual)
        if dia_semana is None:
            import datetime as _dt
            dia_semana = DIAS_PT[_dt.datetime.today().weekday()]

        # 4) Garante foco no primeiro campo; se ainda não estiver, dá um TAB inicial
        if not _ensure_form_focus():
            ActionChains(driver).send_keys(Keys.TAB).perform()
            time.sleep(0.2)

        # Sequência pedida:
        # TAB -> DIA
        # TAB -> CLINICA (+ ENTER para confirmar)
        # TAB -> 0800
        # TAB TAB -> 1700
        # TAB TAB -> 10
        # ENTER

        # DIA
        _type(dia_semana)
        ActionChains(driver).send_keys(Keys.TAB).perform(); time.sleep(0.15)

        # CLINICA
        ActionChains(driver).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        _type(CLINICA)

        # ✅ ADICIONADO: ENTER após digitar a clínica (confirma autocomplete/seleção)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(0.2)

        # # 0800
        ActionChains(driver).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        _type("0800")

        # # 1700
        ActionChains(driver).send_keys(Keys.TAB).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        _type("1700")

        # # 10
        ActionChains(driver).send_keys(Keys.TAB).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        _type("10")

        # # ENTER (confirmar)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(0.4)

        
        # CONFIRMAR CLÍNICA (ENTER), depois TAB, ↓, ENTER (como você pediu)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(0.2)
        ActionChains(driver).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform(); time.sleep(0.15)
        ActionChains(driver).send_keys(Keys.ENTER).perform(); time.sleep(0.2)

        ActionChains(driver).send_keys(Keys.TAB).perform(); time.sleep(0.15)
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform(); time.sleep(0.15)
        ActionChains(driver).send_keys(Keys.ENTER).perform(); time.sleep(0.2)

        ActionChains(driver).send_keys(Keys.ENTER).perform(); time.sleep(0.2)
        # Fecha eventual toast de sucesso para não atrapalhar próximos cliques
        try:
            fechar_toasts(driver, timeout=2)
        except Exception:
            pass

        print("Fluxo 'Cadastrar nova' executado com sucesso.")
        return True

    except Exception as e:
        print(f"[fluxo_cadastrar_nova] Falhou: {e}")
        return False

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

        # FECHA o toast 'Sucesso / Seja bem-vindo' que aparece após escolher a clínica
        fechar_toasts(driver, timeout=6)

        ir_para_recepcao(driver)

        # Abre Opções e seleciona a 5ª opção
        selecionar_opcao_menu_opcoes(driver, 5)

        # Aguarda a tabela e clica no primeiro item (primeira linha -> primeiro <a>)
        clicar_primeiro_item_tabela(driver, timeout=12)
        # Preenche o cadastro novo
        # executa tudo em uma função
        fluxo_cadastrar_nova(driver)  # usa o dia atual; passe dia_semana="Terça-feira" se quiser forçar

        # NOVO: abrir “Exibir:” e selecionar a ÚLTIMA opção antes de começar o fluxo
        # (adicione aqui quando quiser)

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
