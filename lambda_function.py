import json
import time
import hashlib
import logging
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2
from psycopg2 import sql

# Mapeamento das classes CSS
NAME = "d4r55"
RATING = "kvMYJc"
COMMENT = "MyEned"
TIME_AGO = "rsqaWe"
REVIEW = "jJc9Ad"
MORE_BUTTON = "button.w8nwRe.kyuRq"
REVIEW_DIV = "div.m6QErb.DxyBCb.kA9KIf.dS8AEf"

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Exibe logs no console
    ]
)

def generate_review_id(review):
    """Gera um identificador único para cada avaliação."""
    unique_string = f"{review['nome']}_{review['nota']}_{review['tempo']}_{review['comentario']}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def load_existing_reviews(filename):
    """Carrega as avaliações já salvas para evitar duplicação."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return {generate_review_id(review) for review in json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"Arquivo '{filename}' não encontrado ou inválido. Criando novo arquivo.")
        return set()

def expand_long_reviews(driver):
    """Expande avaliações longas visíveis na tela."""
    try:
        more_buttons = driver.find_elements(By.CSS_SELECTOR, MORE_BUTTON)
        for button in more_buttons:
            if button.is_displayed():  # Verifica se o botão está visível
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.5)  # Pequena espera após o clique
    except Exception as e:
        logging.error(f"Erro ao expandir avaliações: {e}")

def get_all_reviews(driver):
    """Coleta todas as avaliações visíveis na página."""
    reviews = []
    elements = driver.find_elements(By.CLASS_NAME, REVIEW)

    for element in elements:
        try:
            name = element.find_element(By.CLASS_NAME, NAME).text.strip()
            rating = element.find_element(By.CLASS_NAME, RATING).get_attribute("aria-label")
            time_ago = element.find_element(By.CLASS_NAME, TIME_AGO).text.strip()
            
            # Tenta capturar o comentário, se não existir, define como ""
            try:
                review_text = element.find_element(By.CLASS_NAME, COMMENT).text.strip()
            except:
                review_text = ""  # Preenche com string vazia se o comentário não existir

            review_data = {
                "nome": name,
                "nota": rating,
                "tempo": time_ago,
                "comentario": review_text
            }

            reviews.append(review_data)

        except Exception as e:
            logging.error(f"Erro ao coletar dados da review: {e}")
            continue

    return reviews

def get_new_reviews(driver, existing_reviews):
    """Coleta apenas as avaliações visíveis que ainda não foram salvas."""
    new_reviews = []
    elements = driver.find_elements(By.CLASS_NAME, REVIEW)

    for element in elements:
        try:
            name = element.find_element(By.CLASS_NAME, NAME).text.strip()
            rating = element.find_element(By.CLASS_NAME, RATING).get_attribute("aria-label")
            time_ago = element.find_element(By.CLASS_NAME, TIME_AGO).text.strip()
            
            # Tenta capturar o comentário, se não existir, define como ""
            try:
                review_text = element.find_element(By.CLASS_NAME, COMMENT).text.strip()
            except:
                review_text = ""  # Preenche com string vazia se o comentário não existir

            review_data = {
                "nome": name,
                "nota": rating,
                "tempo": time_ago,
                "comentario": review_text
            }

            review_id = generate_review_id(review_data)
            if review_id not in existing_reviews:
                new_reviews.append(review_data)
                existing_reviews.add(review_id)  # Adiciona o ID ao conjunto de reviews existentes
            else:
                # Se encontrar uma review já existente, retorna as novas reviews e um sinal para parar
                logging.info("Review já existente encontrada. Interrompendo coleta.")
                return new_reviews, True

        except Exception as e:
            logging.error(f"Erro ao coletar dados da review: {e}")
            continue

    return new_reviews, False

def scroll_page(driver):
    """Rola a página até o final."""
    scrollable_div = driver.find_element(By.CSS_SELECTOR, REVIEW_DIV)
    last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
    scroll_attempts = 0

    while True:
        # Rola a página
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(2.5)

        # Expande reviews longas
        expand_long_reviews(driver)

        # Verifica se atingiu o final da página
        new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        if new_height == last_height:
            scroll_attempts += 1
            if scroll_attempts >= 3:  # Tenta rolar 3 vezes antes de confirmar o fim
                logging.info("Fim das reviews disponíveis.")
                break
        else:
            scroll_attempts = 0  # Reseta o contador se a altura mudar

        last_height = new_height

def scroll_and_collect(driver, existing_reviews):
    """Rola a página e coleta reviews até encontrar uma review já salva."""
    scrollable_div = driver.find_element(By.CSS_SELECTOR, REVIEW_DIV)
    all_reviews = []
    last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

    while True:
        # Rola a página
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(2.5)  # Espera para carregar novas reviews

        # Expande reviews longas
        expand_long_reviews(driver)

        # Coleta novas reviews
        new_reviews, stop_scrolling = get_new_reviews(driver, existing_reviews)
        if new_reviews:
            all_reviews.extend(new_reviews)
            logging.info(f"{len(new_reviews)} novas reviews coletadas.")

        # Se encontrar uma review já existente, para de rolar
        if stop_scrolling:
            logging.info("Interrompendo rolagem: review já existente encontrada.")
            break

        # Verifica se atingiu o final da página
        new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        if new_height == last_height:
            logging.info("Fim das reviews disponíveis.")
            break
        last_height = new_height

    return all_reviews

def order_by_recent(driver):
    """Ordena as avaliações por 'Mais recentes'."""
    try:
        menu_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-value*="Ordenar"]'))
        )
        driver.execute_script("arguments[0].click();", menu_button)
        time.sleep(1)  # Espera para o menu abrir

        recent_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-index*="1"]'))
        )
        driver.execute_script("arguments[0].click();", recent_button)
        time.sleep(1)  # Espera para as avaliações serem reordenadas
    except Exception as e:
        logging.error(f"Não foi possível ordenar as avaliações por 'Mais recentes': {e}")

def save_reviews(reviews, filename):
    """Salva as avaliações no arquivo JSON."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.extend(reviews)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"{len(reviews)} novas reviews salvas no arquivo '{filename}'.")

