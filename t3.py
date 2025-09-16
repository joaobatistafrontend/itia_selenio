# t3.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

URL = "https://qa.app.saudehd.com.br/apps/reception/home"
USUARIO = "estagiarios1@healthdev.io"
SENHA = "123456"
CLINICA = "CLINICA MÉDICA DO CEARÁ"

# ----------------- helpers -----------------
def wait_for(driver, timeout=20):
    return WebDriverWait(driver, timeout)

def txt(el, xp):
    try:
        return el.find_element(By.XPATH, xp).get_attribute("textContent").strip()
    except Exception:
        return ""

def attr(el, xp, name):
    try:
        return el.find_element(By.XPATH, xp).get_attribute(name)
    except Exception:
        return ""

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def login(driver):
    w = wait_for(driver)
    driver.get(URL)
    user = w.until(EC.presence_of_element_located((By.NAME, "username")))
    pwd = driver.find_element(By.NAME, "password")
    user.send_keys(USUARIO)
    pwd.send_keys(SENHA)
    driver.find_element(By.XPATH, "//button[normalize-space()='Entrar']").click()

def select_clinic(driver, nome):
    # espere os cards de unidade
    w = wait_for(driver)
    cards = w.until(EC.presence_of_all_elements_located(
        (By.XPATH, "//ul[contains(@class,'flex')]/li[contains(@class,'group')]")
    ))

    alvo = None
    for li in cards:
        title = ""
        try:
            title = li.find_element(
                By.XPATH, ".//span[contains(@class,'text-base') and contains(@class,'font-medium')]"
            ).get_attribute("textContent").strip()
        except Exception:
            pass
        if title == nome:  # comparação exata evita “UNIDADE 2”
            alvo = li
            break

    if not alvo:
        raise RuntimeError(f"Não achei o card da clínica: {nome}")

    # clique robusto na área interna do card (evita hover/overlays)
    try:
        area_click = alvo.find_element(By.XPATH, ".//div[contains(@class,'px-8') and contains(@class,'py-6')]")
    except Exception:
        area_click = alvo
    js_click(driver, area_click)

def ir_para_recepcao(driver):
    w = wait_for(driver)
    link = w.until(EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='Recepção']/ancestor::a")))
    js_click(driver, link)

def abrir_paginacao_2_se_existir(driver):
    w = wait_for(driver, timeout=5)
    try:
        btn2 = w.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='2' and @data-state='closed']")))
        js_click(driver, btn2)
    except TimeoutException:
        pass  # não há página 2, segue

def coletar_linhas(driver):
    w = wait_for(driver)
    w.until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))
    trs = driver.find_elements(By.XPATH, "//tbody/tr")
    dados = []
    for tr in trs:
        disabled = (tr.get_attribute("data-disabled") == "true")
        hora = txt(tr, ".//td[3]//*[self::div or self::p or self::span][1]")
        paciente = txt(tr, ".//td[4]//*[self::p or self::span][1] | .//td[4]")
        convenio = txt(tr, ".//td[5]")
        status = txt(tr, ".//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]").casefold()
        pagamento = attr(tr, ".//td[7]//svg[contains(@class,'dollar-sign')]", "data-state")  # unpayed/payed/refunded
        especialidade = txt(tr, ".//td[8]//span | .//td[8]")
        profissional = txt(tr, ".//td[10]//span | .//td[10]")

        dados.append({
            "el": tr,
            "disabled": disabled,
            "hora": hora or "-",
            "paciente": paciente or "-",
            "convenio": convenio or "-",
            "status": status or "-",
            "pagamento": pagamento or "-",
            "especialidade": especialidade or "-",
            "profissional": profissional or "-",
        })
    return dados

def clicar_td4_se_vazia(driver, tr):
    """Clica na 4ª coluna: se existir <a>/<button> interno tenta neles; senão clica no TD.
       Só executa se o texto atual for '-' (vazio)."""
    try:
        td4 = tr.find_element(By.XPATH, ".//td[4]")
        conteudo = td4.get_attribute("textContent").strip()
        if conteudo != "-":
            return False  # não é célula vazia
        # tenta um alvo interno clicável
        try:
            inner = td4.find_element(By.XPATH, ".//*[self::a or self::button]")
            wait_for(driver).until(EC.element_to_be_clickable(inner))
            js_click(driver, inner)
        except Exception:
            # clica no TD (com JS para evitar problemas de overlay)
            js_click(driver, td4)
        return True
    except (StaleElementReferenceException, TimeoutException):
        return False

# ----------------- fluxo principal -----------------
def main():
    # inicializa o driver (Selenium Manager resolve o ChromeDriver nas versões recentes)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # descomente se quiser headless
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        # (opcional) limpar chaves de seleção antiga de unidade sem sair do login
        driver.execute_script("""
            try { localStorage.removeItem('selectedUnit'); } catch(e) {}
            try { localStorage.removeItem('selectedClinic'); } catch(e) {}
        """)

        # 1) login
        login(driver)

        # 2) escolher a clínica correta
        select_clinic(driver, CLINICA)

        # 3) ir para Recepção
        ir_para_recepcao(driver)

        # 4) (opcional) paginação "2"
        abrir_paginacao_2_se_existir(driver)

        # 5) coletar linhas
        dados = coletar_linhas(driver)
        print(f"Total de linhas encontradas: {len(dados)}")
        for d in dados:
            print(f"[{'DIS' if d['disabled'] else 'HAB'}] {d['hora']} | {d['status']} | {d['paciente']} | "
                  f"{d['especialidade']} | pay={d['pagamento']}")

        # 6) filtrar apenas as habilitadas e com status 'disponível'
        disponiveis = [d for d in dados if (not d["disabled"]) and ("disponível" in d["status"])]
        print(f"Linhas disponíveis: {len(disponiveis)}")

        # 7) clicar na 4ª coluna SOMENTE quando estiver “-”
        for d in disponiveis:
            ok = clicar_td4_se_vazia(driver, d["el"])
            print(("OK" if ok else "IGNORADA"),
                  f"linha {d['hora']} | status: {d['status']} | paciente: {d['paciente']}")

        input("Pressione Enter para fechar o navegador...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
