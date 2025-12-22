from datetime import date
import logging
import time
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Pagina_Tasas:
    def __init__(self):
        self.base_url = "https://www.sbs.gob.pe/app/pp/EstadisticasSAEEPortal/Paginas/TIActivaTipoCreditoEmpresa.aspx?tip=B"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'

    async def solicitar(self, fecha: date = None) -> str:
        try:
            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(user_agent=self.user_agent)
                page = await ctx.new_page()

                await page.goto(self.base_url, timeout=10000)

                await page.wait_for_load_state('networkidle')

                if fecha:
                    await page.evaluate(f"""
                    var date_input = $find('ctl00_cphContent_rdpDate');
                    date_input.set_selectedDate(new Date({fecha.year}, {fecha.month - 1}, {fecha.day}));
                    """)

                await page.click('#ctl00_cphContent_btnConsultar')
                
                await page.wait_for_timeout(5000)
                
                html_content = await page.content()
                
                await ctx.close()
                await browser.close()
            
            return html_content
        except Exception as e:
            logger.error(f"Error en solicitud a SBS con Playwright")