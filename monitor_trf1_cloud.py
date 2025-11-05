#!/usr/bin/env python3
"""
ROBÔ TRF1 - MONITORAMENTO VIA API DATAJUD v4.0
Monitor de processos do TRF1 usando API oficial DataJud
Com suporte a Resend API e fallback SMTP
"""
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

# Configurações Resend API
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

# Configurações SMTP (fallback)
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
        
        # Pegar o primeiro resultado (processo encontrado)
        processo = hits[0].get('_source', {})
        
        # Extrair movimentações
        movimentos = processo.get('movimentos', [])
        
        print(f"📋 Encontradas {len(movimentos)} movimentações no processo")
        
        for mov in movimentos:
            movimentacoes.append({
                'data': mov.get('dataHora', 'Data não informada'),
                'descricao': mov.get('nome', 'Descrição não disponível'),
                'codigo': mov.get('codigo', ''),
                'complemento': mov.get('complementoNacional', {}).get('nome', '')
            })
        
        # Ordenar por data (mais recente primeiro)
        movimentacoes.sort(key=lambda x: x['data'], reverse=True)
        
        return movimentacoes
        
    except Exception as e:
        print(f"❌ Erro ao extrair movimentações: {e}")
        return []

def carregar_movimentacoes_anteriores():
    """
    Carrega movimentações anteriores do arquivo JSON
    """
    try:
        if os.path.exists(MOVIMENTOS_FILE):
            with open(MOVIMENTOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 Carregadas {len(data)} movimentações anteriores")
                return data
        else:
            print("📂 Nenhum arquivo de movimentações anteriores encontrado")
            return []
    except Exception as e:
        print(f"⚠️ Erro ao carregar movimentações anteriores: {e}")
        return []

def salvar_movimentacoes(movimentacoes):
    """
    Salva movimentações atuais no arquivo JSON
    """
    try:
        with open(MOVIMENTOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(movimentacoes, f, ensure_ascii=False, indent=2)
        print(f"💾 Salvas {len(movimentacoes)} movimentações no arquivo")
    except Exception as e:
        print(f"⚠️ Erro ao salvar movimentações: {e}")

def enviar_email_resend(subject, html_body, recipients):
    """
    Envia e-mail usando Resend API (método principal)
    """
    if not RESEND_API_KEY:
        print("⚠️ RESEND_API_KEY não configurada")
        return False
    
    try:
        print(f"📧 Tentando envio via Resend API...")
        print(f"📤 De: {RESEND_FROM_EMAIL}")
        print(f"📥 Para: {recipients}")
        
        # Preparar lista de destinatários
        to_list = [email.strip() for email in recipients.split(',')]
        
        # Fazer requisição para Resend API
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": to_list,
                "subject": subject,
                "html": html_body
            },
            timeout=30
        )
        
        if response.status_code in (200, 201):
            result = response.json()
            print(f"✅ E-mail enviado com sucesso via Resend!")
            print(f"📧 ID: {result.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Erro Resend: {response.status_code}")
            print(f"📄 Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao enviar via Resend: {e}")
        return False

def enviar_email_smtp(subject, html_body, recipients):
    """
    Envia e-mail usando SMTP tradicional (fallback)
    """
    if not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_APP_PASSWORD não configurada")
        return False
    
    # Preparar lista de destinatários
    to_list = [email.strip() for email in recipients.split(',')]
    
    # Criar mensagem
    msg = MIMEMultipart('alternative')
    msg['From'] = GMAIL_EMAIL
    msg['To'] = ', '.join(to_list)
    msg['Subject'] = subject
    
    # Adicionar corpo HTML
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(html_part)
    
    # Tentar porta 587 (STARTTLS)
    try:
        print(f"📡 Tentando conexão via {SMTP_SERVER}:587 (STARTTLS)...")
        
        if SMTP_FORCE_IPV4:
            original_getaddrinfo = socket.getaddrinfo
            def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
                return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            socket.getaddrinfo = getaddrinfo_ipv4_only
        
        server = smtplib.SMTP(SMTP_SERVER, 587, timeout=30)
        
        if SMTP_DEBUG:
            server.set_debuglevel(2)
        
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ E-mail enviado com sucesso via SMTP (porta 587)!")
        return True
        
    except Exception as e:
        print(f"⚠️ Falha na porta 587/STARTTLS: {e}")
        
        # Tentar porta 465 (SSL)
        try:
            print(f"🔄 Tentando fallback para porta 465/SSL...")
            
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context, timeout=30)
            
            if SMTP_DEBUG:
                server.set_debuglevel(2)
            
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ E-mail enviado com sucesso via SMTP (porta 465)!")
            return True
            
        except Exception as e2:
            print(f"❌ Falha na porta 465/SSL: {e2}")
            return False

