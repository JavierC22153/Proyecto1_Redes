import asyncio
import sys
import json
import traceback
import os
import re
from typing import Dict, List, Any
from dataclasses import dataclass

# Importaciones MCP
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
    )
except ImportError as e:
    print(f"Error importing MCP: {e}")
    print("Please install: pip install mcp")
    sys.exit(1)

# Importaciones locales
from lol_modules.client import DDragonClient
from lol_modules.comp_analyzer import analyze_enemy_comp
from lol_modules.build import suggest_runes, suggest_summoners, suggest_items
from lol_modules.groq_parser import parse_intent_text

class LoLAnalyzer:
    def __init__(self):
        self.state = {
            "matchup": {
                "ally_champion": None,
                "ally_characteristic": None,
                "enemy_team": []
            },
            "dd": None,
            "dd_version": None,
            "lang": "en_US"
        }
    
    async def set_matchup(self, text: str = None, ally_champion: str = None, 
                         ally_characteristic: str = None, enemy_team: List[str] = None) -> Dict[str, Any]:
        try:
            if text:
                # Usar parser de texto libre
                data = parse_intent_text(text)
                self.state["matchup"].update(data)
            else:
                # Usar parámetros específicos
                if ally_champion:
                    self.state["matchup"]["ally_champion"] = ally_champion.lower()
                if ally_characteristic:
                    self.state["matchup"]["ally_characteristic"] = ally_characteristic.upper()
                if enemy_team:
                    self.state["matchup"]["enemy_team"] = [e.lower() for e in enemy_team[:5]]
            
            return {
                "success": True,
                "matchup": self.state["matchup"],
                "message": f"Matchup configurado: {self.state['matchup']['ally_champion']} {self.state['matchup']['ally_characteristic']} vs {', '.join(self.state['matchup']['enemy_team'])}"
            }
        except Exception as e:
            return {"success": False, "error": f"Error configurando matchup: {str(e)}"}
    
    async def fetch_static_data(self, ddragon_version: str = "latest", lang: str = "en_US") -> Dict[str, Any]:
        try:
            self.state["lang"] = lang
            dd = DDragonClient(lang=self.state["lang"])
            version = dd.ensure_latest(ddragon_version)
            self.state["dd"] = dd
            self.state["dd_version"] = version
            
            return {
                "success": True,
                "version": version,
                "lang": lang,
                "message": f"Datos estáticos cargados - Versión: {version}"
            }
        except Exception as e:
            return {"success": False, "error": f"Error cargando datos: {str(e)}"}
    
    async def analyze_enemy_composition(self) -> Dict[str, Any]:
        try:
            if not self.state["dd"]:
                return {"success": False, "error": "Primero debes cargar los datos estáticos"}
            
            if not self.state["matchup"]["enemy_team"]:
                return {"success": False, "error": "No hay equipo enemigo configurado"}
            
            analysis = analyze_enemy_comp(self.state["dd"], self.state["matchup"]["enemy_team"])
            
            return {
                "success": True,
                "analysis": analysis,
                "enemy_team": self.state["matchup"]["enemy_team"]
            }
        except Exception as e:
            return {"success": False, "error": f"Error analizando composición: {str(e)}"}
    
    async def get_runes_suggestion(self) -> Dict[str, Any]:
        try:
            if not self._validate_state():
                return {"success": False, "error": "Estado incompleto. Configura matchup y carga datos primero."}
            
            mu = self.state["matchup"]
            comp = analyze_enemy_comp(self.state["dd"], mu["enemy_team"])
            runes = suggest_runes(self.state["dd"], mu["ally_champion"], mu["ally_characteristic"], comp)
            
            return {
                "success": True,
                "runes": runes,
                "champion": mu["ally_champion"],
                "characteristic": mu["ally_characteristic"]
            }
        except Exception as e:
            return {"success": False, "error": f"Error generando runas: {str(e)}"}
    
    async def get_summoners_suggestion(self) -> Dict[str, Any]:
        try:
            if not self._validate_state():
                return {"success": False, "error": "Estado incompleto. Configura matchup y carga datos primero."}
            
            mu = self.state["matchup"]
            comp = analyze_enemy_comp(self.state["dd"], mu["enemy_team"])
            summoners = suggest_summoners(mu["ally_champion"], mu["ally_characteristic"], comp)
            
            return {
                "success": True,
                "summoners": summoners,
                "champion": mu["ally_champion"],
                "characteristic": mu["ally_characteristic"]
            }
        except Exception as e:
            return {"success": False, "error": f"Error generando hechizos: {str(e)}"}
    
    async def get_items_suggestion(self) -> Dict[str, Any]:
        try:
            if not self._validate_state():
                return {"success": False, "error": "Estado incompleto. Configura matchup y carga datos primero."}
            
            mu = self.state["matchup"]
            comp = analyze_enemy_comp(self.state["dd"], mu["enemy_team"])
            items = suggest_items(self.state["dd"], mu["ally_champion"], mu["ally_characteristic"], comp)
            
            return {
                "success": True,
                "items": items,
                "champion": mu["ally_champion"],
                "characteristic": mu["ally_characteristic"]
            }
        except Exception as e:
            return {"success": False, "error": f"Error generando items: {str(e)}"}
    
    def _validate_state(self) -> bool:
        mu = self.state["matchup"]
        return (self.state["dd"] is not None and 
                mu["ally_champion"] is not None and 
                mu["ally_characteristic"] is not None and 
                len(mu["enemy_team"]) > 0)

