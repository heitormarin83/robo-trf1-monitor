import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import os
import yagmail

# URL do processo
url = "https://pje2g.trf1.jus.br/consultapublica/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam?ca=f6a55fbc9faaab3a0728ab495301f39d90cb6c0728456e86"

# Caminho para o arquivo de movimentos anteriores
previous_movs_file = "movimentos_trf1_previous.json"

# Configurações de e-mail (usando variáveis de ambiente para segurança)
EMAIL_USER = os.getenv("EMAIL_USER", "heitor.a.marin@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "vueywlqyqhsozzqr")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "heitor.a.marin@gmail.com")

def send_email_yagmail(subject, body):
    """
    Envia e-mail usando yagmail com App Password do Gmail
    """
    try:
        if not EMAIL_APP_PASSWORD:
            print("ERRO: App Password do Gmail não configurada!")
            return False
            
        # Inicializa o cliente SMTP
        yag = yagmail.SMTP(EMAIL_USER, EMAIL_APP_PASSWORD)
        
        # Envia o e-mail
        yag.send(
            to=EMAIL_RECIPIENT,
            subject=subject,
            contents=body
        )
        
        print(f"E-mail enviado com sucesso para {EMAIL_RECIPIENT}")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

def get_current_movs():
    """
    Extrai os movimentos atuais do processo no TRF1
    """
    movimentos_list = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # Regex para encontrar o padrão de data e hora no início da string
    date_time_pattern = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} - ")

    # Buscar por todos os elementos <td> na página
    all_tds = soup.find_all("td")

    for td in all_tds:
        text = td.get_text(strip=True)
        if date_time_pattern.match(text):
            movimentos_list.append(text)
    
    return movimentos_list

def load_previous_movs():
    """
    Carrega os movimentos anteriores do arquivo JSON
    """
    if os.path.exists(previous_movs_file):
        with open(previous_movs_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_current_movs(movs):
    """
    Salva os movimentos atuais no arquivo JSON
    """
    with open(previous_movs_file, "w", encoding="utf-8") as f:
        json.dump(movs, f, ensure_ascii=False, indent=4)

def check_for_updates(current_movs, previous_movs):
    """
    Verifica se houve atualizações comparando movimentos atuais com anteriores
    """
    has_update = False
    
    if len(current_movs) > len(previous_movs):
        has_update = True
    elif len(current_movs) == len(previous_movs):
        # Comparar se os movimentos são os mesmos
        for i in range(len(current_movs)):
            if current_movs[i] != previous_movs[i]:
                has_update = True
                break
    else:
        # Se a quantidade de movimentos atuais for menor, considerar como atualização
        has_update = True
    
    return has_update

def generate_email_body(has_update, current_movs):
    """
    Gera o corpo do e-mail em HTML
    """
    email_body = ""
    
    # Mensagem de status
    if has_update:
        status_message = '<p style="color: red; font-weight: bold; font-size: 18px;">PROCESSO ATUALIZADO</p>'
    else:
        status_message = '<p style="color: green; font-weight: bold; font-size: 18px;">PROCESSO SEM MOVIMENTAÇÃO</p>'
    
    email_body += status_message
    email_body += "<hr>"
    email_body += "<h3>Movimentações do Processo:</h3>"
    
    if current_movs:
        email_body += "<ul style='line-height: 1.6;'>"
        for mov in current_movs:
            email_body += f"<li>{mov}</li>"
        email_body += "</ul>"
    else:
        email_body += "<p><em>Nenhuma movimentação encontrada.</em></p>"
    
    # Adicionar informações adicionais
    email_body += "<hr>"
    email_body += f"<p><small>Consulta realizada em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</small></p>"
    email_body += f"<p><small>Total de movimentações: {len(current_movs)}</small></p>"
    email_body += f"<p><small>Executado via Railway Cloud</small></p>"
    
    return email_body

def main():
    """
    Função principal do robô de monitoramento
    """
    print(f"Iniciando monitoramento do TRF1 - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verificar se a App Password está configurada
    if not EMAIL_APP_PASSWORD:
        print("ATENÇÃO: App Password do Gmail não configurada!")
        print("Por favor, configure a variável de ambiente EMAIL_APP_PASSWORD.")
        return
    
    # Obter movimentos atuais
    print("Obtendo movimentos atuais...")
    current_movs = get_current_movs()
    
    if not current_movs:
        print("ERRO: Não foi possível obter os movimentos do processo.")
        return
    
    print(f"Encontrados {len(current_movs)} movimentos.")
    
    # Carregar movimentos anteriores
    previous_movs = load_previous_movs()
    print(f"Movimentos anteriores: {len(previous_movs)}")
    
    # Verificar se houve atualizações
    has_update = check_for_updates(current_movs, previous_movs)
    
    if has_update:
        print("ATUALIZAÇÃO DETECTADA!")
    else:
        print("Nenhuma atualização detectada.")
    
    # Salvar movimentos atuais
    save_current_movs(current_movs)
    
    # Gerar e-mail
    data_consulta = datetime.now().strftime("%d/%m/%Y")
    email_subject = f"Situação Processo TRF1 - {data_consulta}"
    email_body = generate_email_body(has_update, current_movs)
    
    # Enviar e-mail
    print("Enviando e-mail...")
    success = send_email_yagmail(email_subject, email_body)
    
    if success:
        print("Monitoramento concluído com sucesso!")
    else:
        print("Erro no envio do e-mail.")

if __name__ == "__main__":
    main()

