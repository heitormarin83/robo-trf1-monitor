# Guia Rápido de Instalação - Robô TRF1

## Instalação em 5 Passos

### 1. Preparar o Ambiente
```bash
# Instalar dependências
pip3 install requests beautifulsoup4 yagmail

# Fazer download dos arquivos do projeto
# (copiar todos os arquivos .py e .sh para um diretório)
```

### 2. Configurar Gmail
1. Acesse [myaccount.google.com](https://myaccount.google.com)
2. Vá em "Segurança" → "Verificação em duas etapas"
3. Clique em "Senhas de app"
4. Selecione "E-mail" e "Windows Computer"
5. Copie a senha de 16 caracteres

### 3. Configurar o Script
Edite `monitor_trf1.py` e altere:
```python
EMAIL_USER = "seu.email@gmail.com"
EMAIL_APP_PASSWORD = "sua_app_password_aqui"
EMAIL_RECIPIENT = "destinatario@gmail.com"
```

### 4. Testar o Sistema
```bash
# Teste de e-mail
python3 test_email.py

# Teste completo
python3 monitor_trf1.py
```

### 5. Configurar Execução Automática
```bash
# Tornar scripts executáveis
chmod +x *.sh

# Configurar agendamento diário
./setup_cron.sh
```

## Verificação

✅ **E-mail de teste enviado com sucesso**  
✅ **Script de monitoramento executado**  
✅ **Agendamento configurado no cron**  
✅ **Log criado em trf1_monitor.log**

## Comandos Úteis

```bash
# Ver agendamentos
crontab -l

# Ver logs
tail -f trf1_monitor.log

# Executar manualmente
./run_trf1_monitor.sh

# Remover agendamento
crontab -l | grep -v run_trf1_monitor.sh | crontab -
```

---
**O robô está pronto! Ele executará automaticamente todos os dias às 9:00.**

