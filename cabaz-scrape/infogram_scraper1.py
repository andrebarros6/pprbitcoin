#!/usr/bin/env python3
"""
Ferramenta de Webscraping para dados do Infogram - Cabaz Alimentar ADL
Este script extrai dados de gráficos do Infogram que carregam conteúdo via JavaScript.
"""

import time
import json
import csv
import pandas as pd
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re

class InfogramScraper:
    def __init__(self, headless=True, timeout=20):
        """
        Inicializa o scraper para Infogram
        
        Args:
            headless (bool): Se True, roda o navegador sem interface gráfica
            timeout (int): Timeout em segundos para aguardar elementos
        """
        self.timeout = timeout
        self.driver = None
        self.setup_driver(headless)
        
    def setup_driver(self, headless=True):
        """Configura o driver do Chrome/Chromium"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Driver Chrome configurado com sucesso")
        except Exception as e:
            print(f"✗ Erro ao configurar Chrome driver: {e}")
            print("Certifique-se de que o ChromeDriver está instalado")
            raise

    def extract_infogram_data(self, url):
        """
        Extrai dados do Infogram da URL fornecida
        
        Args:
            url (str): URL do infograma
            
        Returns:
            dict: Dados extraídos organizados
        """
        print(f"🔍 Acessando: {url}")
        
        try:
            # Navega para a página
            self.driver.get(url)
            
            # Aguarda o carregamento do conteúdo
            print("⏳ Aguardando carregamento do conteúdo...")
            time.sleep(5)
            
            # Tenta encontrar elementos com dados
            data_extracted = {}
            
            # Método 1: Procurar por scripts com dados JSON
            scripts = self.driver.find_elements(By.TAG_NAME, "script")
            for script in scripts:
                script_content = script.get_attribute("innerHTML")
                if script_content and ("data" in script_content or "chart" in script_content):
                    # Tenta extrair JSON dos scripts
                    json_matches = re.findall(r'\{[^{}]*"data"[^{}]*\}', script_content)
                    for match in json_matches:
                        try:
                            data = json.loads(match)
                            if "data" in data:
                                data_extracted["script_data"] = data
                                print("✓ Dados encontrados em script JSON")
                                break
                        except:
                            continue
            
            # Método 2: Procurar por elementos de texto com valores numéricos
            text_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '€') or contains(text(), ',') or contains(text(), '.')]")
            values = []
            for element in text_elements:
                text = element.text.strip()
                if text and (('€' in text) or (re.search(r'\d+[.,]\d+', text))):
                    values.append({
                        'text': text,
                        'tag': element.tag_name,
                        'class': element.get_attribute('class')
                    })
            
            if values:
                data_extracted["text_values"] = values
                print(f"✓ Encontrados {len(values)} elementos com valores")
            
            # Método 3: Procurar por elementos SVG (gráficos)
            svg_elements = self.driver.find_elements(By.TAG_NAME, "svg")
            svg_data = []
            for svg in svg_elements:
                # Procurar por texto dentro do SVG
                svg_texts = svg.find_elements(By.TAG_NAME, "text")
                for text_elem in svg_texts:
                    text_content = text_elem.text.strip()
                    if text_content:
                        svg_data.append({
                            'content': text_content,
                            'x': text_elem.get_attribute('x'),
                            'y': text_elem.get_attribute('y')
                        })
            
            if svg_data:
                data_extracted["svg_data"] = svg_data
                print(f"✓ Encontrados {len(svg_data)} elementos SVG com texto")
            
            # Método 4: Capturar HTML completo para análise posterior
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Procurar por divs com classes relacionadas a dados
            data_divs = soup.find_all('div', class_=re.compile(r'(data|chart|value|number)', re.I))
            if data_divs:
                div_data = []
                for div in data_divs:
                    text = div.get_text(strip=True)
                    if text and (('€' in text) or re.search(r'\d+', text)):
                        div_data.append({
                            'text': text,
                            'class': div.get('class', []),
                            'id': div.get('id', '')
                        })
                
                if div_data:
                    data_extracted["div_data"] = div_data
                    print(f"✓ Encontrados {len(div_data)} divs com dados")
            
            # Método 5: Procurar por tabelas
            tables = soup.find_all('table')
            if tables:
                table_data = []
                for table in tables:
                    rows = []
                    for row in table.find_all('tr'):
                        cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                        if any(cells):  # Se há pelo menos uma célula com conteúdo
                            rows.append(cells)
                    if rows:
                        table_data.append(rows)
                
                if table_data:
                    data_extracted["table_data"] = table_data
                    print(f"✓ Encontradas {len(table_data)} tabelas")
            
            return data_extracted
            
        except Exception as e:
            print(f"✗ Erro durante extração: {e}")
            return {}

    def parse_cabaz_data(self, raw_data):
        """
        Processa os dados brutos e organiza especificamente para o cabaz alimentar:
        - Extrai DATAS (mês/ano) 
        - Extrai VALORES em EUROS (€)
        - Organiza para CSV com colunas: Data, Valor_Euros
        
        Args:
            raw_data (dict): Dados brutos extraídos
            
        Returns:
            list: Lista de dicionários com dados do cabaz [{data, valor_euros}, ...]
        """
        cabaz_records = []
        
        # Combinar todos os textos encontrados
        all_texts = []
        
        if "text_values" in raw_data:
            all_texts.extend([item['text'] for item in raw_data['text_values']])
        
        if "svg_data" in raw_data:
            all_texts.extend([item['content'] for item in raw_data['svg_data']])
            
        if "div_data" in raw_data:
            all_texts.extend([item['text'] for item in raw_data['div_data']])
        
        # Padrões específicos para cabaz alimentar
        patterns = {
            'euro_value': r'(\d+[.,]\d+)\s*€',  # Valores monetários
            'year': r'(20\d{2})',              # Anos (2020, 2021, etc.)
            'month_pt': r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)',
            'month_en': r'(january|february|march|april|may|june|july|august|september|october|november|december)',
            'date_format': r'(\d{1,2}[/-]\d{1,2}[/-]20\d{2})',  # Formatos de data
            'month_year': r'(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s*(20\d{2})',
        }
        
        # Mapeamento de meses para números
        month_map = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12',
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05',
            'jun': '06', 'jul': '07', 'ago': '08', 'set': '09', 'out': '10',
            'nov': '11', 'dez': '12'
        }
        
        print(f"🔍 Analisando {len(all_texts)} textos encontrados...")
        
        # Procurar por pares data-valor
        for text in all_texts:
            text = text.lower().strip()
            
            # Extrair valores em euros
            euro_matches = re.findall(patterns['euro_value'], text, re.IGNORECASE)
            
            if euro_matches:
                # Tentar encontrar data no mesmo texto
                data_encontrada = None
                
                # Método 1: Procurar ano
                year_matches = re.findall(patterns['year'], text)
                if year_matches:
                    ano = year_matches[0]
                    
                    # Procurar mês em português
                    month_matches = re.findall(patterns['month_pt'], text, re.IGNORECASE)
                    if month_matches:
                        mes = month_map.get(month_matches[0].lower(), '01')
                        data_encontrada = f"{mes}/{ano}"
                    else:
                        # Se só tem ano, assume janeiro
                        data_encontrada = f"01/{ano}"
                
                # Método 2: Formato mês-ano abreviado
                if not data_encontrada:
                    month_year_matches = re.findall(patterns['month_year'], text, re.IGNORECASE)
                    if month_year_matches:
                        mes_abrev, ano = month_year_matches[0]
                        mes_num = month_map.get(mes_abrev.lower(), '01')
                        data_encontrada = f"{mes_num}/{ano}"
                
                # Método 3: Data formato DD/MM/YYYY ou DD-MM-YYYY
                if not data_encontrada:
                    date_matches = re.findall(patterns['date_format'], text)
                    if date_matches:
                        data_encontrada = date_matches[0].replace('-', '/')
                
                # Se encontrou valor em euro, criar registro
                for euro_value in euro_matches:
                    valor_limpo = float(euro_value.replace(',', '.'))
                    
                    record = {
                        'Data': data_encontrada or 'Data não identificada',
                        'Valor_Euros': valor_limpo,
                        'Texto_Original': text[:100] + '...' if len(text) > 100 else text
                    }
                    cabaz_records.append(record)
                    print(f"✓ Encontrado: {data_encontrada or 'S/Data'} -> {valor_limpo}€")
        
        # Ordenar por data (tentar converter para ordenação cronológica)
        def sort_key(record):
            data = record['Data']
            if data == 'Data não identificada':
                return '0000/00'
            try:
                # Converter MM/YYYY para YYYY/MM para ordenação
                if '/' in data:
                    parts = data.split('/')
                    if len(parts) == 2:
                        return f"{parts[1]}/{parts[0]}"
                return data
            except:
                return data
        
        cabaz_records.sort(key=sort_key)
        
        print(f"📊 Total de registros do cabaz encontrados: {len(cabaz_records)}")
        return cabaz_records

    def save_data(self, data, filename=None):
        """
        Salva os dados do cabaz em formato CSV otimizado
        
        Args:
            data (list): Lista de registros do cabaz [{Data, Valor_Euros}, ...]
            filename (str): Nome base do arquivo (sem extensão)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cabaz_alimentar_{timestamp}"
        
        # Se os dados são uma lista de registros do cabaz, salvar diretamente em CSV
        if isinstance(data, list) and data and all('Data' in item and 'Valor_Euros' in item for item in data):
            # Salvar CSV principal (dados limpos)
            csv_filename = f"{filename}.csv"
            df = pd.DataFrame(data)
            
            # Reorganizar colunas: Data, Valor_Euros primeiro
            cols = ['Data', 'Valor_Euros'] + [col for col in df.columns if col not in ['Data', 'Valor_Euros']]
            df = df[cols]
            
            df.to_csv(csv_filename, index=False, encoding='utf-8', decimal=',')
            print(f"✅ Dados do cabaz salvos em: {csv_filename}")
            
            # Mostrar prévia dos dados
            print(f"\n📋 Prévia dos dados (primeiros 5 registros):")
            print(df.head().to_string(index=False))
            
            # Estatísticas resumidas
            if len(data) > 0:
                valores = [item['Valor_Euros'] for item in data if isinstance(item['Valor_Euros'], (int, float))]
                if valores:
                    print(f"\n📊 Estatísticas:")
                    print(f"   • Total de registros: {len(data)}")
                    print(f"   • Valor mínimo: {min(valores):.2f}€")
                    print(f"   • Valor máximo: {max(valores):.2f}€")
                    print(f"   • Valor médio: {sum(valores)/len(valores):.2f}€")
            
            return csv_filename
        
        # Fallback: salvar dados complexos em JSON
        else:
            json_filename = f"{filename}_completo.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Dados completos salvos em: {json_filename}")
            return json_filename

    def close(self):
        """Fecha o driver"""
        if self.driver:
            self.driver.quit()
            print("✓ Driver fechado")