def enviar_email(subject, html_body, recipients):
    """
    Envia e-mail tentando Resend primeiro, depois SMTP como fallback
    """
    print(f"\n{'='*60}")
    print(f"📧 INICIANDO ENVIO DE E-MAIL")
    print(f"{'='*60}")
    
    # Método 1: Tentar Resend API (recomendado para Railway)
    if RESEND_API_KEY:
        print(f"\n🎯 Método 1: Resend API")
        if enviar_email_resend(subject, html_body, recipients):
            return True
        print(f"⚠️ Resend falhou, tentando fallback SMTP...")
    else:
        print(f"⚠️ Resend API não configurada, usando SMTP direto")
    
    # Método 2: Fallback para SMTP tradicional
    print(f"\n🎯 Método 2: SMTP Tradicional")
    if enviar_email_smtp(subject, html_body, recipients):
        return True
    
    print(f"\n❌ Todas as tentativas de envio falharam")
    return False

def gerar_html_email(movimentacoes, tem_atualizacao, movimentos_anteriores):
    """
    Gera o HTML do e-mail com as movimentações
    """
    data_consulta = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    # Determinar mensagem de status
    if tem_atualizacao:
        status_msg = '<p style="color: #dc3545; font-weight: bold; font-size: 18px; text-align: center; background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">🔴 PROCESSO ATUALIZADO</p>'
    else:
        status_msg = '<p style="color: #28a745; font-weight: bold; font-size: 18px; text-align: center; background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">🟢 PROCESSO SEM MOVIMENTAÇÃO</p>'
    
    # Gerar HTML das movimentações
    movimentos_html = ""
    for i, mov in enumerate(movimentacoes[:10], 1):  # Mostrar até 10 movimentações
        # Destacar as 3 mais recentes
        destaque = ' style="background-color: #fff3cd; border-left: 4px solid #ffc107;"' if i <= 3 else ''
        
        movimentos_html += f"""
        <div{destaque} style="margin-bottom: 15px; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px;">
            <p style="margin: 0 0 8px 0;"><strong>#{i} - Data:</strong> {mov['data']}</p>
            <p style="margin: 0 0 8px 0;"><strong>Descrição:</strong> {mov['descricao']}</p>
            {f'<p style="margin: 0;"><strong>Complemento:</strong> {mov["complemento"]}</p>' if mov['complemento'] else ''}
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Situação Processo TRF1</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="color: #0056b3; margin: 0 0 10px 0;">📋 Situação Processo TRF1</h1>
            <p style="margin: 0; color: #666;">Consulta realizada em: {data_consulta}</p>
        </div>
        
        {status_msg}
        
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0 0 5px 0;"><strong>Processo:</strong> {PROCESSO_NUMERO}</p>
            <p style="margin: 0 0 5px 0;"><strong>Total de movimentações:</strong> {len(movimentacoes)}</p>
            <p style="margin: 0;"><strong>Movimentações anteriores:</strong> {len(movimentos_anteriores)}</p>
        </div>
        
        <h2 style="color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px;">
            📑 Últimas Movimentações
        </h2>
        
        <div style="margin-top: 20px;">
            {movimentos_html}
        </div>
        
        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; text-align: center; color: #666; font-size: 12px;">
            <p style="margin: 0;">🤖 Robô TRF1 Monitor v4.0 - Powered by DataJud API + Resend</p>
            <p style="margin: 5px 0 0 0;">Monitoramento automático de processos judiciais</p>
        </div>
    </body>
    </html>
    """
    
    return html

def main():
    print("\n" + "="*60)
    print("🤖 ROBÔ TRF1 - MONITORAMENTO VIA API DATAJUD v4.0")
    print("="*60 + "\n")
    
    # 1. Consultar processo via API
    api_response = consultar_processo_datajud(PROCESSO_NUMERO_LIMPO)
    
    if not api_response:
        print("❌ Falha na consulta à API. Abortando...")
        return
    
    # 2. Extrair movimentações
    movimentacoes_atuais = extrair_movimentacoes(api_response)
    
    if not movimentacoes_atuais:
        print("⚠️ Nenhuma movimentação encontrada")
        return
    
    print(f"\n📊 Movimentações extraídas: {len(movimentacoes_atuais)}")
    
    # 3. Carregar movimentações anteriores
    movimentacoes_anteriores = carregar_movimentacoes_anteriores()
    
    # 4. Verificar se houve atualização
    tem_atualizacao = len(movimentacoes_atuais) != len(movimentacoes_anteriores)
    
    if tem_atualizacao:
        print(f"\n🔴 ATUALIZAÇÃO DETECTADA!")
        print(f"   Anterior: {len(movimentacoes_anteriores)} movimentações")
        print(f"   Atual: {len(movimentacoes_atuais)} movimentações")
    else:
        print(f"\n🟢 Nenhuma atualização detectada")
        print(f"   Total: {len(movimentacoes_atuais)} movimentações")
    
    # 5. Gerar e-mail
    subject = f"Situação Processo TRF1 - {datetime.now().strftime('%d/%m/%Y')}"
    html_body = gerar_html_email(movimentacoes_atuais, tem_atualizacao, movimentacoes_anteriores)
    
    # 6. Enviar e-mail
    sucesso = enviar_email(subject, html_body, EMAIL_RECIPIENT)
    
    if sucesso:
        # 7. Salvar movimentações atuais
        salvar_movimentacoes(movimentacoes_atuais)
        print(f"\n✅ Processo concluído com sucesso!")
    else:
        print(f"\n❌ Falha no envio do e-mail")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
