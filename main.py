import asyncio
import json
from ai_module import identificar_hardware
from scraping_module import buscar_precios

async def ejecutar_comparador(ruta_foto):
    print(f"📸 Procesando imagen: {ruta_foto}...")
    
    # 1. LA IA IDENTIFICA
    res_ia = identificar_hardware(ruta_foto)
    datos = json.loads(res_ia) # Convertimos el texto JSON a diccionario
    
    nombre_identificado = f"{datos.get('marca')} {datos.get('modelo')}"
    print(f"🤖 IA Identificó: {nombre_identificado}")
    
    # 2. EL SCRAPING BUSCA (Usando el nombre de la IA)
    print(f"🔍 Buscando precios para '{nombre_identificado}'...")
    lista_precios = await buscar_precios(nombre_identificado)
    
    # 3. COMPARACIÓN
    print("\n--- COMPARATIVA DE PRECIOS ---")
    # Ordenamos por precio de menor a mayor
    lista_precios.sort(key=lambda x: x['precio'])
    
    for item in lista_precios:
        print(f"💰 {item['tienda']}: ${item['precio']} -> Link: {item['url']}")

if __name__ == "__main__":
    asyncio.run(ejecutar_comparador("prueba.jpg"))