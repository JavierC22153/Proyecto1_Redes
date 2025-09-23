import json
import os
import sys
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any
import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Cargar variables de entorno
load_dotenv()


class MCPChatbot:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada en el archivo .env")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"
        
        self.conversation_history = []
        self.log_file = "mcp_interactions.log"
        self.setup_logging()
        
        self.mcp_sessions = {}
        self.available_tools = {}
        
        # URL de tu MCP remoto
        self.remote_mcp_url = "https://mcp-password-generator-57963600269.us-central1.run.app"

    def setup_logging(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== MCP Chatbot Log - Iniciado: {datetime.now().isoformat()} ===\n")

    def log_interaction(self, interaction_type: str, content: str, response: Any = None):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": interaction_type,
            "content": content,
            "response": str(response) if response else None,
            "available_servers": list(self.mcp_sessions.keys()),
            "tools_count": len(self.available_tools)
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")

    #Conectar a MCP remoto
    def test_remote_mcp_connection(self):
        """Verificar conexión al MCP remoto"""
        try:
            response = requests.get(self.remote_mcp_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f" MCP Remoto conectado: {data.get('message', 'OK')}")
                print(f" Funcionalidad: {data.get('funcionalidad', 'N/A')}")
                return True
            else:
                print(f" MCP remoto responde con código: {response.status_code}")
                return False
        except Exception as e:
            print(f" Error conectando MCP remoto: {e}")
            return False

    # NUEVA FUNCIÓN: Usar MCP remoto
    def call_remote_mcp(self, endpoint: str, method: str = "GET", data: Dict = None):
        """Llamar al MCP remoto"""
        try:
            url = f"{self.remote_mcp_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json=data or {}, headers=headers, timeout=10)
            else:
                return {"error": "Método no soportado"}
            
            if response.status_code == 200:
                result = response.json()
                self.log_interaction("REMOTE_MCP_CALL", f"{method} {endpoint}", result)
                return result
            else:
                return {"error": f"Error HTTP {response.status_code}", "details": response.text}
                
        except Exception as e:
            error_msg = f"Error llamando MCP remoto: {e}"
            self.log_interaction("REMOTE_MCP_ERROR", f"{method} {endpoint}", error_msg)
            return {"error": error_msg}

    async def connect_to_server(self, server_name: str, server_params: StdioServerParameters):
        try:
            async with asyncio.timeout(15):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        
                        self.mcp_sessions[server_name] = {
                            'params': server_params,
                            'tools': result.tools
                        }
                        
                        for tool in result.tools:
                            tool_key = f"{server_name}_{tool.name}"
                            self.available_tools[tool_key] = {
                                "server": server_name,
                                "tool": tool
                            }
                        
                        self.log_interaction("MCP_INIT", server_name, {"status": "success", "tools": len(result.tools)})
                        return True
                        
        except Exception as e:
            self.log_interaction("MCP_ERROR", server_name, {"error": str(e)})
            print(f"Advertencia: No se pudo conectar al servidor {server_name}: {e}")
            return False

    async def initialize_mcp_servers(self):
        print("Inicializando servidores MCP...")
        print(" Verificando MCP remoto...")
        self.test_remote_mcp_connection()
        
        # Servidor filesystem
        try:
            filesystem_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
            )
            await self.connect_to_server("filesystem", filesystem_params)
            print(" Servidor filesystem conectado")
        except Exception as e:
            print(f" Servidor filesystem no disponible: {e}")
        
        # Servidor git
        try:
            git_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_server_git", "--repository", os.getcwd()]
            )
            await self.connect_to_server("git", git_params)
            print(" Servidor git conectado")
        except Exception as e:
            print(f" Servidor git no disponible: {e}")
        
        # Servidor F1 personalizado
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            f1_server_path = os.path.join(current_dir, "f1_mcp_server.py")
            print(f"🔍 Buscando servidor F1 en: {f1_server_path}")
            
            if os.path.exists(f1_server_path):
                f1_params = StdioServerParameters(
                    command=sys.executable,
                    args=[f1_server_path]
                )
                success = await self.connect_to_server("f1_analyzer", f1_params)
                if success:
                    print(" Servidor F1 Strategy Analyzer conectado")
                else:
                    print(" Error conectando servidor F1")
            else:
                print(f" Archivo f1_mcp_server.py no encontrado en: {f1_server_path}")
        except Exception as e:
            print(f" Servidor F1 no disponible: {e}")
        
        # Servidor League of Legends personalizado
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            lol_server_path = os.path.join(current_dir, "lol_mcp_server.py")
            print(f"🔍 Buscando servidor LoL en: {lol_server_path}")
            
            if os.path.exists(lol_server_path):
                lol_params = StdioServerParameters(
                    command=sys.executable,
                    args=[lol_server_path]
                )
                success = await self.connect_to_server("lol_advisor", lol_params)
                if success:
                    print(" Servidor LoL Build Advisor conectado")
                else:
                    print(" Error conectando servidor LoL")
            else:
                print(f" Archivo lol_mcp_server.py no encontrado en: {lol_server_path}")
                print(" Asegúrate de crear el archivo lol_mcp_server.py y la carpeta lol_modules/")
        except Exception as e:
            print(f" Servidor LoL no disponible: {e}")
            import traceback
            print(f" Traceback: {traceback.format_exc()}")
        
        # Servidor Movie Advisor personalizado
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            movie_server_path = os.path.join(current_dir, "movie_mcp_server.py")
            print(f"🔍 Buscando servidor Movies en: {movie_server_path}")
            
            if os.path.exists(movie_server_path):
                movie_params = StdioServerParameters(
                    command=sys.executable,
                    args=[movie_server_path]
                )
                success = await self.connect_to_server("movie_advisor", movie_params)
                if success:
                    print(" Servidor Movie Advisor conectado")
                else:
                    print(" Error conectando servidor Movies")
            else:
                print(f" Archivo movie_mcp_server.py no encontrado en: {movie_server_path}")
        except Exception as e:
            print(f" Servidor Movies no disponible: {e}")
            print(" Asegúrate de tener TMDB_API_KEY en tu archivo .env")
        
        print(f"Total de herramientas disponibles: {len(self.available_tools)}")
        print(f"🌐 MCP remoto disponible en: {self.remote_mcp_url}\n")

    async def execute_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        try:
            if server_name not in self.mcp_sessions:
                return f"Servidor {server_name} no disponible"
            
            server_params = self.mcp_sessions[server_name]['params']
            
            async with asyncio.timeout(30):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        
                        self.log_interaction("MCP_TOOL_EXECUTION", 
                                           f"{server_name}.{tool_name}({arguments})", 
                                           str(result))
                        
                        response_text = ""
                        for content in result.content:
                            if hasattr(content, 'text'):
                                response_text += content.text + "\n"
                        
                        return response_text.strip() if response_text else "Herramienta ejecutada correctamente"
                        
        except Exception as e:
            error_msg = f"Error ejecutando {server_name}.{tool_name}: {e}"
            self.log_interaction("MCP_TOOL_ERROR", f"{server_name}.{tool_name}", error_msg)
            return error_msg

    def add_to_context(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 20:  # Mantener solo los últimos 20 mensajes
            self.conversation_history = self.conversation_history[-20:]

    def get_available_tools_info(self) -> str:
        if not self.available_tools:
            return "No hay herramientas MCP disponibles."
        
        info = "Herramientas MCP disponibles:\n\n"
        
        # Agrupar por servidor
        servers = {}
        for tool_key, tool_info in self.available_tools.items():
            server = tool_info['server']
            if server not in servers:
                servers[server] = []
            servers[server].append(tool_info['tool'])
        
        for server_name, tools in servers.items():
            # Iconos por servidor
            icon = {
                'filesystem': '📁',
                'git': '🔧',
                'f1_analyzer': '🏎️',
                'lol_advisor': '🎮',
                'movie_advisor': '🎬'
            }.get(server_name, '⚙️')
            
            info += f"{icon} {server_name.upper()}:\n"
            for tool in tools:
                info += f"  • {tool.name}: {tool.description}\n"
            info += "\n"
        
        return info

    def create_system_prompt(self) -> str:
        base_prompt = """Eres un asistente AI especializado con acceso a herramientas MCP avanzadas y un servidor MCP remoto.

NUEVA FUNCIONALIDAD - MCP REMOTO:
🎲 GENERADOR DE NÚMEROS ALEATORIOS (100% REMOTO):
- Generar números aleatorios simples
- Personalizar rangos de números
- Funciona completamente en Google Cloud Run
- URL: https://mcp-password-generator-57963600269.us-central1.run.app

Para usar el MCP remoto, puedes:
- Generar número aleatorio: "Dame un número aleatorio"
- Rango personalizado: "Genera un número entre 50 y 200"
- Verificar estado: "¿Está funcionando el MCP remoto?"

OTRAS CAPACIDADES EXISTENTES:

🏎️ ANÁLISIS DE FÓRMULA 1: Estrategias de carrera, análisis de neumáticos, timing de pit stops
🎮 LEAGUE OF LEGENDS: Builds de campeones, runas, items, análisis de composiciones
🎬 PELÍCULAS Y ENTRETENIMIENTO: Búsqueda de películas, recomendaciones, tendencias
📁 MANIPULACIÓN DE ARCHIVOS: Leer, escribir, buscar archivos y directorios
🔧 OPERACIONES DE GIT: Commits, branches, historial, estado del repositorio

CAPACIDADES ESPECIALES:

F1 Analysis:
- Analizar estrategias de neumáticos de cualquier piloto
- Comparar timing de pit stops entre pilotos
- Encontrar ventanas óptimas para paradas estratégicas
- Obtener información de sesiones y pilotos

League of Legends:
- Configurar matchups usando texto libre (ej: "Quiero jugar Darius tank contra Garen, Maokai, Ahri, Jinx, Lulu")
- Analizar composiciones enemigas (damage mix, CC, healing)
- Sugerir runas optimizadas según el matchup
- Recomendar builds de items y hechizos de invocador

Movies & Entertainment:
- Buscar información detallada de películas por título
- Obtener recomendaciones basadas en géneros y ratings
- Descubrir películas aleatorias populares
- Ver tendencias semanales de películas
- Información de plataformas de streaming disponibles

MCP Remoto - Números Aleatorios:
- Generación simple: números entre 1-100
- Rangos personalizados: especifica min y max
- Completamente remoto en Google Cloud Run
- Respuesta con timestamp y información del servidor

Responde de manera directa, técnica cuando sea necesario, y siempre explica qué herramientas estás usando y por qué."""
        
        if self.available_tools:
            tools_info = "\n\nHERRAMIENTAS DISPONIBLES:\n"
            
            # Mostrar herramientas agrupadas por servidor
            servers = {}
            for tool_key, tool_info in self.available_tools.items():
                server = tool_info['server']
                if server not in servers:
                    servers[server] = []
                servers[server].append(tool_info['tool'])
            
            for server_name, tools in servers.items():
                icon = {
                    'filesystem': '📁',
                    'git': '🔧', 
                    'f1_analyzer': '🏎️',
                    'lol_advisor': '🎮',
                    'movie_advisor': '🎬'
                }.get(server_name, '⚙️')
                
                tools_info += f"\n{icon} {server_name.upper()}:\n"
                for tool in tools:
                    tools_info += f"  - {tool.name}: {tool.description}\n"
            
            # Agregar info del MCP remoto
            tools_info += f"\n MCP REMOTO (GOOGLE CLOUD RUN):\n"
            tools_info += f"  - /random: Genera número aleatorio (1-100)\n"
            tools_info += f"  - /random (POST): Genera número con rango personalizado\n"
            tools_info += f"  - /: Información del servidor remoto\n"
            
            base_prompt += tools_info
            
        return base_prompt

    async def handle_tool_calls(self, response):
        assistant_response = ""
        
        for content in response.content:
            if content.type == "text":
                assistant_response += content.text
            elif content.type == "tool_use":
                tool_name = content.name
                arguments = content.input
                
                # Buscar servidor de la herramienta
                server_name = None
                for tool_key, tool_info in self.available_tools.items():
                    if tool_info['tool'].name == tool_name:
                        server_name = tool_info['server']
                        break
                
                if server_name:
                    # Iconos para diferentes tipos de herramientas
                    icon = {
                        'f1_analyzer': '🏎️',
                        'lol_advisor': '🎮',
                        'movie_advisor': '🎬',
                        'filesystem': '📁',
                        'git': '🔧'
                    }.get(server_name, '⚙️')
                    
                    print(f"\n{icon} Ejecutando {tool_name} en servidor {server_name}...")
                    result = await self.execute_mcp_tool(server_name, tool_name, arguments)
                    assistant_response += f"\n\n{result}\n"
                else:
                    assistant_response += f"\n Herramienta {tool_name} no encontrada.\n"
                    
        return assistant_response

    async def process_query(self, user_input: str) -> str:
        try:
            self.add_to_context("user", user_input)
            self.log_interaction("USER_QUERY", user_input)
            
            user_lower = user_input.lower()
            
            # Detectar requests para el MCP remoto
            if any(keyword in user_lower for keyword in [
                "número aleatorio", "numero aleatorio", "random", 
                "mcp remoto", "servidor remoto", "google cloud"
            ]):
                print("\n Detectando solicitud para MCP remoto...")
                
                # Determinar qué endpoint usar
                if "entre" in user_lower or "rango" in user_lower:
                    # Extraer números si es posible (lógica simple)
                    import re
                    numbers = re.findall(r'\d+', user_input)
                    if len(numbers) >= 2:
                        min_num = int(numbers[0])
                        max_num = int(numbers[1])
                        result = self.call_remote_mcp("/random", "POST", {"min": min_num, "max": max_num})
                    else:
                        result = self.call_remote_mcp("/random", "POST", {"min": 1, "max": 100})
                else:
                    result = self.call_remote_mcp("/random", "GET")
                
                if "error" not in result:
                    response_text = f" **Número aleatorio generado por MCP remoto:**\n"
                    response_text += f"**Número:** {result.get('numero', 'N/A')}\n"
                    response_text += f"**Servidor:** {result.get('servidor', 'Google Cloud Run')}\n"
                    response_text += f"**Timestamp:** {result.get('timestamp', 'N/A')}\n"
                    
                    if "rango" in result:
                        rango = result["rango"]
                        response_text += f"**Rango:** {rango['min']} - {rango['max']}\n"
                    
                    response_text += "\n **Tu MCP está funcionando 100% remoto en Google Cloud Run!**"
                    
                    self.add_to_context("assistant", response_text)
                    return response_text
                else:
                    error_response = f" Error en MCP remoto: {result.get('error', 'Desconocido')}"
                    self.add_to_context("assistant", error_response)
                    return error_response
            
            # Verificar estado del MCP remoto
            if any(keyword in user_lower for keyword in [
                "estado mcp", "funciona mcp", "mcp remoto", "servidor remoto"
            ]):
                print("\n🌐 Verificando estado del MCP remoto...")
                result = self.call_remote_mcp("/", "GET")
                
                if "error" not in result:
                    status_text = f"✅ **Estado del MCP Remoto:**\n"
                    status_text += f"**Mensaje:** {result.get('message', 'N/A')}\n"
                    status_text += f"**Estado:** {result.get('status', 'N/A')}\n"
                    status_text += f"**Autor:** {result.get('author', 'N/A')}\n"
                    status_text += f"**Funcionalidad:** {result.get('funcionalidad', 'N/A')}\n"
                    status_text += f"**URL:** {self.remote_mcp_url}\n"
                    
                    endpoints = result.get('endpoints', {})
                    if endpoints:
                        status_text += "\n**Endpoints disponibles:**\n"
                        for endpoint, description in endpoints.items():
                            status_text += f"  • {endpoint}: {description}\n"
                    
                    self.add_to_context("assistant", status_text)
                    return status_text
                else:
                    error_response = f" MCP remoto no responde: {result.get('error', 'Desconocido')}"
                    self.add_to_context("assistant", error_response)
                    return error_response
            
            # Preparar herramientas para Claude
            tools = []
            for tool_info in self.available_tools.values():
                tool = tool_info['tool']
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                })

            # Llamar a Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.create_system_prompt(),
                messages=self.conversation_history,
                tools=tools if tools else None
            )

            # Procesar respuesta
            assistant_response = await self.handle_tool_calls(response)
            
            self.add_to_context("assistant", assistant_response)
            self.log_interaction("ASSISTANT_RESPONSE", user_input, assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Error procesando consulta: {str(e)}"
            self.log_interaction("PROCESSING_ERROR", user_input, error_msg)
            return error_msg

    def show_recent_logs(self, limit: int = 5):
        print(f"\nÚltimas {limit} interacciones:")
        print("-" * 80)
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Obtener las últimas entradas
            recent_entries = []
            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith('==='):
                    try:
                        entry = json.loads(line)
                        recent_entries.append(entry)
                        if len(recent_entries) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Mostrar en orden cronológico
            for entry in reversed(recent_entries):
                timestamp = entry.get('timestamp', 'N/A')
                entry_type = entry.get('type', 'N/A')
                content = entry.get('content', 'N/A')
                print(f"[{timestamp}] {entry_type}: {content[:100]}...")
                
        except Exception as e:
            print(f"Error al leer logs: {e}")

    def show_f1_examples(self):
        examples = """
🏎️ EJEMPLOS DE ANÁLISIS DE FÓRMULA 1:

1. Pregunta sobre los pilotos que participaron:
   "¿Qué pilotos corrieron en la carrera de Singapur?"

2. Sesiones disponibles:
   "Muestra las sesiones de Spa en 2023"

3. Búsqueda por año:
   "¿Qué sesiones hubo en 2024?"

4. Preguntas Descriptivas:
   "Lista completa de pilotos y equipos"

5. Comparaciones:
   "Analiza la estrategia de Hamilton en la sesión 9158, luego la de Verstappen en la misma sesión"

📋 NOTAS:
   - Usa session_key (números como 9158, 9159, etc.) También puedes especificar Año y Nombre de la Sesión
   - Los números de piloto son estándar (ej: 1=Verstappen, 44=Hamilton, 16=Leclerc)
   - Puedes combinar múltiples análisis en una sola consulta
"""
        print(examples)

    def show_lol_examples(self):
        examples = """
 EJEMPLOS DE LEAGUE OF LEGENDS:

1. Configurar matchup con texto libre:
   "Quiero jugar Darius tank contra Garen, Maokai, Ahri, Jinx, Lulu"

2. Análisis paso a paso:
   - Primero: "Configura un matchup con Yasuo AD contra Malphite, Graves, LeBlanc, Kai'Sa, Thresh"
   - Luego: "Analiza la composición enemiga"
   - Después: "Sugiere runas para este matchup"

3. Builds completos:
   "Dame el build completo de Jinx ADC contra un equipo tanque"

4. Consultas específicas:
   "¿Qué runas usar con Azir AP contra mucho CC?"
   "Items para Garen tank vs equipo full AD"
"""
        print(examples)

    def show_movies_examples(self):
        examples = """
EJEMPLOS DE BÚSQUEDA DE PELÍCULAS:

1. Búsqueda específica:
   "Información de Avengers Endgame"

2. Recomendaciones personalizadas:
   "Recomiéndame películas de acción con rating mayor a 8"

3. Descubrimiento:
   "Dame una película aleatoria"

4. Tendencias:
   "¿Qué películas están en tendencia esta semana?"

 GÉNEROS DISPONIBLES:
   - Acción, Aventura, Animación, Comedia
   - Crimen, Documental, Drama, Familia
   - Fantasía, Historia, Horror, Música
   - Misterio, Romance, Ciencia Ficción
   - Terror, Thriller, Guerra, Western

 INFORMACIÓN QUE OBTIENES:
   - Sinopsis completa y detalles técnicos
   - Ratings y año de lanzamiento
   - Géneros y duración
   - Plataformas de streaming disponibles
   - Películas similares recomendadas
   - Presupuesto y recaudación (cuando disponible)
"""
        print(examples)

    def show_remote_mcp_examples(self):
        examples = f"""
    EJEMPLOS DEL MCP REMOTO (GOOGLE CLOUD RUN):

URL: {self.remote_mcp_url}

1. Generar número aleatorio simple:
   "Dame un número aleatorio"

2. Número con rango personalizado:
   "Dame un número aleatorio entre 100 y 500"
"""
        print(examples)

    async def run_chat(self):
        print("=" * 80)
        
        # Inicializar servidores MCP
        await self.initialize_mcp_servers()
        
        print("🤖 Inicia la conversación escribiendo tu mensaje.")
        print("\n🔧 Comandos especiales disponibles:")
        print("  /logs     - Ver logs recientes")
        print("  /f1       - Ver ejemplos de análisis F1")
        print("  /lol      - Ver ejemplos de League of Legends")
        print("  /movies   - Ver ejemplos de búsqueda de películas")
        print("  /remote   - Ver ejemplos del MCP remoto ")
        print("  /quit     - Salir del chatbot")
        print("=" * 80)

        while True:
            try:
                user_input = input("\n🔵 Tú: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == '/quit':
                    print("👋 ¡Hasta luego!")
                    break
                elif user_input.lower() == '/logs':
                    self.show_recent_logs()
                    continue
                elif user_input.lower() == '/f1':
                    self.show_f1_examples()
                    continue
                elif user_input.lower() == '/lol':
                    self.show_lol_examples()
                    continue
                elif user_input.lower() == '/movies':
                    self.show_movies_examples()
                    continue
                elif user_input.lower() == '/remote':
                    self.show_remote_mcp_examples()
                    continue
                
                print("\n🤖 Claude: ", end="", flush=True)
                response = await self.process_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n Error: {e}")

    def run(self):
        """Método principal"""
        asyncio.run(self.run_chat())


if __name__ == "__main__":
    try:
        chatbot = MCPChatbot()
        chatbot.run()
    except ValueError as e:
        print(f"Error de configuración: {e}")
        print("\n Asegúrate de tener un archivo .env con ANTHROPIC_API_KEY=tu-api-key")
    except Exception as e:
        print(f"Error inesperado: {e}")