# Crear servidor MCP
server = Server("lol-build-advisor")
analyzer = LoLAnalyzer()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="lol_set_matchup",
            description="Configura un matchup de League of Legends usando texto libre o parámetros específicos",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texto libre describiendo el matchup (ej: 'Quiero jugar Darius tank contra Garen, Maokai, Ahri, Jinx, Lulu')"
                    },
                    "ally_champion": {
                        "type": "string",
                        "description": "Nombre del campeón aliado"
                    },
                    "ally_characteristic": {
                        "type": "string",
                        "description": "Característica del build: AD, AP, o TANK"
                    },
                    "enemy_team": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de hasta 5 campeones enemigos"
                    }
                }
            }
        ),
        Tool(
            name="lol_fetch_data",
            description="Carga datos estáticos de League of Legends desde DDragon",
            inputSchema={
                "type": "object",
                "properties": {
                    "ddragon_version": {
                        "type": "string",
                        "description": "Versión de DDragon a usar (default: 'latest')"
                    },
                    "lang": {
                        "type": "string",
                        "description": "Idioma de los datos (default: 'en_US')"
                    }
                }
            }
        ),
        Tool(
            name="lol_analyze_enemies",
            description="Analiza la composición del equipo enemigo",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="lol_suggest_runes",
            description="Genera sugerencias de runas basadas en el matchup",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="lol_suggest_summoners",
            description="Genera sugerencias de hechizos de invocador",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="lol_suggest_items",
            description="Genera sugerencias de items y build path",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    try:
        if name == "lol_set_matchup":
            result = await analyzer.set_matchup(
                text=arguments.get("text"),
                ally_champion=arguments.get("ally_champion"),
                ally_characteristic=arguments.get("ally_characteristic"),
                enemy_team=arguments.get("enemy_team")
            )
            
            if result["success"]:
                return [TextContent(type="text", text=f"✅ {result['message']}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "lol_fetch_data":
            result = await analyzer.fetch_static_data(
                ddragon_version=arguments.get("ddragon_version", "latest"),
                lang=arguments.get("lang", "en_US")
            )
            
            if result["success"]:
                return [TextContent(type="text", text=f"✅ {result['message']}")]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "lol_analyze_enemies":
            result = await analyzer.analyze_enemy_composition()
            
            if result["success"]:
                analysis = result["analysis"]
                output = f"""🔍 ANÁLISIS DE COMPOSICIÓN ENEMIGA

Equipo enemigo: {', '.join(result['enemy_team'])}

Distribución de daño:
• AD: {analysis['mix']['ad_pct']}%
• AP: {analysis['mix']['ap_pct']}%

Tanques: {analysis['tanks']}
Nivel de CC: {analysis['cc']}
Healing/Shields: {analysis['healing']}
Amenaza de crítico: {analysis['crit_threat']}
Poke: {analysis['poke']}"""
                
                return [TextContent(type="text", text=output)]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "lol_suggest_runes":
            result = await analyzer.get_runes_suggestion()
            
            if result["success"]:
                runes = result["runes"]
                output = f"""🌟 SUGERENCIAS DE RUNAS - {result['champion'].upper()} ({result['characteristic']})

ÁRBOL PRINCIPAL: {runes['primary_tree']}
• Piedra Angular: {runes['keystone']}
• Runas: {', '.join(runes['primary'])}

ÁRBOL SECUNDARIO: {runes['secondary_tree']}
• Runas: {', '.join(runes['secondary'])}

 FRAGMENTOS: {', '.join(runes['statShards'])}

 RAZONES:
"""
                for reason in runes['why']:
                    output += f"• {reason}\n"
                
                return [TextContent(type="text", text=output)]
            else:
                return [TextContent(type="text", text=f" {result['error']}")]
        
        elif name == "lol_suggest_summoners":
            result = await analyzer.get_summoners_suggestion()
            
            if result["success"]:
                summs = result["summoners"]
                output = f"""✨ HECHIZOS DE INVOCADOR - {result['champion'].upper()} ({result['characteristic']})

 RECOMENDADOS: {', '.join(summs['summoners'])}
 ALTERNATIVOS: {', '.join(summs['alt'])}

 EXPLICACIÓN: {summs['why']}"""
                
                return [TextContent(type="text", text=output)]
            else:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
        
        elif name == "lol_suggest_items":
            result = await analyzer.get_items_suggestion()
            
            if result["success"]:
                items = result["items"]
                output = f"""🛒 BUILD DE ITEMS - {result['champion'].upper()} ({result['characteristic']})

 ITEMS INICIALES: {', '.join(items['starter'])}

BOTAS:
• Principal: {items['boots']['pick']}
• Alternativa: {items['boots']['alt']}
• Regla: {items['boots']['rule']}

 CORE ITEMS:
"""
                for i, item in enumerate(items['core'], 1):
                    output += f"{i}. {item['item']} - {item['why']}\n"
                
                output += "\n🔧 ITEMS SITUACIONALES:\n"
                for item in items['situational']:
                    output += f"• {item['item']} - {item['when']}\n"
                
                return [TextContent(type="text", text=output)]
            else:
                return [TextContent(type="text", text=f" {result['error']}")]
        
        else:
            return [TextContent(type="text", text=f"Herramienta '{name}' no reconocida")]
            
    except Exception as e:
        error_msg = f"Error ejecutando {name}: {str(e)}\n{traceback.format_exc()}"
        return [TextContent(type="text", text=error_msg)]

async def run_mcp_server():
    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())

def main():
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        print("\n Servidor LoL terminado correctamente", file=sys.stderr)
    except Exception as e:
        print(f"Error en servidor LoL: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()