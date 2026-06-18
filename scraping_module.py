import asyncio
from playwright.async_api import async_playwright

async def buscar_precios(nombre_producto):
    resultados = []
    
    async with async_playwright() as p:
        # Lanzamos el navegador (headless=True para que sea rápido y no se vea)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # --- BUSQUEDA EN AMAZON ---
            print(f"🔎 Buscando '{nombre_producto}' en Amazon...")
            # Formateamos el nombre para la URL de búsqueda de Amazon
            query = nombre_producto.replace(" ", "+")
            url_amazon = f"https://www.amazon.com/s?k={query}"
            
            await page.goto(url_amazon, wait_until="domcontentloaded")
            
            # Buscamos el primer bloque de precio disponible
            # Estos selectores pueden cambiar, son la parte "frágil" del scraping
            await page.wait_for_selector(".a-price-whole", timeout=5000)
            
            precio_entero = await page.inner_text(".a-price-whole")
            precio_decimal = await page.inner_text(".a-price-fraction")
            precio_final = float(f"{precio_entero.replace(',', '')}.{precio_decimal}")

            resultados.append({
                "tienda": "Amazon",
                "precio": precio_final,
                "url": url_amazon
            })

        except Exception as e:
            print(f"⚠️ No se pudo obtener precio de Amazon: {e}")

        await browser.close()
    
    return resultados