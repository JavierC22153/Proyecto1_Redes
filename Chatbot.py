import json
import os
import sys
import asyncio
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

    def setup_logging(self):
        """Configurar el archivo de log"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== MCP Chatbot Log - Iniciado: {datetime.now().isoformat()} ===\n")

    def log_interaction(self, interaction_type: str, content: str, response: Any = None):
        """Registrar interacciones en el log"""
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

    async def connect_to_server(self, server_name: str, server_params: StdioServerParameters):
        """Conectar a un servidor MCP"""
        try:
            async with asyncio.timeout(10):
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
            return False

    async def initialize_mcp_servers(self):
        """Inicializar servidores MCP"""
        # Servidor filesystem
        filesystem_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
        )
        await self.connect_to_server("filesystem", filesystem_params)
        
        # Servidor git
        git_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_git", "--repository", os.getcwd()]
        )
        await self.connect_to_server("git", git_params)

    async def execute_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]):
        """Ejecutar una herramienta MCP"""
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
        """Agregar mensaje al contexto de conversación"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 20:  # Mantener solo los últimos 20 mensajes
            self.conversation_history = self.conversation_history[-20:]

    def get_available_tools_info(self) -> str:
        """Obtener información de herramientas disponibles"""
        if not self.available_tools:
            return "No hay herramientas MCP disponibles."
        
        info = "Herramientas MCP disponibles:\n\n"
        for tool_key, tool_info in self.available_tools.items():
            tool = tool_info['tool']
            server = tool_info['server']
            info += f"• {tool.name} ({server}): {tool.description}\n"
        
        return info

    def create_system_prompt(self) -> str:
        """Crear prompt del sistema"""
        base_prompt = """Eres un asistente AI con acceso a herramientas MCP para manipular archivos y repositorios Git.

Puedes ayudar con tareas como:
- Leer y escribir archivos
- Listar directorios
- Operaciones de Git (commits, branches, etc.)
- Buscar archivos y contenido

Responde de manera directa y concisa. Cuando uses herramientas, explica qué estás haciendo."""
        
        if self.available_tools:
            tools_info = "\n\nHerramientas disponibles:\n"
            for tool_key, tool_info in self.available_tools.items():
                tool = tool_info['tool']
                tools_info += f"- {tool.name}: {tool.description}\n"
            base_prompt += tools_info
            
        return base_prompt

    async def handle_tool_calls(self, response):
        """Manejar llamadas a herramientas de Claude"""
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
                    result = await self.execute_mcp_tool(server_name, tool_name, arguments)
                    assistant_response += f"\n\nResultado de {tool_name}:\n{result}\n"
                else:
                    assistant_response += f"\nHerramienta {tool_name} no encontrada.\n"
                    
        return assistant_response

    async def process_query(self, user_input: str) -> str:
        """Procesar consulta del usuario"""
        try:
            self.add_to_context("user", user_input)
            self.log_interaction("USER_QUERY", user_input)
            
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
                max_tokens=1500,
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
        """Mostrar logs recientes"""
        print(f"\nÚltimas {limit} interacciones:")
        print("-" * 60)
        
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
                print(f"[{timestamp}] {entry_type}: {content[:80]}...")
                
        except Exception as e:
            print(f"Error al leer logs: {e}")

    async def run_chat(self):
        """Ejecutar el chat"""
        print("Inicia la conversación escribiendo tu mensaje.")
        print("\nComandos especiales disponibles:")
        print("  /logs     - Ver logs recientes")
        print("  /tools    - Ver herramientas MCP disponibles")
        print("  /quit     - Salir del chatbot")
        print("=" * 60)

        # Inicializar servidores MCP silenciosamente
        await self.initialize_mcp_servers()

        while True:
            try:
                user_input = input("\nTú: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == '/quit':
                    print("¡Hasta luego!")
                    break
                elif user_input.lower() == '/logs':
                    self.show_recent_logs()
                    continue
                elif user_input.lower() == '/tools':
                    print(self.get_available_tools_info())
                    continue
                
                print("\nClaude: ", end="", flush=True)
                response = await self.process_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n¡Hasta luego!")
                break
            except Exception as e:
                print(f"\nError: {e}")

    def run(self):
        """Método principal"""
        asyncio.run(self.run_chat())


if __name__ == "__main__":
    try:
        chatbot = MCPChatbot()
        chatbot.run()
    except ValueError as e:
        print(f"Error de configuración: {e}")
        print("\nAsegúrate de tener un archivo .env con ANTHROPIC_API_KEY=tu-api-key")
    except Exception as e:
        print(f"Error inesperado: {e}")