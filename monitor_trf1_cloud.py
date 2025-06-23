import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import os
import yagmail
import time

# Configurações
CPF_BUSCA = "30696525810"
PROCESSO_NUMERO = "1002946-59.2025.4.01.9999"
PROCESSO_TEXTO = "ApCiv 1002946-59.2025.4.01.9999 - Ambiental"
URL_CONSULTA = "https://pje2g.trf1.jus.br/consultapublica/ConsultaPublica/listView.seam"

# Caminho para o arquivo de movimentos anteriores
previous_movs_file = "movimentos_trf1_previous.json"

# Configurações de e-mail (usando variáveis de ambiente para segurança)
EMAIL_USER = os.getenv("EMAIL_USER", "heitor.a.marin@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "vueywlqyqhsozzqr")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "heitor.a.marin@gmail.com")

def create_session():
    """
    Cria uma sessão HTTP com headers apropriados
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def buscar_processo_validado(session, cpf):
    """
    Busca processo usando exatamente o método validado manualmente
    """
    try:
        print(f"Acessando página de consulta: {URL_CONSULTA}")
        
        # Primeira requisição para obter a página inicial
        response = session.get(URL_CONSULTA)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Procurar pelo formulário de busca
        form = soup.find('form')
        if not form:
            print("Erro: Formulário de busca não encontrado")
            return None
        
        # Extrair action do formulário
        form_action = form.get('action', '')
        if form_action.startswith('/'):
            form_url = f"https://pje2g.trf1.jus.br{form_action}"
        else:
            form_url = f"https://pje2g.trf1.jus.br/consultapublica/ConsultaPublica/{form_action}"
        
        print(f"URL do formulário: {form_url}")
        
        # Extrair TODOS os campos hidden do formulário
        form_data = {}
        hidden_inputs = soup.find_all('input', type='hidden')
        for hidden in hidden_inputs:
            name = hidden.get('name')
            value = hidden.get('value', '')
            if name:
                form_data[name] = value
        
        # Extrair outros campos necessários
        all_inputs = soup.find_all('input')
        for input_elem in all_inputs:
            name = input_elem.get('name')
            value = input_elem.get('value', '')
            input_type = input_elem.get('type', 'text')
            
            if name and input_type not in ['hidden', 'submit'] and value:
                form_data[name] = value
        
        # Campo CPF específico - baseado na validação manual
        # Na validação, descobrimos que o campo correto tem o nome relacionado a "tipoMascaraDocumento"
        cpf_field_candidates = [
            'tipoMascaraDocumento',
            'fPP:Decoration:numeroOAB',
            'fPP:numeroOAB',
            'numeroOAB'
        ]
        
        cpf_field_name = None
        for candidate in cpf_field_candidates:
            if any(inp.get('name') == candidate for inp in all_inputs):
                cpf_field_name = candidate
                print(f"Campo CPF encontrado: {cpf_field_name}")
                break
        
        # Se não encontrou pelos nomes conhecidos, procurar por padrão
        if not cpf_field_name:
            for input_elem in all_inputs:
                name = input_elem.get('name', '')
                input_type = input_elem.get('type', 'text')
                if input_type == 'text' and any(term in name.lower() for term in ['cpf', 'documento', 'oab']):
                    cpf_field_name = name
                    print(f"Campo CPF encontrado por padrão: {cpf_field_name}")
                    break
        
        if not cpf_field_name:
            print("Erro: Campo CPF não encontrado")
            return None
        
        # Adicionar CPF aos dados do formulário
        form_data[cpf_field_name] = cpf
        
        # Adicionar dados específicos do formulário se necessário
        form_data['fPP'] = 'fPP'
        
        print("Enviando formulário de busca...")
        print(f"Campo CPF usado: {cpf_field_name} = {cpf}")
        
        # Enviar formulário
        search_response = session.post(form_url, data=form_data)
        search_response.raise_for_status()
        
        # Analisar resultados
        result_soup = BeautifulSoup(search_response.text, 'html.parser')
        
        # Salvar HTML para debug
        with open('debug_busca_validada.html', 'w', encoding='utf-8') as f:
            f.write(search_response.text)
        
        print(f"Procurando pelo processo: {PROCESSO_TEXTO}")
        
        # Buscar pelo link do processo - método exato da validação
        processo_url = None
        
        # Buscar por todos os links na página
        all_links = result_soup.find_all('a', href=True)
        
        for link in all_links:
            link_text = link.get_text(strip=True)
            href = link.get('href')
            
            # Verificar se o link contém o texto exato do processo
            if PROCESSO_TEXTO in link_text:
                if href.startswith('/'):
                    processo_url = f"https://pje2g.trf1.jus.br{href}"
                else:
                    processo_url = href
                print(f"Processo encontrado! URL: {processo_url}")
                print(f"Texto do link: {link_text}")
                break
            
            # Verificar também pelo número do processo
            elif PROCESSO_NUMERO in link_text:
                if href.startswith('/'):
                    processo_url = f"https://pje2g.trf1.jus.br{href}"
                else:
                    processo_url = href
                print(f"Processo encontrado pelo número! URL: {processo_url}")
                print(f"Texto do link: {link_text}")
                break
        
        if not processo_url:
            print("Processo não encontrado nos resultados")
            print("Links encontrados na página:")
            for i, link in enumerate(all_links[:10]):
                text = link.get_text(strip=True)
                if text and len(text) > 5:
                    print(f"  {i+1}: {text[:100]}")
            return None
        
        return processo_url
        
    except Exception as e:
        print(f"Erro durante busca: {e}")
        return None

def extrair_movimentos_detalhes(session, processo_url):
    """
    Extrai movimentos da página de detalhes
    """
    movimentos_list = []
    try:
        print(f"Acessando página de detalhes: {processo_url}")
        
        response = session.get(processo_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Salvar HTML para debug
        with open('debug_detalhes_validado.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print("Extraindo movimentos da página de detalhes...")
        
        # Buscar por movimentos usando múltiplas estratégias
        
        # Estratégia 1: Buscar por texto que contenha datas brasileiras
        date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
        
        # Buscar em todos os elementos de texto
        all_text_elements = soup.find_all(string=True)
        
        for text in all_text_elements:
            text_clean = text.strip()
            if date_pattern.search(text_clean) and len(text_clean) > 20:
                # Verificar se parece com um movimento
                movimento_keywords = ['conclus', 'distribu', 'juntad', 'intimaç', 'decisão', 'sentença', 'despacho', 'petição', 'recurso']
                if any(palavra in text_clean.lower() for palavra in movimento_keywords):
                    movimentos_list.append(text_clean)
                    print(f"Movimento encontrado: {text_clean[:100]}...")
        
        # Estratégia 2: Buscar em tabelas
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    if date_pattern.search(row_text) and len(row_text) > 20:
                        movimentos_list.append(row_text)
                        print(f"Movimento em tabela: {row_text[:100]}...")
        
        # Estratégia 3: Buscar por divs específicas
        divs = soup.find_all('div')
        for div in divs:
            text = div.get_text(strip=True)
            if date_pattern.search(text) and len(text) > 20 and len(text) < 500:
                movimento_keywords = ['conclus', 'distribu', 'juntad', 'intimaç', 'decisão', 'sentença', 'despacho']
                if any(palavra in text.lower() for palavra in movimento_keywords):
                    movimentos_list.append(text)
                    print(f"Movimento em div: {text[:100]}...")
        
        # Remover duplicatas mantendo a ordem
        movimentos_list = list(dict.fromkeys(movimentos_list))
        
        # Se não encontrou movimentos específicos, buscar por qualquer texto com data
        if not movimentos_list:
            print("Nenhum movimento específico encontrado, buscando textos com datas...")
            for text in all_text_elements:
                text_clean = text.strip()
                if date_pattern.search(text_clean) and len(text_clean) > 15 and len(text_clean) < 300:
                    movimentos_list.append(text_clean)
            
            # Limitar e remover duplicatas
            movimentos_list = list(dict.fromkeys(movimentos_list))[:15]
        
        print(f"Total de movimentos extraídos: {len(movimentos_list)}")
        return movimentos_list
        
    except Exception as e:
        print(f"Erro ao extrair movimentos: {e}")
        return []

def get_current_movs():
    """
    Função principal para obter movimentos atuais
    """
    session = create_session()
    
    try:
        # Buscar processo usando método validado
        processo_url = buscar_processo_validado(session, CPF_BUSCA)
        
        if not processo_url:
            print("Erro: Não foi possível encontrar o processo")
            return []
        
        # Extrair movimentos da página de detalhes
        movimentos = extrair_movimentos_detalhes(session, processo_url)
        
        return movimentos
        
    except Exception as e:
        print(f"Erro geral na obtenção de movimentos: {e}")
        return []

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
    email_body += f"<h3>Processo: {PROCESSO_TEXTO}</h3>"
    email_body += f"<p><strong>CPF consultado:</strong> {CPF_BUSCA}</p>"
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
    email_body += f"<p><small>Método: Busca validada manualmente - versão final</small></p>"
    
    return email_body

def main():
    """
    Função principal do robô de monitoramento
    """
    print(f"Iniciando monitoramento do TRF1 - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"CPF de busca: {CPF_BUSCA}")
    print(f"Processo esperado: {PROCESSO_TEXTO}")
    print("Versão: FINAL - Validada manualmente")
    
    # Verificar se a App Password está configurada
    if not EMAIL_APP_PASSWORD:
        print("ATENÇÃO: App Password do Gmail não configurada!")
        print("Por favor, configure a variável de ambiente EMAIL_APP_PASSWORD.")
        return
    
    # Obter movimentos atuais
    print("Iniciando busca com método validado...")
    current_movs = get_current_movs()
    
    if not current_movs:
        print("ERRO: Não foi possível obter os movimentos do processo.")
        # Enviar e-mail de erro
        error_subject = f"ERRO - Situação Processo TRF1 - {datetime.now().strftime('%d/%m/%Y')}"
        error_body = f"""
        <p style="color: red; font-weight: bold;">ERRO NA CONSULTA DO PROCESSO</p>
        <p>Não foi possível acessar ou extrair as movimentações do processo.</p>
        <p><strong>CPF consultado:</strong> {CPF_BUSCA}</p>
        <p><strong>Processo esperado:</strong> {PROCESSO_TEXTO}</p>
        <p>Possíveis causas:</p>
        <ul>
            <li>Site do TRF1 indisponível</li>
            <li>Processo não encontrado</li>
            <li>Mudança na estrutura da página</li>
            <li>Problema de conectividade</li>
        </ul>
        <p><small>Verificação realizada em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</small></p>
        <p><small>Versão: FINAL - Validada manualmente</small></p>
        """
        
        send_email_yagmail(error_subject, error_body)
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
