"""
Script para iniciar el servidor API con configuración correcta de event loop
"""

import asyncio
import sys
import platform
import nest_asyncio

if platform.system() == 'Windows' and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

nest_asyncio.apply()

import uvicorn

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        config = uvicorn.Config(
            "api.api_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
    finally:
        loop.close()