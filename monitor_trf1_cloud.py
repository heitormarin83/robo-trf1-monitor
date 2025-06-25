import requests
import json
import os
from datetime import datetime
import yagmail

# Configurações da API DataJud
DATAJUD_API_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_trf1/_search"
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Configurações do processo
PROCESSO_NUMERO = "1002946-59.2025.4.01.9999"
PROCESSO_NUMERO_LIMPO = PROCESSO_NUMERO.replace("-", "" ).replace(".", "")

# Configurações de e-mail (usando variáveis de ambiente)
EMAIL_USER = os.getenv("EMAIL_USER", "heitor.a.marin@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "heitor.a.marin@gmail.com")

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

def send_email_yagmail(subject, body):
    """
    Envia e-mail usando yagmail
    """
    try:
        if not EMAIL_APP_PASSWORD:
            print("❌ ERRO: App Password do Gmail não configurada!")
            return False
        
        print(f"📧 Enviando e-mail para: {EMAIL_RECIPIENT}")
        
        yag = yagmail.SMTP(EMAIL_USER, EMAIL_APP_PASSWORD)
        yag.send(
            to=EMAIL_RECIPIENT,
            subject=subject,
            contents=body
        )
        
        print(f"✅ E-mail enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False

def generate_email_body(has_update, movimentacoes):
    """
    Gera corpo do e-mail em HTML
    """
    if has_update:
        status_message = '<p style="color: red; font-weight: bold; font-size: 18px;">🔴 PROCESSO ATUALIZADO</p>'
    else:
        status_message = '<p style="color: green; font-weight: bold; font-size: 18px;">🟢 PROCESSO SEM MOVIMENTAÇÃO</p>'
    
    email_body = f"""
    <html>
    <body>
        {status_message}
        <hr>
        <h3>📋 Processo TRF1 - 2ª Instância</h3>
        <p><strong>🆔 Número:</strong> {PROCESSO_NUMERO}</p>
        <p><strong>🔍 Fonte:</strong> API Oficial DataJud/CNJ</p>
        
        <h3>📄 Movimentações do Processo:</h3>
        
        {f'<p><strong>📊 Total de movimentações:</strong> {len(movimentacoes)}</p>' if movimentacoes else ''}
        
        {'<ol style="line-height: 1.8; padding-left: 20px;">' if movimentacoes else '<p><em>❌ Nenhuma movimentação encontrada.</em></p>'}
        
        {''.join([f'<li style="margin-bottom: 10px; {"font-weight: bold;" if i < 3 else ""}">{mov}</li>' for i, mov in enumerate(movimentacoes)])}
        
        {'</ol>' if movimentacoes else ''}
        
        <hr>
        <p><small>🕐 Consulta realizada em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</small></p>
        <p><small>🔗 Método: API Oficial DataJud/CNJ</small></p>
        <p><small>🤖 Robô TRF1 v3.0 - DataJud API</small></p>
    </body>
    </html>
    """
    
    return email_body

def main():
    """
    Função principal do robô
    """
    print("=" * 80)
    print("🤖 ROBÔ TRF1 - MONITORAMENTO VIA API DATAJUD v3.0")
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
        <p style="color: red; font-weight: bold;">❌ ERRO NA CONSULTA DA API DATAJUD</p>
        <p>Não foi possível acessar a API oficial do DataJud/CNJ.</p>
        <p><strong>📋 Processo:</strong> {PROCESSO_NUMERO}</p>
        <p><strong>🌐 Endpoint:</strong> {DATAJUD_API_URL}</p>
        <p><strong>🕐 Tentativa em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        <p><small>🤖 Robô TRF1 v3.0 - DataJud API</small></p>
        """
        
        send_email_yagmail(error_subject, error_body)
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
    email_subject = f"📋 Situação Processo TRF1 - {data_consulta}"
    email_body = generate_email_body(has_update, movimentacoes_atuais)
    
    print("📧 Enviando e-mail...")
    success = send_email_yagmail(email_subject, email_body)
    
    if success:
        print("✅ Monitoramento concluído com sucesso!")
    else:
        print("❌ Erro no envio do e-mail")
    
    print("=" * 80)

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()


