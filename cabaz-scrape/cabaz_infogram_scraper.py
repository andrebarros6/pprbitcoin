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
        Processa os dados brutos extraídos e organiza especificamente para o cabaz alimentar
        
        Args:
            raw_data (dict): Dados brutos extraídos
            
        Returns:
            list: Lista de dicionários com dados organizados
        """
        parsed_data = []
        
        # Combinar todos os textos encontrados
        all_texts = []
        
        if "text_values" in raw_data:
            all_texts.extend([item['text'] for item in raw_data['text_values']])
        
        if "svg_data" in raw_data:
            all_texts.extend([item['content'] for item in raw_data['svg_data']])
            
        if "div_data" in raw_data:
            all_texts.extend([item['text'] for item in raw_data['div_data']])
        
        # Padrões para identificar dados do cabaz alimentar
        patterns = {
            'euro_value': r'(\d+[.,]\d+)\s*€',
            'percentage': r'(\d+[.,]\d+)\s*%',
            'date': r'(20\d{2})',
            'month': r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)',
            'product': r'([A-Za-záàâãéèêíìôóõúùûçÁÀÂÃÉÈÊÍÌÔÓÕÚÙÛÇ\s]+)'
        }
        
        for text in all_texts:
            entry = {'raw_text': text}
            
            # Extrair valores em euros
            euro_matches = re.findall(patterns['euro_value'], text, re.IGNORECASE)
            if euro_matches:
                entry['valor_euros'] = [float(val.replace(',', '.')) for val in euro_matches]
            
            # Extrair percentagens
            perc_matches = re.findall(patterns['percentage'], text, re.IGNORECASE)
            if perc_matches:
                entry['percentagem'] = [float(val.replace(',', '.')) for val in perc_matches]
            
            # Extrair anos
            year_matches = re.findall(patterns['date'], text)
            if year_matches:
                entry['ano'] = year_matches
            
            # Se encontrou dados relevantes, adiciona à lista
            if any(key in entry for key in ['valor_euros', 'percentagem', 'ano']):
                parsed_data.append(entry)
        
        return parsed_data

    def save_data(self, data, filename=None):
        """
        Salva os dados em diferentes formatos
        
        Args:
            data (list): Dados para salvar
            filename (str): Nome base do arquivo (sem extensão)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cabaz_alimentar_{timestamp}"
        
        # Salvar como JSON
        json_filename = f"{filename}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Dados salvos em: {json_filename}")
        
        # Salvar como CSV se os dados estão estruturados
        if data and isinstance(data, list) and all(isinstance(item, dict) for item in data):
            try:
                df = pd.json_normalize(data)
                csv_filename = f"{filename}.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8')
                print(f"✓ Dados salvos em: {csv_filename}")
            except Exception as e:
                print(f"⚠ Não foi possível salvar CSV: {e}")
        
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
            print("\n📊 Processando dados extraídos...")
            parsed_data = scraper.parse_cabaz_data(raw_data)
            
            print(f"✓ Total de entradas processadas: {len(parsed_data)}")
            
            # Mostrar algumas amostras
            if parsed_data:
                print("\n🔍 Primeiras entradas encontradas:")
                for i, entry in enumerate(parsed_data[:5]):
                    print(f"{i+1}. {entry}")
            
            # Salvar dados
            filename = scraper.save_data({
                'metadata': {
                    'url': url,
                    'extraction_date': datetime.now().isoformat(),
                    'total_entries': len(parsed_data)
                },
                'raw_data': raw_data,
                'parsed_data': parsed_data
            })
            
            print(f"\n✅ Extração concluída! Dados salvos em: {filename}")
            
        else:
            print("❌ Nenhum dado foi extraído. A página pode ter mudado ou há problemas de carregamento.")
            
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()