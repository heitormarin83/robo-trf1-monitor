import requests
import json
import os
import smtplib
import ssl
import socket
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configurações da API DataJud
DATAJUD_API_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_trf1/_search"
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Configurações do processo
PROCESSO_NUMERO = "1002946-59.2025.4.01.9999"
PROCESSO_NUMERO_LIMPO = PROCESSO_NUMERO.replace("-", "").replace(".", "")

# Configurações de e-mail (usando variáveis de ambiente padronizadas)
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", os.getenv("EMAIL_USER", "heitor.a.marin@gmail.com"))
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", os.getenv("EMAIL_APP_PASSWORD", ""))
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "heitor.a.marin@gmail.com")

# Configurações SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_DEBUG = os.getenv("SMTP_DEBUG", "").lower() in ("1", "true", "yes")
SMTP_FORCE_IPV4 = os.getenv("SMTP_FORCE_IPV4", "true").lower() in ("1", "true", "yes")

# Arquivo para armazenar movimentações anteriores
MOVIMENTOS_FILE = "movimentos_datajud_previous.json"

def consultar_processo_datajud(numero_processo):
    """
    Consulta processo usando a API oficial do DataJud
    """
    try:
        print(f"🔍 Consultando processo via API DataJud...")
        print(f"📋 Número do processo: {numero_processo}")
        print(f"🌐 Endpoint: {DATAJUD_API_URL}")
        
        # Headers da requisição
        headers = {
            "Authorization": f"APIKey {DATAJUD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Corpo da requisição (Query DSL)
        query_body = {
            "query": {
                "match": {
                    "numeroProcesso": numero_processo
                }
            }
        }
        
        print(f"🔑 Usando API Key: {DATAJUD_API_KEY[:20]}...")
        print(f"📤 Enviando consulta...")
        
        # Fazer a requisição
        response = requests.post(
            DATAJUD_API_URL,
            headers=headers,
            json=query_body,
            timeout=30
        )
        
        print(f"📥 Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Salvar resposta completa para debug
            with open('debug_datajud_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Resposta recebida com sucesso!")
            print(f"📊 Total de resultados: {data.get('hits', {}).get('total', {}).get('value', 0)}")
            
            return data
            
        else:
            print(f"❌ Erro na API: {response.status_code}")
            print(f"📄 Resposta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        return None

def extrair_movimentacoes(api_response):
    """
    Extrai movimentações do JSON de resposta da API
    """
    movimentacoes = []
    
    try:
        hits = api_response.get('hits', {}).get('hits', [])
        
        if not hits:
            print("⚠️ Nenhum processo encontrado na resposta da API")
            return []
        
        # Pegar o primeiro resultado (deve ser único)
        processo = hits[0].get('_source', {})
        
        print(f"📋 Processo encontrado:")
        print(f"   🆔 Número: {processo.get('numeroProcesso', 'N/A')}")
        print(f"   📅 Data de ajuizamento: {processo.get('dataAjuizamento', 'N/A')}")
        print(f"   🏛️ Classe: {processo.get('classe', {}).get('nome', 'N/A')}")
        print(f"   📍 Órgão julgador: {processo.get('orgaoJulgador', {}).get('nome', 'N/A')}")
        
        # Extrair movimentações
        movimentacoes_raw = processo.get('movimentos', [])
        
        print(f"📄 Encontradas {len(movimentacoes_raw)} movimentações")
        
        for mov in movimentacoes_raw:
            data_hora = mov.get('dataHora', '')
            codigo = mov.get('codigo', '')
            nome = mov.get('nome', '')
            
            # Verificar se há complementos tabelados
            complementos = mov.get('complementosTabelados', [])
            complemento_texto = ""
            if complementos:
                complemento_texto = " - " + ", ".join([comp.get('nome', '') for comp in complementos])
            
            # Formatar movimentação
            descricao = f"{nome}{complemento_texto}"
            
            # Formato: "DD/MM/AAAA HH:MM:SS - Descrição"
            if data_hora:
                try:
                    # Converter ISO para formato brasileiro
                    dt = datetime.fromisoformat(data_hora.replace('Z', '+00:00'))
                    data_formatada = dt.strftime('%d/%m/%Y %H:%M:%S')
                    movimento_formatado = f"{data_formatada} - {descricao}"
                except:
                    movimento_formatado = f"{data_hora} - {descricao}"
            else:
                movimento_formatado = f"Data não informada - {descricao}"
            
            movimentacoes.append(movimento_formatado)
            print(f"   📝 {movimento_formatado}")
        
        # Ordenar por data (mais recente primeiro)
        movimentacoes.sort(reverse=True)
        
        return movimentacoes
        
    except Exception as e:
        print(f"❌ Erro ao extrair movimentações: {e}")
        return []

def load_previous_movs():
    """
    Carrega movimentações anteriores
    """
    if os.path.exists(MOVIMENTOS_FILE):
        try:
            with open(MOVIMENTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_current_movs(movs):
    """
    Salva movimentações atuais
    """
    try:
        with open(MOVIMENTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(movs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar movimentações: {e}")

def check_for_updates(current_movs, previous_movs):
    """
    Verifica se houve atualizações
    """
    if len(current_movs) != len(previous_movs):
        return True
    
    # Comparar cada movimentação
    for i, mov_atual in enumerate(current_movs):
        if i >= len(previous_movs) or mov_atual != previous_movs[i]:
            return True
    
    return False

def send_email_robust(subject, html_body):
    """
    Envia e-mail usando SMTP com fallback robusto
    Baseado no sistema do Insurance News Agent
    """
    try:
        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            print("❌ ERRO: GMAIL_EMAIL e/ou GMAIL_APP_PASSWORD não configurados!")
            print(f"   GMAIL_EMAIL: {'✓ configurado' if GMAIL_EMAIL else '✗ não configurado'}")
            print(f"   GMAIL_APP_PASSWORD: {'✓ configurado' if GMAIL_APP_PASSWORD else '✗ não configurado'}")
            return False
        
        # Preparar lista de destinatários
        recipients = [r.strip() for r in EMAIL_RECIPIENT.split(",") if r.strip()]
        if not recipients:
            print("❌ ERRO: Nenhum destinatário configurado!")
            return False
        
        print(f"📧 Preparando envio de e-mail...")
        print(f"   De: {GMAIL_EMAIL}")
        print(f"   Para: {', '.join(recipients)}")
        print(f"   Assunto: {subject}")
        
        # Criar mensagem MIME
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Robô TRF1 Monitor <{GMAIL_EMAIL}>"
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        # Configuração de debug
        debug_smtp = SMTP_DEBUG
        force_ipv4 = SMTP_FORCE_IPV4
        
        # Monkey-patch temporário para forçar IPv4 (contorna ambientes sem IPv6)
        orig_getaddrinfo = socket.getaddrinfo
        def only_v4(host, port, family=0, type=0, proto=0, flags=0):
            res = orig_getaddrinfo(host, port, family, type, proto, flags)
            v4 = [r for r in res if r[0] == socket.AF_INET]
            return v4 or res
        
        try:
            if force_ipv4:
                print("🔧 Forçando uso de IPv4 para conexão SMTP")
                socket.getaddrinfo = only_v4
            
            # Tentativa 1: Porta 587 com STARTTLS
            try:
                print(f"📡 Tentando conexão via {SMTP_SERVER}:587 (STARTTLS)...")
                context = ssl.create_default_context()
                with smtplib.SMTP(SMTP_SERVER, 587, timeout=30) as smtp:
                    if debug_smtp:
                        smtp.set_debuglevel(1)
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                    smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
                    smtp.sendmail(GMAIL_EMAIL, recipients, msg.as_string())
                print(f"✅ E-mail enviado com sucesso via {SMTP_SERVER}:587 (STARTTLS)")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Erro de autenticação SMTP (porta 587): {e}")
                print("   Verifique se o GMAIL_APP_PASSWORD está correto")
                print("   Gere uma senha de app em: https://myaccount.google.com/apppasswords")
                return False
                
            except Exception as e:
                print(f"⚠️ Falha na porta 587/STARTTLS: {e}")
                print(f"🔄 Tentando fallback para porta 465/SSL...")
            
            # Tentativa 2: Porta 465 com SSL direto
            try:
                print(f"📡 Tentando conexão via {SMTP_SERVER}:465 (SSL)...")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context, timeout=30) as smtp:
                    if debug_smtp:
                        smtp.set_debuglevel(1)
                    smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
                    smtp.sendmail(GMAIL_EMAIL, recipients, msg.as_string())
                print(f"✅ E-mail enviado com sucesso via {SMTP_SERVER}:465 (SSL)")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Erro de autenticação SMTP (porta 465): {e}")
                print("   Verifique se o GMAIL_APP_PASSWORD está correto")
                return False
                
            except Exception as e:
                print(f"❌ Falha na porta 465/SSL: {e}")
                print("❌ Todas as tentativas de envio falharam")
                return False
        
        finally:
            if force_ipv4:
                socket.getaddrinfo = orig_getaddrinfo
                
    except Exception as e:
        print(f"❌ Erro inesperado ao enviar e-mail: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_email_body(has_update, movimentacoes):
    """
    Gera corpo do e-mail em HTML com formatação aprimorada
    """
    if has_update:
        status_message = '<p style="color: #d32f2f; font-weight: bold; font-size: 20px; text-align: center; background-color: #ffebee; padding: 15px; border-radius: 5px; margin: 20px 0;">🔴 PROCESSO ATUALIZADO</p>'
    else:
        status_message = '<p style="color: #388e3c; font-weight: bold; font-size: 20px; text-align: center; background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">🟢 PROCESSO SEM MOVIMENTAÇÃO</p>'
    
    email_body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Situação Processo TRF1</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #1976d2;
            border-bottom: 3px solid #1976d2;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        h3 {{
            color: #424242;
            margin-top: 25px;
        }}
        .info-box {{
            background-color: #e3f2fd;
            padding: 15px;
            border-left: 4px solid #1976d2;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .info-box p {{
            margin: 8px 0;
        }}
        .movimentacoes {{
            background-color: #fafafa;
            padding: 20px;
            border-radius: 4px;
            margin: 15px 0;
        }}
        .movimentacoes ol {{
            line-height: 1.8;
            padding-left: 25px;
        }}
        .movimentacoes li {{
            margin-bottom: 12px;
            padding: 8px;
            background-color: white;
            border-radius: 4px;
            border-left: 3px solid #e0e0e0;
        }}
        .movimentacoes li.recent {{
            font-weight: bold;
            border-left-color: #ff9800;
            background-color: #fff3e0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 0.9em;
            color: #757575;
        }}
        .footer p {{
            margin: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {status_message}
        
        <h2>📋 Processo TRF1 - 2ª Instância</h2>
        
        <div class="info-box">
            <p><strong>🆔 Número do Processo:</strong> {PROCESSO_NUMERO}</p>
            <p><strong>🔍 Fonte de Dados:</strong> API Oficial DataJud/CNJ</p>
            <p><strong>🕐 Consulta Realizada em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </div>
        
        <h3>📄 Movimentações do Processo</h3>
        
        <div class="movimentacoes">
            {f'<p style="margin-bottom: 15px;"><strong>📊 Total de movimentações:</strong> {len(movimentacoes)}</p>' if movimentacoes else ''}
            
            {'<ol>' if movimentacoes else '<p style="text-align: center; color: #757575; font-style: italic; padding: 20px;">❌ Nenhuma movimentação encontrada.</p>'}
            
            {''.join([f'<li class="{"recent" if i < 3 else ""}">{mov}</li>' for i, mov in enumerate(movimentacoes)])}
            
            {'</ol>' if movimentacoes else ''}
        </div>
        
        <div class="footer">
            <p><strong>🤖 Robô TRF1 Monitor v3.1</strong></p>
            <p>🔗 Método: API Oficial DataJud/CNJ</p>
            <p>🌐 Endpoint: {DATAJUD_API_URL}</p>
            <p style="margin-top: 15px; font-size: 0.85em;">
                Este é um e-mail automático gerado pelo sistema de monitoramento de processos TRF1.
                As informações são obtidas diretamente da API oficial do DataJud/CNJ.
            </p>
        </div>
    </div>
</body>
</html>
    """
    
    return email_body

def main():
    """
    Função principal do robô
    """
    print("=" * 80)
    print("🤖 ROBÔ TRF1 - MONITORAMENTO VIA API DATAJUD v3.1")
    print("=" * 80)
    print(f"🕐 Iniciando monitoramento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📋 Processo: {PROCESSO_NUMERO}")
    print(f"🔗 Método: API Oficial DataJud/CNJ")
    print(f"🌐 Endpoint: {DATAJUD_API_URL}")
    print("=" * 80)
    
    # Consultar processo via API
    api_response = consultar_processo_datajud(PROCESSO_NUMERO_LIMPO)
    
    if not api_response:
        print("❌ ERRO: Não foi possível consultar a API DataJud")
        
        # Enviar e-mail de erro
        error_subject = f"❌ ERRO API - Situação Processo TRF1 - {datetime.now().strftime('%d/%m/%Y')}"
        error_body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px; }}
        .error-box {{ background-color: #ffebee; padding: 20px; border-left: 4px solid #d32f2f; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="error-box">
        <p style="color: #d32f2f; font-weight: bold; font-size: 18px;">❌ ERRO NA CONSULTA DA API DATAJUD</p>
        <p>Não foi possível acessar a API oficial do DataJud/CNJ.</p>
        <p><strong>📋 Processo:</strong> {PROCESSO_NUMERO}</p>
        <p><strong>🌐 Endpoint:</strong> {DATAJUD_API_URL}</p>
        <p><strong>🕐 Tentativa em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        <p style="margin-top: 20px; font-size: 0.9em; color: #757575;">🤖 Robô TRF1 Monitor v3.1 - DataJud API</p>
    </div>
</body>
</html>
        """
        
        send_email_robust(error_subject, error_body)
        print("=" * 80)
        return
    
    # Extrair movimentações
    movimentacoes_atuais = extrair_movimentacoes(api_response)
    
    if not movimentacoes_atuais:
        print("⚠️ Nenhuma movimentação encontrada")
    else:
        print(f"✅ Extraídas {len(movimentacoes_atuais)} movimentações")
    
    # Carregar movimentações anteriores
    movimentacoes_anteriores = load_previous_movs()
    print(f"📂 Movimentações anteriores: {len(movimentacoes_anteriores)}")
    
    # Verificar atualizações
    has_update = check_for_updates(movimentacoes_atuais, movimentacoes_anteriores)
    
    if has_update:
        print("🔴 ATUALIZAÇÃO DETECTADA!")
    else:
        print("🟢 Nenhuma atualização detectada")
    
    # Salvar movimentações atuais
    save_current_movs(movimentacoes_atuais)
    print("💾 Movimentações salvas para próxima comparação")
    
    # Gerar e enviar e-mail
    data_consulta = datetime.now().strftime("%d/%m/%Y")
    email_subject = f"Situação Processo TRF1 - {data_consulta}"
    email_body = generate_email_body(has_update, movimentacoes_atuais)
    
    print("📧 Enviando e-mail...")
    success = send_email_robust(email_subject, email_body)
    
    if success:
        print("✅ Monitoramento concluído com sucesso!")
    else:
        print("❌ Erro no envio do e-mail")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
