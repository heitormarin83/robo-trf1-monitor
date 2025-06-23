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

# URL DIRETA do processo (solução definitiva)
PROCESSO_URL_DIRETA = "https://pje2g.trf1.jus.br/consultapublica/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam?ca=f6a55fbc9faaab3a0728ab495301f39d90cb6c0728456e86"

# Caminho para o arquivo de movimentos anteriores
previous_movs_file = "movimentos_trf1_previous.json"

# Configurações de e-mail (usando variáveis de ambiente para segurança)
EMAIL_USER = os.getenv("EMAIL_USER", "heitor.a.marin@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")  # DEVE ser configurado no Railway
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

def extrair_movimentos_url_direta(session, url):
    """
    Extrai movimentos usando URL direta do processo
    """
    movimentos_list = []
    try:
        print(f"🔗 Acessando URL direta do processo...")
        print(f"🌐 URL: {url}")
        
        response = session.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Salvar HTML para debug
        with open('debug_url_direta.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print("📋 Extraindo movimentos da página...")
        
        # Estratégia 1: Buscar por texto que contenha datas brasileiras
        date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
        
        # Buscar em todos os elementos de texto
        all_text_elements = soup.find_all(string=True)
        
        movimento_keywords = [
            'conclus', 'distribu', 'juntad', 'intimaç', 'decisão', 'sentença', 
            'despacho', 'petição', 'recurso', 'apelação', 'vista', 'carga',
            'baixa', 'arquiv', 'remess', 'devolv', 'certidão', 'mandado'
        ]
        
        for text in all_text_elements:
            text_clean = text.strip()
            if date_pattern.search(text_clean) and len(text_clean) > 20:
                # Verificar se parece com um movimento
                if any(palavra in text_clean.lower() for palavra in movimento_keywords):
                    movimentos_list.append(text_clean)
                    print(f"📄 Movimento encontrado: {text_clean[:100]}...")
        
        # Estratégia 2: Buscar em tabelas
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    if date_pattern.search(row_text) and len(row_text) > 20:
                        # Verificar se é um movimento válido
                        if any(palavra in row_text.lower() for palavra in movimento_keywords):
                            movimentos_list.append(row_text)
                            print(f"📊 Movimento em tabela: {row_text[:100]}...")
        
        # Estratégia 3: Buscar por divs com classes específicas
        movimento_divs = soup.find_all('div', class_=re.compile(r'movimento|movimentacao|historico', re.IGNORECASE))
        for div in movimento_divs:
            text = div.get_text(strip=True)
            if date_pattern.search(text) and len(text) > 20 and len(text) < 500:
                movimentos_list.append(text)
                print(f"📦 Movimento em div: {text[:100]}...")
        
        # Estratégia 4: Buscar por spans e paragrafos
        for tag in ['span', 'p', 'li']:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text(strip=True)
                if date_pattern.search(text) and len(text) > 20 and len(text) < 300:
                    if any(palavra in text.lower() for palavra in movimento_keywords):
                        movimentos_list.append(text)
                        print(f"📝 Movimento em {tag}: {text[:100]}...")
        
        # Remover duplicatas mantendo a ordem
        movimentos_list = list(dict.fromkeys(movimentos_list))
        
        # Se não encontrou movimentos específicos, buscar por qualquer texto com data
        if not movimentos_list:
            print("⚠️ Nenhum movimento específico encontrado, buscando textos com datas...")
            for text in all_text_elements:
                text_clean = text.strip()
                if date_pattern.search(text_clean) and len(text_clean) > 15 and len(text_clean) < 300:
                    # Filtrar textos muito genéricos
                    if not any(palavra in text_clean.lower() for palavra in ['copyright', 'versão', 'sistema', 'cnj']):
                        movimentos_list.append(text_clean)
            
            # Limitar e remover duplicatas
            movimentos_list = list(dict.fromkeys(movimentos_list))[:20]
        
        # Ordenar movimentos por data (mais recente primeiro)
        def extrair_data(texto):
            match = date_pattern.search(texto)
            if match:
                try:
                    data_str = match.group()
                    return datetime.strptime(data_str, '%d/%m/%Y')
                except:
                    return datetime.min
            return datetime.min
        
        movimentos_list.sort(key=extrair_data, reverse=True)
        
        print(f"✅ Total de movimentos extraídos: {len(movimentos_list)}")
        return movimentos_list
        
    except Exception as e:
        print(f"❌ Erro ao extrair movimentos: {e}")
        return []

def get_current_movs():
    """
    Função principal para obter movimentos atuais usando URL direta
    """
    session = create_session()
    
    try:
        # Usar URL direta do processo
        movimentos = extrair_movimentos_url_direta(session, PROCESSO_URL_DIRETA)
        
        return movimentos
        
    except Exception as e:
        print(f"❌ Erro geral na obtenção de movimentos: {e}")
        return []

def send_email_yagmail(subject, body):
    """
    Envia e-mail usando yagmail com App Password do Gmail
    """
    try:
        if not EMAIL_APP_PASSWORD:
            print("❌ ERRO: App Password do Gmail não configurada!")
            print("💡 Configure a variável EMAIL_APP_PASSWORD no Railway")
            print("💡 Acesse: myaccount.google.com > Segurança > Senhas de app")
            return False
        
        print(f"📧 Enviando e-mail para: {EMAIL_RECIPIENT}")
        print(f"📧 Usando conta: {EMAIL_USER}")
        
        # Inicializa o cliente SMTP
        yag = yagmail.SMTP(EMAIL_USER, EMAIL_APP_PASSWORD)
        
        # Envia o e-mail
        yag.send(
            to=EMAIL_RECIPIENT,
            subject=subject,
            contents=body
        )
        
        print(f"✅ E-mail enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        if "Username and Password not accepted" in str(e):
            print("💡 Erro de autenticação - verifique a App Password no Railway")
            print("💡 Variável: EMAIL_APP_PASSWORD")
        return False

def load_previous_movs():
    """
    Carrega os movimentos anteriores do arquivo JSON
    """
    if os.path.exists(previous_movs_file):
        try:
            with open(previous_movs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_current_movs(movs):
    """
    Salva os movimentos atuais no arquivo JSON
    """
    try:
        with open(previous_movs_file, "w", encoding="utf-8") as f:
            json.dump(movs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Erro ao salvar movimentos: {e}")

def check_for_updates(current_movs, previous_movs):
    """
    Verifica se houve atualizações comparando movimentos atuais com anteriores
    """
    has_update = False
    
    if len(current_movs) > len(previous_movs):
        has_update = True
        print(f"🔴 Novos movimentos detectados: {len(current_movs)} vs {len(previous_movs)}")
    elif len(current_movs) == len(previous_movs):
        # Comparar se os movimentos são os mesmos
        for i in range(len(current_movs)):
            if i < len(previous_movs) and current_movs[i] != previous_movs[i]:
                has_update = True
                print(f"🔴 Movimento alterado na posição {i+1}")
                break
    else:
        # Se a quantidade de movimentos atuais for menor, considerar como atualização
        has_update = True
        print(f"🔴 Quantidade de movimentos alterada: {len(current_movs)} vs {len(previous_movs)}")
    
    return has_update

def generate_email_body(has_update, current_movs):
    """
    Gera o corpo do e-mail em HTML
    """
    email_body = ""
    
    # Mensagem de status
    if has_update:
        status_message = '<p style="color: red; font-weight: bold; font-size: 18px;">🔴 PROCESSO ATUALIZADO</p>'
    else:
        status_message = '<p style="color: green; font-weight: bold; font-size: 18px;">🟢 PROCESSO SEM MOVIMENTAÇÃO</p>'
    
    email_body += status_message
    email_body += "<hr>"
    email_body += f"<h3>📋 Processo: {PROCESSO_TEXTO}</h3>"
    email_body += f"<p><strong>🆔 CPF consultado:</strong> {CPF_BUSCA}</p>"
    email_body += "<h3>📄 Movimentações do Processo:</h3>"
    
    if current_movs:
        email_body += "<ol style='line-height: 1.8; padding-left: 20px;'>"
        for i, mov in enumerate(current_movs):
            # Destacar movimentos mais recentes
            if i < 3:
                email_body += f"<li style='margin-bottom: 10px; font-weight: bold;'>{mov}</li>"
            else:
                email_body += f"<li style='margin-bottom: 8px;'>{mov}</li>"
        email_body += "</ol>"
    else:
        email_body += "<p><em>❌ Nenhuma movimentação encontrada.</em></p>"
    
    # Adicionar informações adicionais
    email_body += "<hr>"
    email_body += f"<p><small>🕐 Consulta realizada em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</small></p>"
    email_body += f"<p><small>📊 Total de movimentações: {len(current_movs)}</small></p>"
    email_body += f"<p><small>🔗 Método: URL direta - versão definitiva</small></p>"
    email_body += f"<p><small>🤖 Robô TRF1 v2.0 - Monitoramento automático</small></p>"
    
    return email_body

def main():
    """
    Função principal do robô de monitoramento
    """
    print("=" * 70)
    print("🤖 ROBÔ TRF1 - MONITORAMENTO DE PROCESSOS v2.0")
    print("=" * 70)
    print(f"🕐 Iniciando monitoramento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🆔 CPF de busca: {CPF_BUSCA}")
    print(f"📋 Processo: {PROCESSO_TEXTO}")
    print(f"🔗 Método: URL direta (solução definitiva)")
    print("=" * 70)
    
    # Verificar configuração de e-mail
    if not EMAIL_APP_PASSWORD:
        print("❌ ERRO: App Password do Gmail não configurada!")
        print("💡 Configure a variável EMAIL_APP_PASSWORD no Railway")
        print("💡 Acesse: myaccount.google.com > Segurança > Senhas de app")
        print("=" * 70)
    else:
        print("✅ App Password configurada")
    
    # Obter movimentos atuais
    print("🔍 Acessando processo via URL direta...")
    current_movs = get_current_movs()
    
    if not current_movs:
        print("❌ ERRO: Não foi possível obter os movimentos do processo.")
        # Enviar e-mail de erro
        error_subject = f"❌ ERRO - Situação Processo TRF1 - {datetime.now().strftime('%d/%m/%Y')}"
        error_body = f"""
        <p style="color: red; font-weight: bold;">❌ ERRO NA CONSULTA DO PROCESSO</p>
        <p>Não foi possível acessar ou extrair as movimentações do processo.</p>
        <p><strong>🆔 CPF consultado:</strong> {CPF_BUSCA}</p>
        <p><strong>📋 Processo:</strong> {PROCESSO_TEXTO}</p>
        <p><strong>🔗 URL acessada:</strong> {PROCESSO_URL_DIRETA}</p>
        <p>🔍 Possíveis causas:</p>
        <ul>
            <li>Site do TRF1 indisponível</li>
            <li>URL do processo alterada</li>
            <li>Problema de conectividade</li>
            <li>Mudança na estrutura da página</li>
        </ul>
        <p><small>🕐 Verificação realizada em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</small></p>
        <p><small>🤖 Robô TRF1 v2.0 - URL direta</small></p>
        """
        
        send_email_yagmail(error_subject, error_body)
        print("=" * 70)
        return
    
    print(f"✅ Encontrados {len(current_movs)} movimentos.")
    
    # Carregar movimentos anteriores
    previous_movs = load_previous_movs()
    print(f"📂 Movimentos anteriores: {len(previous_movs)}")
    
    # Verificar se houve atualizações
    has_update = check_for_updates(current_movs, previous_movs)
    
    if has_update:
        print("🔴 ATUALIZAÇÃO DETECTADA!")
    else:
        print("🟢 Nenhuma atualização detectada.")
    
    # Salvar movimentos atuais
    save_current_movs(current_movs)
    print("💾 Movimentos salvos para próxima comparação.")
    
    # Gerar e-mail
    data_consulta = datetime.now().strftime("%d/%m/%Y")
    email_subject = f"📋 Situação Processo TRF1 - {data_consulta}"
    email_body = generate_email_body(has_update, current_movs)
    
    # Enviar e-mail
    print("📧 Enviando e-mail...")
    success = send_email_yagmail(email_subject, email_body)
    
    if success:
        print("✅ Monitoramento concluído com sucesso!")
    else:
        print("❌ Erro no envio do e-mail.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()