def extract_place_name(url):
    """Extrai o nome do lugar da URL."""
    try:
        place_name = url.split("place/")[1].split("/")[0]  # Pega o texto após "place/" e antes do próximo "/"
        place_name = urllib.parse.unquote(place_name)
        place_name = place_name.replace("+", "_")  # Substitui "+" por "_"
        place_name = place_name.replace("-", "_")  # Substitui "-" por "_"
        place_name = place_name.lower()  # Converte para minúsculas
        return place_name
    except Exception as e:
        logging.error(f"Erro ao extrair o nome do lugar da URL: {e}")
        return "reviews"

def connect_to_db():
    """Conecta ao banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname="case_nola",
            user="fabio",
            password="123",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def save_reviews_to_db(reviews, place_name):
    """Salva as reviews no banco de dados PostgreSQL."""
    conn = connect_to_db()
    if conn is None:
        return

    try:
        create_table(conn, place_name)
        insert_reviews(conn, reviews, place_name)
        logging.info(f"{len(reviews)} reviews salvas na tabela '{place_name}'.")
    except Exception as e:
        logging.error(f"Erro ao salvar reviews no banco de dados: {e}")
    finally:
        if conn:
            conn.close()

def create_table(conn, table_name):
    """Cria a tabela no PostgreSQL se ela não existir."""
    create_table_query = sql.SQL("""
    CREATE TABLE IF NOT EXISTS {} (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        nota TEXT NOT NULL,
        tempo TEXT NOT NULL,
        comentario TEXT
    );
    """).format(sql.Identifier(table_name))
    
    with conn.cursor() as cursor:
        cursor.execute(create_table_query)
    conn.commit()

def insert_reviews(conn, reviews, table_name):
    """Insere as reviews na tabela PostgreSQL."""
    insert_query = sql.SQL("""
    INSERT INTO {} (nome, nota, tempo, comentario)
    VALUES (%s, %s, %s, %s);
    """).format(sql.Identifier(table_name))
    
    with conn.cursor() as cursor:
        for review in reviews:
            cursor.execute(insert_query, (review['nome'], review['nota'], review['tempo'], review['comentario']))
    conn.commit()

def lambda_handler(event, context):
    url = event.get('url')
    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps('URL não fornecida')
        }

    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--remote-debugging-port=9222")

    service = Service(service = Service(ChromeDriverManager().install()))

    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)

    try:
        # Clica no botão "Avaliações"
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="Avaliações"]'))
        )
        driver.execute_script("arguments[0].click();", button)
        time.sleep(1)  # Espera para as avaliações carregarem
    except Exception as e:
        logging.error(f"Botão de avaliações não encontrado: {e}")
        driver.quit()
        return {
            'statusCode': 500,
            'body': json.dumps('Erro ao encontrar o botão de avaliações')
        }

    # Ordena por "Mais recentes"
    order_by_recent(driver)

    # Extrai o nome do lugar da URL
    place_name = extract_place_name(url)

    filename = f"./{place_name}_reviews.json"

    # Verifica se o arquivo JSON já existe
    existing_reviews = load_existing_reviews(filename)

    if not existing_reviews:
        # Se o arquivo não existir, faz o scroll total antes de coletar as reviews
        logging.info("Arquivo JSON não encontrado. Fazendo scroll total da página...")
        scroll_page(driver)
        logging.info("Scroll completo. Coletando todas as reviews...")
        reviews = get_all_reviews(driver)
    else:
        # Se o arquivo existir, faz o scroll e coleta apenas as novas reviews
        logging.info("Arquivo JSON encontrado. Coletando apenas as novas reviews...")
        reviews = scroll_and_collect(driver, existing_reviews)

    # Salva as reviews
    if reviews:
        save_reviews(reviews, filename)
        save_reviews_to_db(reviews, place_name)
    else:
        logging.info("Nenhuma nova review para salvar.")

    driver.quit()

    return {
        'statusCode': 200,
        'body': json.dumps(f"{len(reviews)} novas reviews coletadas e salvas.")
    }

if __name__ == "__main__":
    # Evento simulado para teste local
    event = {
        #"url": "https://www.google.com/maps/place/Nema/@-22.9841517,-43.2128543,15z/data=!4m5!3m4!1s0x0:0x4c1eb56d62eb469b!8m2!3d-22.9841517!4d-43.2128543?shorturl=1",
        #"url": "https://www.google.com/maps/place/Portugo+-+Past%C3%A9is+de+Nata/@-22.9850962,-43.2264946,15z/data=!4m5!3m4!1s0x0:0x930f8a469526651c!8m2!3d-22.9851673!4d-43.2264659?shorturl=1",
        #"url": "https://www.google.com/maps/place/Nema+Padaria/@-22.9561199,-43.2051002,15z/data=!4m5!3m4!1s0x0:0x17650611ede4f2c9!8m2!3d-22.9561199!4d-43.1963455?shorturl=1",
        "url": "https://www.google.com/maps/place/MERCADO+BACELAR/@-25.4958129,-49.3532736,16z/data=!4m6!3m5!1s0x94dce3916c0327f1:0x28831459a6e866d6!8m2!3d-25.4988623!4d-49.3516109!16s%2Fg%2F11jkzt3j11?entry=ttu&g_ep=EgoyMDI1MDMwNC4wIKXMDSoASAFQAw%3D%3D"
    }

    context = {}

    # Executa o lambda_handler localmente
    response = lambda_handler(event, context)
    print(response)