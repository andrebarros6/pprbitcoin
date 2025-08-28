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
        """Configura o driver do Chrome/Chromium com instalação automática do ChromeDriver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            # Tentar usar ChromeDriver do sistema primeiro
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Driver Chrome configurado com sucesso")
        except Exception as e:
            print(f"⚠ ChromeDriver não encontrado no sistema: {e}")
            print("🔧 Tentando instalação automática...")
            
            try:
                # Usar webdriver-manager para instalação automática
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✓ ChromeDriver instalado automaticamente!")
                
            except ImportError:
                print("❌ Para instalação automática, instale: pip install webdriver-manager")
                print("\n🛠 Soluções manuais:")
                print("Ubuntu/Debian: sudo apt install chromium-chromedriver")
                print("macOS: brew install chromedriver")
                print("Windows: Baixar de https://chromedriver.chromium.org/")
                raise Exception("ChromeDriver não disponível")
            except Exception as e2:
                print(f"❌ Falha na instalação automática: {e2}")
                raise

    def extract_infogram_data(self, url):
        """
        Extrai dados do Infogram com simulação de hover/mouse para tooltips
        
        Args:
            url (str): URL do infograma
            
        Returns:
            dict: Dados extraídos organizados
        """
        print(f"🔍 Acessando: {url}")
        
        try:
            # Navega para a página
            self.driver.get(url)
            
            # Aguarda o carregamento inicial
            print("⏳ Aguardando carregamento do conteúdo...")
            time.sleep(8)  # Mais tempo para gráficos JavaScript
            
            data_extracted = {}
            
            # Método 1: Simular hover em elementos SVG (pontos do gráfico)
            print("🖱️ Simulando interações do mouse para extrair tooltips...")
            tooltip_data = self.extract_hover_tooltips()
            if tooltip_data:
                data_extracted["tooltip_data"] = tooltip_data
                print(f"✓ Extraídos {len(tooltip_data)} tooltips")
            
            # Método 2: Procurar por scripts com dados JSON embutidos
            print("🔍 Procurando dados JSON em scripts...")
            json_data = self.extract_json_from_scripts()
            if json_data:
                data_extracted["json_data"] = json_data
                print("✓ Dados JSON encontrados")
            
            # Método 3: Interceptar requisições AJAX/XHR (dados dinâmicos)
            print("📡 Verificando requisições de dados...")
            network_data = self.check_network_requests()
            if network_data:
                data_extracted["network_data"] = network_data
                print("✓ Dados de rede encontrados")
            
            # Método 4: Elementos tradicionais (fallback)
            traditional_data = self.extract_traditional_elements()
            if traditional_data:
                data_extracted.update(traditional_data)
            
            return data_extracted
            
        except Exception as e:
            print(f"✗ Erro durante extração: {e}")
            return {}

    def extract_hover_tooltips(self):
        """Simula hover em pontos do gráfico para extrair tooltips"""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By
        
        tooltip_data = []
        actions = ActionChains(self.driver)
        
        try:
            # Procurar elementos que podem ser pontos de dados
            possible_selectors = [
                'circle',  # Pontos SVG
                '.data-point',
                '[data-value]',
                '.point',
                '.marker',
                'g circle',  # Círculos dentro de grupos SVG
                'path[d*="M"]',  # Caminhos SVG
                '.tooltip-trigger',
                '[role="img"] circle',
                'svg circle',
                'svg g circle'
            ]
            
            for selector in possible_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"   Testando {len(elements)} elementos com seletor: {selector}")
                    
                    for i, element in enumerate(elements[:20]):  # Limitar a 20 elementos por seletor
                        try:
                            # Scroll para o elemento se necessário
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            
                            # Simular hover
                            actions.move_to_element(element).perform()
                            time.sleep(1)  # Aguardar tooltip aparecer
                            
                            # Procurar por tooltips que apareceram
                            tooltip_selectors = [
                                '.tooltip',
                                '[role="tooltip"]',
                                '.data-tooltip',
                                '.chart-tooltip',
                                '.popup',
                                '.overlay',
                                '.info-box',
                                'div[style*="position: absolute"]',
                                'div[style*="z-index"]'
                            ]
                            
                            for tooltip_sel in tooltip_selectors:
                                tooltips = self.driver.find_elements(By.CSS_SELECTOR, tooltip_sel)
                                for tooltip in tooltips:
                                    if tooltip.is_displayed():
                                        text = tooltip.text.strip()
                                        if text and ('€' in text or re.search(r'\d', text)):
                                            tooltip_data.append({
                                                'text': text,
                                                'selector': selector,
                                                'tooltip_selector': tooltip_sel,
                                                'element_index': i
                                            })
                                            print(f"   ✓ Tooltip encontrado: {text[:50]}...")
                            
                            # Mover mouse para fora para esconder tooltip
                            actions.move_by_offset(100, 100).perform()
                            time.sleep(0.3)
                            
                        except Exception as e:
                            continue  # Pular elementos problemáticos
                            
                except Exception:
                    continue  # Pular seletores que não funcionam
            
            # Remover duplicatas
            seen = set()
            unique_tooltips = []
            for item in tooltip_data:
                text = item['text']
                if text not in seen:
                    seen.add(text)
                    unique_tooltips.append(item)
            
            return unique_tooltips
            
        except Exception as e:
            print(f"   ⚠ Erro na extração de tooltips: {e}")
            return []

    def extract_json_from_scripts(self):
        """Procura dados JSON embutidos nos scripts da página"""
        try:
            scripts = self.driver.find_elements(By.TAG_NAME, "script")
            json_data = []
            
            for script in scripts:
                try:
                    content = script.get_attribute("innerHTML")
                    if not content:
                        continue
                    
                    # Procurar por padrões de dados JSON
                    patterns = [
                        r'data\s*:\s*(\{[^}]*\}|\[[^\]]*\])',
                        r'chartData\s*[=:]\s*(\{.*?\}|\[.*?\])',
                        r'"data"\s*:\s*(\{.*?\}|\[.*?\])',
                        r'infogram.*?data.*?(\{.*?\}|\[.*?\])',
                        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.DOTALL)
                        for match in matches:
                            try:
                                # Tentar parsear JSON
                                data = json.loads(match)
                                if isinstance(data, (dict, list)):
                                    json_data.append({
                                        'data': data,
                                        'pattern': pattern,
                                        'size': len(str(data))
                                    })
                            except:
                                continue
                                
                except Exception:
                    continue
            
            return json_data if json_data else None
            
        except Exception as e:
            print(f"   ⚠ Erro na extração JSON: {e}")
            return None

    def check_network_requests(self):
        """Verifica requisições de rede que podem conter dados do gráfico"""
        try:
            # Habilitar logging de rede
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Aguardar um pouco para capturar requisições
            time.sleep(3)
            
            # Obter logs de rede
            logs = self.driver.get_log('performance')
            network_data = []
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if message['message']['method'] == 'Network.responseReceived':
                        url = message['message']['params']['response']['url']
                        if any(keyword in url.lower() for keyword in ['data', 'chart', 'api', 'json']):
                            network_data.append({
                                'url': url,
                                'timestamp': log['timestamp']
                            })
                except:
                    continue
            
            return network_data if network_data else None
            
        except Exception as e:
            print(f"   ⚠ Erro na verificação de rede: {e}")
            return None

    def extract_traditional_elements(self):
        """Método tradicional de extração (fallback)"""
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            data = {}
            
            # Procurar por elementos com valores
            text_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '€')]")
            if text_elements:
                values = []
                for element in text_elements:
                    text = element.text.strip()
                    if text:
                        values.append(text)
                data["text_values"] = values
            
            # Procurar SVGs
            svg_elements = soup.find_all('svg')
            if svg_elements:
                svg_data = []
                for svg in svg_elements:
                    texts = svg.find_all('text')
                    for text in texts:
                        if text.get_text(strip=True):
                            svg_data.append(text.get_text(strip=True))
                if svg_data:
                    data["svg_data"] = svg_data
            
            return data
            
        except Exception as e:
            print(f"   ⚠ Erro na extração tradicional: {e}")
            return {}

    def parse_cabaz_data(self, raw_data):
        """
        Processa os dados brutos (incluindo tooltips) e organiza para o cabaz alimentar:
        - Extrai DATAS (mês/ano) 
        - Extrai VALORES em EUROS (€)
        - Prioriza dados de tooltips (hover)
        
        Args:
            raw_data (dict): Dados brutos extraídos (com tooltips, JSON, etc.)
            
        Returns:
            list: Lista de dicionários com dados do cabaz [{data, valor_euros}, ...]
        """
        cabaz_records = []
        
        # Combinar todos os textos encontrados, priorizando tooltips
        all_texts = []
        
        # PRIORIDADE 1: Dados de tooltips (hover)
        if "tooltip_data" in raw_data:
            tooltip_texts = [item['text'] for item in raw_data['tooltip_data']]
            all_texts.extend(tooltip_texts)
            print(f"🎯 Priorizando {len(tooltip_texts)} tooltips encontrados")
        
        # PRIORIDADE 2: Dados JSON estruturados
        if "json_data" in raw_data:
            for json_item in raw_data['json_data']:
                json_texts = self.extract_text_from_json(json_item['data'])
                all_texts.extend(json_texts)
                print(f"📊 Adicionando dados JSON: {len(json_texts)} textos")
        
        # PRIORIDADE 3: Dados tradicionais
        if "text_values" in raw_data:
            all_texts.extend(raw_data['text_values'])
        
        if "svg_data" in raw_data:
            all_texts.extend(raw_data['svg_data'])
        
        # Padrões específicos para cabaz alimentar (melhorados para tooltips)
        patterns = {
            'euro_value': r'(\d+[.,]\d+)\s*€',  # Valores monetários
            'euro_tooltip': r'€\s*(\d+[.,]\d+)',  # Formato tooltip: €25,50
            'year': r'(20\d{2})',              # Anos (2020, 2021, etc.)
            'month_pt': r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)',
            'month_short': r'\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\b',
            'date_format': r'(\d{1,2}[/-]\d{1,2}[/-]20\d{2})',
            'tooltip_date': r'(\w+\s+20\d{2})',  # Formato tooltip: "Janeiro 2022"
            'year_month': r'(20\d{2})[/-](\d{1,2})',  # 2022/01 ou 2022-01
        }
        
        # Mapeamento de meses
        month_map = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12',
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05',
            'jun': '06', 'jul': '07', 'ago': '08', 'set': '09', 'out': '10',
            'nov': '11', 'dez': '12',
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        
        print(f"🔍 Analisando {len(all_texts)} textos (incluindo tooltips)...")
        
        for text in all_texts:
            if isinstance(text, dict) and 'text' in text:
                text = text['text']
            
            original_text = str(text)
            text_lower = original_text.lower().strip()
            
            # Extrair valores em euros (múltiplos padrões)
            euro_values = []
            
            # Padrão 1: 25,50€
            euro_matches1 = re.findall(patterns['euro_value'], text_lower, re.IGNORECASE)
            euro_values.extend(euro_matches1)
            
            # Padrão 2: €25,50
            euro_matches2 = re.findall(patterns['euro_tooltip'], text_lower, re.IGNORECASE)
            euro_values.extend(euro_matches2)
            
            if euro_values:
                # Tentar encontrar data no mesmo texto
                data_encontrada = None
                
                # Método 1: Tooltip com formato "Janeiro 2022: €25,50"
                tooltip_date_matches = re.findall(patterns['tooltip_date'], text_lower, re.IGNORECASE)
                if tooltip_date_matches:
                    date_str = tooltip_date_matches[0].strip()
                    parts = date_str.split()
                    if len(parts) >= 2:
                        month_name = parts[0].lower()
                        year = parts[1]
                        mes_num = month_map.get(month_name, '01')
                        data_encontrada = f"{mes_num}/{year}"
                
                # Método 2: Procurar ano e mês separadamente
                if not data_encontrada:
                    year_matches = re.findall(patterns['year'], text_lower)
                    if year_matches:
                        ano = year_matches[0]
                        
                        # Procurar mês completo
                        month_matches = re.findall(patterns['month_pt'], text_lower, re.IGNORECASE)
                        if month_matches:
                            mes = month_map.get(month_matches[0].lower(), '01')
                            data_encontrada = f"{mes}/{ano}"
                        else:
                            # Procurar mês abreviado
                            month_short_matches = re.findall(patterns['month_short'], text_lower, re.IGNORECASE)
                            if month_short_matches:
                                mes = month_map.get(month_short_matches[0].lower(), '01')
                                data_encontrada = f"{mes}/{ano}"
                            else:
                                data_encontrada = f"01/{ano}"  # Default janeiro
                
                # Método 3: Formato YYYY/MM
                if not data_encontrada:
                    year_month_matches = re.findall(patterns['year_month'], text_lower)
                    if year_month_matches:
                        year, month = year_month_matches[0]
                        month = month.zfill(2)  # Adicionar zero à esquerda se necessário
                        data_encontrada = f"{month}/{year}"
                
                # Criar registros para cada valor encontrado
                for euro_value in euro_values:
                    try:
                        valor_limpo = float(euro_value.replace(',', '.'))
                        
                        record = {
                            'Data': data_encontrada or 'Data não identificada',
                            'Valor_Euros': valor_limpo,
                            'Texto_Original': original_text[:150] + '...' if len(original_text) > 150 else original_text,
                            'Fonte': 'tooltip' if "tooltip_data" in raw_data and original_text in [item['text'] for item in raw_data['tooltip_data']] else 'texto'
                        }
                        cabaz_records.append(record)
                        print(f"✓ Encontrado: {data_encontrada or 'S/Data'} -> {valor_limpo}€ ({record['Fonte']})")
                        
                    except ValueError:
                        continue
        
        # Remover duplicatas (mesmo valor e data)
        seen = set()
        unique_records = []
        for record in cabaz_records:
            key = (record['Data'], record['Valor_Euros'])
            if key not in seen:
                seen.add(key)
                unique_records.append(record)
        
        # Ordenar cronologicamente
        def sort_key(record):
            data = record['Data']
            if data == 'Data não identificada':
                return '0000/00'
            try:
                if '/' in data:
                    parts = data.split('/')
                    if len(parts) == 2:
                        return f"{parts[1]}/{parts[0].zfill(2)}"  # YYYY/MM
                return data
            except:
                return data
        
        unique_records.sort(key=sort_key)
        
        print(f"📊 Total de registros únicos do cabaz: {len(unique_records)}")
        if len(unique_records) != len(cabaz_records):
            print(f"   (Removidas {len(cabaz_records) - len(unique_records)} duplicatas)")
        
        return unique_records

    def extract_text_from_json(self, json_data):
        """Extrai textos de estruturas JSON complexas"""
        texts = []
        
        def extract_recursive(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
            elif isinstance(obj, str):
                if '€' in obj or re.search(r'\d+[.,]\d+', obj):
                    texts.append(obj)
        
        try:
            extract_recursive(json_data)
        except:
            pass
        
        return textsif data == 'Data não identificada':
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