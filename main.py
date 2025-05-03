from playwright.sync_api import sync_playwright
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import os
import json

# Configuração do acesso ao Google Sheets via variável de ambiente
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

if not creds_json:
    raise Exception("A variável de ambiente GOOGLE_CREDENTIALS_JSON não está definida.")

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Abrir a planilha e selecionar a aba ativa
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1iz9jtvIrybDbTYuyCdUCmCz3Idp6uzVtuDMFflPoIWY/edit").sheet1

# Lê os IMOs digitados na célula B3 (pode ser separados por vírgula)
raw_imo = sheet.acell("B3").value
imos = [imo.strip() for imo in raw_imo.split(",") if imo.strip()]

def buscar_navios():
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://login.sppilots.com.br/santos")

        page.fill('input[name="usuario"]', "37973919864")
        page.fill('input[name="senha"]', "37973919864")
        page.click('button:has-text("Entrar")')
        page.wait_for_timeout(3000)

        try:
            page.click('button:has-text("Entendi")')
        except:
            pass

        page.wait_for_selector("table")

        # Coleta todas as linhas das duas tabelas
        tabelas = page.query_selector_all("table")
        todas_linhas = []
        for tabela in tabelas:
            linhas = tabela.query_selector_all("tbody tr")
            for linha in linhas:
                colunas = linha.query_selector_all("td")
                if len(colunas) >= 6:
                    dados = [col.inner_text().strip() for col in colunas]
                    resultado = {
                        "IMO": dados[0],
                        "NAVIO": dados[1],
                        "MV": dados[2],
                        "LOC1": dados[3],
                        "LOC2": dados[4],
                        "POB": dados[5]
                    }
                    if resultado["IMO"] in imos:
                        resultados.append(resultado)
        browser.close()
    return resultados

def atualizar_planilha(dados):
    sheet.batch_clear(["A6:F1000"])
    sheet.update("A5:F5", [["IMO", "NAVIO", "MV", "LOC#1", "LOC#2", "POB"]])
    linhas = [[d["IMO"], d["NAVIO"], d["MV"], d["LOC1"], d["LOC2"], d["POB"]] for d in dados]
    if linhas:
        sheet.update(f"A6:F{6 + len(linhas) - 1}", linhas)

if __name__ == "__main__":
    navios_encontrados = buscar_navios()
    atualizar_planilha(navios_encontrados)
