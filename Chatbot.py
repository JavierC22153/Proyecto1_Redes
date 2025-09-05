import json
import os
from datetime import datetime
from typing import List, Dict
import anthropic
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class MCPChatbot:
    def __init__(self):
        # 1. Conexión con LLM (Anthropic Claude)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada en el archivo .env")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-sonnet-20240229"
        
        # 2. Contexto de la conversación
        self.conversation_history = []
        
        # 3. Logging de interacciones
        self.log_file = "mcp_interactions.log"
        self.setup_logging()
    
    def setup_logging(self):
        # Crear archivo de log si no existe
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== MCP Chatbot Log - Iniciado: {datetime.now().isoformat()} ===\n")
    
    def log_interaction(self, interaction_type: str, content: str, response: str = None):
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "type": interaction_type,
            "user_input": content,
            "llm_response": response,
            "context_length": len(self.conversation_history)
        }
        
        # Escribir al archivo de log
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{json.dumps(log_entry, indent=2, ensure_ascii=False)}\n")
        
        print(f"📝 [LOG] {interaction_type} registrado - {timestamp}")
    
    def add_to_context(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Limitar contexto a últimos 20 mensajes para evitar exceso de tokens
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def send_message(self, user_input: str) -> str:
        try:
            # Agregar mensaje del usuario al contexto
            self.add_to_context("user", user_input)
            
            # Log de la solicitud
            self.log_interaction("REQUEST", user_input)
            
            # Enviar a Claude con todo el contexto
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=self.conversation_history
            )
            
            assistant_response = response.content[0].text
            
            # Agregar respuesta del asistente al contexto
            self.add_to_context("assistant", assistant_response)
            
            # Log de la respuesta
            self.log_interaction("RESPONSE", user_input, assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Error al comunicarse con Claude: {str(e)}"
            self.log_interaction("ERROR", user_input, error_msg)
            return error_msg
    
    def show_conversation_stats(self):
        print(f"\n Estadísticas de la sesión:")
        print(f"   • Mensajes en contexto: {len(self.conversation_history)}")
        print(f"   • Archivo de log: {self.log_file}")
        
        # Contar interacciones del log
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                interactions = content.count('"type":')
            print(f"   • Total interacciones registradas: {interactions}")
        except:
            print(f"   • No se pudo leer el archivo de log")
    
    def show_recent_logs(self, limit: int = 5):
        print(f"\n Últimas {limit} interacciones:")
        print("-" * 50)
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Buscar las últimas entradas JSON
            log_entries = []
            current_entry = ""
            
            for line in lines:
                if line.strip().startswith('{"timestamp"'):
                    if current_entry:
                        try:
                            entry = json.loads(current_entry)
                            log_entries.append(entry)
                        except:
                            pass
                    current_entry = line.strip()
                elif current_entry and (line.strip().startswith('}') or '"' in line):
                    current_entry += line.strip()
                    if line.strip().endswith('}'):
                        try:
                            entry = json.loads(current_entry)
                            log_entries.append(entry)
                            current_entry = ""
                        except:
                            current_entry = ""
            
            # Mostrar las últimas entradas
            for entry in log_entries[-limit:]:
                timestamp = entry.get('timestamp', 'N/A')
                interaction_type = entry.get('type', 'N/A')
                user_input = entry.get('user_input', 'N/A')[:50] + "..."
                
                print(f"[{timestamp}] {interaction_type}")
                print(f"   Input: {user_input}")
                if entry.get('llm_response'):
                    response_preview = entry['llm_response'][:100] + "..."
                    print(f"   Response: {response_preview}")
                print()
        
        except Exception as e:
            print(f"Error al leer logs: {e}")
    
    def run(self):
        print(" MCP Chatbot")
        print("=" * 55)
        print("Conectado a Claude (Anthropic)")
        print("Funcionalidades activas:")
        print("1. Conexión con LLM")
        print("2. Mantenimiento de contexto")
        print("3. Logging de interacciones")
        print("\nComandos especiales:")
        print("  /stats  - Ver estadísticas")
        print("  /logs   - Ver logs recientes")
        print("  /quit   - Salir")
        print("=" * 55)
        
        while True:
            try:
                user_input = input("\n Tú: ").strip()
                
                if not user_input:
                    continue
                
                # Comandos especiales
                if user_input.lower() == '/quit':
                    print("\n ¡Hasta luego!")
                    break
                elif user_input.lower() == '/stats':
                    self.show_conversation_stats()
                    continue
                elif user_input.lower() == '/logs':
                    self.show_recent_logs()
                    continue
                
                # Enviar mensaje a Claude
                print("\n🤖 Claude: ", end="")
                response = self.send_message(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n Error: {e}")


if __name__ == "__main__":
    try:
        chatbot = MCPChatbot()
        chatbot.run()
    except ValueError as e:
        print(f" Error de configuración: {e}")
        print("\n Asegúrate de:")
        print("1. Tener un archivo .env con ANTHROPIC_API_KEY=tu-api-key")
        print("2. Instalar las dependencias: pip install anthropic python-dotenv")
    except Exception as e:
        print(f" Error inesperado: {e}")