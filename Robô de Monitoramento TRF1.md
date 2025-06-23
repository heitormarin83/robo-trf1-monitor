# Robô de Monitoramento TRF1

## 📋 Visão Geral

Este projeto implementa um robô automatizado para monitoramento diário de processos judiciais no **Tribunal Regional Federal da 1ª Região (TRF1)**. O sistema verifica automaticamente se houve atualizações nos movimentos processuais e envia relatórios por e-mail.

## ✨ Características Principais

- 🤖 **Monitoramento Automatizado**: Verifica diariamente as movimentações do processo
- 🔍 **Detecção de Atualizações**: Compara movimentos atuais com anteriores
- 📧 **Notificação por E-mail**: Envia relatórios formatados via Gmail SMTP
- ⏰ **Execução Agendada**: Configuração para execução diária automática
- 📝 **Logs Detalhados**: Registro completo de todas as execuções
- ☁️ **Deploy na Nuvem**: Pronto para Railway/Heroku

## 📁 Arquivos do Projeto

### Scripts Principais
- `monitor_trf1_cloud.py` - Script principal (versão nuvem)
- `monitor_trf1.py` - Script principal (versão local)
- `test_email.py` - Script de teste para verificar envio de e-mails

### Configuração
- `requirements.txt` - Dependências Python
- `Dockerfile` - Configuração Docker
- `railway.toml` - Configuração Railway
- `.gitignore` - Arquivos a ignorar no Git

### Scripts de Automação (Local)
- `run_trf1_monitor.sh` - Script bash para execução com logs
- `setup_cron.sh` - Script para configurar agendamento automático

### Documentação
- `README.md` - Este arquivo
- `INSTALACAO.md` - Guia rápido de instalação local
- `GUIA_GITHUB.md` - Passo a passo GitHub
- `GUIA_RAILWAY.md` - Passo a passo Railway
- `DEPLOY_RAPIDO.md` - Resumo rápido de deploy

## 🚀 Instalação Rápida

### Opção 1: Deploy na Nuvem (Recomendado)
1. Siga o `GUIA_GITHUB.md` para configurar repositório
2. Siga o `GUIA_RAILWAY.md` para deploy na nuvem
3. Configure as variáveis de ambiente no Railway

### Opção 2: Instalação Local
1. Siga o `INSTALACAO.md` para instalação local
2. Configure cron para execução automática

## ⚙️ Configuração

### Variáveis de Ambiente (Nuvem)
```
EMAIL_USER=seu.email@gmail.com
EMAIL_APP_PASSWORD=sua_app_password_16_chars
EMAIL_RECIPIENT=destinatario@gmail.com
```

### Configuração Local
Edite `monitor_trf1.py`:
```python
EMAIL_USER = "seu.email@gmail.com"
EMAIL_APP_PASSWORD = "sua_app_password_aqui"
EMAIL_RECIPIENT = "destinatario@gmail.com"
```

## 📧 Configuração Gmail

1. **Habilitar verificação em duas etapas** na conta Google
2. **Criar App Password**:
   - Acesse [myaccount.google.com](https://myaccount.google.com)
   - Segurança → Verificação em duas etapas → Senhas de app
   - Selecione "E-mail" e "Windows Computer"
   - Copie a senha de 16 caracteres

## 🔄 Como Funciona

1. **Acesso**: Sistema acessa URL do processo TRF1
2. **Extração**: Utiliza BeautifulSoup para extrair movimentos
3. **Comparação**: Compara com movimentos da execução anterior
4. **Detecção**: Identifica se houve atualizações
5. **Relatório**: Cria e-mail formatado em HTML
6. **Envio**: Envia via Gmail SMTP
7. **Armazenamento**: Salva movimentos para próxima comparação

## 📊 Formato do E-mail

**Assunto**: `Situação Processo TRF1 - DD/MM/AAAA`

**Status**:
- 🔴 **PROCESSO ATUALIZADO** (quando há mudanças)
- 🟢 **PROCESSO SEM MOVIMENTAÇÃO** (quando não há mudanças)

**Conteúdo**:
- Lista completa de movimentos
- Data e hora da consulta
- Total de movimentações

## 🛠️ Comandos Úteis

### Local
```bash
# Testar e-mail
python3 test_email.py

# Executar monitoramento
python3 monitor_trf1.py

# Configurar agendamento
./setup_cron.sh

# Ver logs
tail -f trf1_monitor.log
```

### Git
```bash
# Configurar
git config --global user.name "Seu Nome"
git config --global user.email "seu.email@gmail.com"

# Enviar mudanças
git add .
git commit -m "Atualização"
git push
```

## 🔧 Troubleshooting

### Problemas Comuns

**Erro de autenticação Gmail:**
- Verificar App Password
- Confirmar verificação em duas etapas ativada

**Erro ao acessar TRF1:**
- Verificar conectividade
- Confirmar URL do processo

**Cron não executa:**
- Verificar serviço: `sudo systemctl status cron`
- Verificar permissões: `chmod +x *.sh`

## 💰 Custos

### Railway (Nuvem)
- ✅ **$5 gratuito/mês**
- ✅ **Suficiente para o robô**
- ✅ **~$1-2 de uso real**

### Local
- ✅ **Totalmente gratuito**
- ⚠️ **Depende do seu computador**

## 🔒 Segurança

- ✅ Use sempre App Password (nunca senha principal)
- ✅ Mantenha credenciais em variáveis de ambiente
- ✅ Repositório privado no GitHub
- ✅ Monitore logs regularmente

## 📞 Suporte

Para problemas:
1. Verifique logs (`trf1_monitor.log`)
2. Teste componentes individualmente
3. Consulte guias específicos
4. Verifique configurações de e-mail

## 📄 Licença

Este projeto foi desenvolvido para uso pessoal de monitoramento de processos judiciais.

---

**🎯 Desenvolvido para**: Monitoramento automatizado TRF1  
**📅 Versão**: 2.0  
**🚀 Status**: Pronto para produção