def main():
    """Função principal para executar o scraper"""
    url = "https://infogram.com/cabaz-alimentar-desde-2022-adl-1hmr6g8oqqrwz2n"
    
    scraper = None
    try:
        # Inicializar o scraper
        print("🚀 Iniciando extração de dados do Infogram...")
        scraper = InfogramScraper(headless=True)
        
        # Extrair dados
        raw_data = scraper.extract_infogram_data(url)
        
        if raw_data:
            print("\n📊 Processando dados do cabaz alimentar...")
            cabaz_data = scraper.parse_cabaz_data(raw_data)
            
            if cabaz_data:
                print(f"✓ Encontrados {len(cabaz_data)} registros de preços do cabaz")
                
                # Salvar dados do cabaz em CSV
                csv_file = scraper.save_data(cabaz_data)
                print(f"\n✅ Dados do cabaz salvos em formato CSV: {csv_file}")
                
                # Também salvar dados completos em JSON para backup
                complete_data = {
                    'metadata': {
                        'url': url,
                        'extraction_date': datetime.now().isoformat(),
                        'total_records': len(cabaz_data),
                        'description': 'Preços do Cabaz Alimentar ADL - Datas e Valores em Euros'
                    },
                    'cabaz_records': cabaz_data,
                    'raw_extraction': raw_data
                }
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_file = scraper.save_data(complete_data, f"cabaz_backup_{timestamp}")
                
            else:
                print("❌ Nenhum registro de preço do cabaz foi encontrado.")
                print("💡 Verifique se a página carregou corretamente ou se a estrutura mudou.")
                
        else:
            print("❌ Nenhum dado foi extraído. A página pode ter mudado ou há problemas de carregamento.")
            
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()