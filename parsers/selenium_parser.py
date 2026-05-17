from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import random
import re

class SeleniumParser:
    """Парсер для сайтов с JavaScript (Avito, HH.ru)"""
    
    def __init__(self):
        self.driver = None
        self.results = []
    
    def setup_driver(self):
        """Настраивает Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
    
    def safe_sleep(self, min_sec=3, max_sec=7):
        """Случайная пауза"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def extract_phone(self, text: str) -> str:
        """Извлекает телефон из текста"""
        pattern = r'(\+7[\s\-\(\)]?\(?\d{3}\)?[\s\-\(\)]?\d{3}[\s\-\(\)]?\d{2}[\s\-\(\)]?\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else ""
    
    def is_hot_lead(self, text: str) -> bool:
        """Проверка на горячий лид"""
        hot_keywords = [
            'китай', 'импорт', 'доставка из китая', 'груз из китая',
            '1688', 'alibaba', 'вэд', 'логист', 'перевозка', 'карго',
            'поставки', 'таможня', 'растаможка'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in hot_keywords)
    
    def parse_avito(self, search_url: str) -> list:
        """Парсит Avito по поисковому запросу"""
        print(f"🔍 Парсим Avito: {search_url}")
        leads = []
        
        try:
            self.setup_driver()
            self.driver.get(search_url)
            
            # Ждём загрузки объявлений
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-marker='item']"))
            )
            
            # Находим все объявления
            listings = self.driver.find_elements(By.CSS_SELECTOR, "[data-marker='item']")
            
            for listing in listings[:20]:
                try:
                    title_elem = listing.find_element(By.CSS_SELECTOR, "[data-marker='item-title']")
                    title = title_elem.text.strip()
                    
                    # Цена
                    try:
                        price_elem = listing.find_element(By.CSS_SELECTOR, "[data-marker='item-price']")
                        price = price_elem.text.strip()
                    except:
                        price = ""
                    
                    # Телефон (может быть скрыт)
                    try:
                        phone_elem = listing.find_element(By.CSS_SELECTOR, "[data-marker='item-phone']")
                        phone = phone_elem.text.strip()
                    except:
                        phone = ""
                    
                    # Ссылка
                    try:
                        link_elem = listing.find_element(By.CSS_SELECTOR, "a[data-marker='item-title']")
                        link = link_elem.get_attribute('href')
                    except:
                        link = ""
                    
                    if len(title) > 10 and self.is_hot_lead(title):
                        lead = {
                            'company': title[:150],
                            'contact': '',
                            'phone': self.extract_phone(phone) or self.extract_phone(title),
                            'city': '',
                            'cargo_type': 'любые',
                            'volume': price,
                            'source': f'avito:{link[:100]}',
                            'reason': f'Объявление: {title[:80]}',
                            'hot_level': 'hot' if self.is_hot_lead(title) else 'warm',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ Avito: {title[:50]}...")
                    
                    self.safe_sleep(1, 3)
                    
                except Exception as e:
                    print(f"⚠️ Ошибка объявления: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Ошибка Avito: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return leads
    
    def parse_hh_ru(self, search_url: str) -> list:
        """Парсит HH.ru (обновлённые селекторы 2024)"""
        print(f"🔍 Парсим HH.ru: {search_url}")
        leads = []
        
        try:
            self.setup_driver()
            self.driver.get(search_url)
            
            # Принимаем куки если есть баннер
            try:
                cookie_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-qa='hh-cookie-banner__accept']"))
                )
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            # Ждём загрузки вакансий
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-qa='vacancy-serp__vacancy'], article[data-qa='vacancy-card']"))
            )
            
            # Пробуем разные селекторы для вакансий
            vacancies = []
            for selector in [
                "div[data-qa='vacancy-serp__vacancy']",
                "article[data-qa='vacancy-card']",
                "div.vacancy-serp-item",
                "div[data-qa='magadela-vacancy']"
            ]:
                vacancies = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if vacancies:
                    break
            
            if not vacancies:
                print("⚠️ Не найдено вакансий — возможно, нужна авторизация или капча")
                return []
            
            for vacancy in vacancies[:20]:
                try:
                    # Заголовок вакансии
                    title = ""
                    link = ""
                    for sel in [
                        "a[data-qa='vacancy-serp__vacancy-title']",
                        "a.bloko-link",
                        "a.vacancy-title",
                        "h2 a",
                        ".vacancy-name"
                    ]:
                        try:
                            elem = vacancy.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip()
                            link = elem.get_attribute('href')
                            break
                        except:
                            continue
                    
                    if not title:
                        continue
                    
                    # Компания
                    company = ""
                    for sel in [
                        "[data-qa='vacancy-serp__vacancy-employer']",
                        ".vacancy-company-name",
                        ".bloko-text",
                        "span[data-qa='company-name']"
                    ]:
                        try:
                            elem = vacancy.find_element(By.CSS_SELECTOR, sel)
                            company = elem.text.strip()
                            break
                        except:
                            continue
                    
                    # Зарплата
                    salary = ""
                    try:
                        salary_elem = vacancy.find_element(By.CSS_SELECTOR, "[data-qa='vacancy-serp__vacancy-salary'], .vacancy-salary")
                        salary = salary_elem.text.strip()
                    except:
                        pass
                    
                    # Фильтруем по ключевым словам
                    full_text = (company + " " + title).lower()
                    if any(kw in full_text for kw in ['логист', 'вэд', 'импорт', 'китай', 'доставка', 'карго']):
                        lead = {
                            'company': company[:150] if company else title[:150],
                            'contact': '',
                            'phone': '',
                            'city': '',
                            'cargo_type': 'любые',
                            'volume': salary,
                            'source': f'hh.ru:{link[:100] if link else ""}',
                            'reason': f'Вакансия: {title[:80]}',
                            'hot_level': 'warm',
                            'created_at': datetime.now().isoformat()
                        }
                        leads.append(lead)
                        print(f"✅ HH.ru: {company or title}")
                    
                    self.safe_sleep(1, 2)
                    
                except Exception as e:
                    print(f"⚠️ Ошибка вакансии: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Ошибка HH.ru: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return leads
    
    def close(self):
        """Закрывает браузер"""
        if self.driver:
            self.driver.quit()
