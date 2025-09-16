from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 20)

# aguarda a tabela existir
wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr")))

def safe_text(el, xpath):
    try:
        return el.find_element(By.XPATH, xpath).text.strip()
    except Exception:
        return ""

def safe_attr(el, xpath, attr):
    try:
        return el.find_element(By.XPATH, xpath).get_attribute(attr)
    except Exception:
        return ""

# só linhas habilitadas
linhas = driver.find_elements(By.XPATH, "//tbody/tr[not(@data-disabled='true')]")

dados = []
for tr in linhas:
    # Hora (3ª coluna). Aceita <div> ou <p>
    hora = safe_text(tr, ".//td[3]//*[self::div or self::p or self::span][1]")

    # Paciente (4ª coluna). Pode vir '-' ou <p> dentro de <a>
    paciente = safe_text(tr, ".//td[4]//*[self::p or self::span][1]")

    # Convênio (5ª) — pode ser '-' puro
    convenio = safe_text(tr, ".//td[5]")

    # Status (6ª) — span interno do botão: 'agendado' ou 'disponível'
    status = safe_text(tr, ".//td[6]//span[contains(@class,'w-28') or contains(@class,'max-w-28')]")

    # Pagamento (7ª) — atributo data-state do ícone de cifrão
    pagamento = safe_attr(tr, ".//td[7]//svg[contains(@class,'dollar-sign')]", "data-state")  # unpayed/payed/refunded

    # Especialidade (8ª) — pode ser <span> ou texto
    especialidade = safe_text(tr, ".//td[8]//span | .//td[8]")

    # Profissional/Observação (10ª) — geralmente um <span> truncado
    profissional = safe_text(tr, ".//td[10]//span | .//td[10]")

    dados.append({
        "hora": hora,
        "paciente": paciente,
        "convenio": convenio,
        "status": status.lower(),
        "pagamento": pagamento,
        "especialidade": especialidade,
        "profissional": profissional,
        "elemento": tr,  # guardo o <tr> para ações depois
    })

print(f"Total de linhas habilitadas: {len(dados)}")
for d in dados:
    print(d["hora"], d["status"], d["paciente"], d["especialidade"], d["pagamento"])

# --- (2) AÇÕES: clique no primeiro 'disponível' ---
for d in dados:
    if "disponível" in d["status"]:
        # botão do status dentro da 6ª coluna
        btn = d["elemento"].find_element(By.XPATH, ".//td[6]//button")
        wait.until(EC.element_to_be_clickable(btn)).click()
        print(f"Cliquei no disponível das {d['hora']}")
        break

# --- exemplo: clicar em um 'disponível' por horário específico ---
alvo_hora = "08:10"
for d in dados:
    if d["hora"] == alvo_hora and "disponível" in d["status"]:
        btn = d["elemento"].find_element(By.XPATH, ".//td[6]//button")
        wait.until(EC.element_to_be_clickable(btn)).click()
        print(f"Cliquei no disponível das {alvo_hora}")
        break

# --- exemplo: filtrar por especialidade + disponível ---
alvo_especialidade = "PRÓTESE"
for d in dados:
    if "disponível" in d["status"] and alvo_especialidade.lower() in d["especialidade"].lower():
        btn = d["elemento"].find_element(By.XPATH, ".//td[6]//button")
        wait.until(EC.element_to_be_clickable(btn)).click()
        print(f"Cliquei no disponível de {alvo_especialidade} às {d['hora']}")
        break
