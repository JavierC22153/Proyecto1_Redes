import asyncio
import aiohttp
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import sys
import traceback

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

# Configuración de la API OpenF1
OPENF1_BASE_URL = "https://api.openf1.org/v1"

@dataclass
class TireStint:
    compound: str
    start_lap: int
    end_lap: int
    laps_count: int
    avg_lap_time: float
    degradation_per_lap: float
    stint_time: float

class F1DataAnalyzer:
    
    def __init__(self):
        self.session = None
        self.cache = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_data(self, endpoint: str, params: Dict = None) -> List[Dict]:
        cache_key = f"{endpoint}_{str(params)}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        url = f"{OPENF1_BASE_URL}/{endpoint}"
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.cache[cache_key] = data
                    return data
                else:
                    raise Exception(f"Error API: {response.status}")
        except Exception as e:
            raise Exception(f"Error obteniendo datos de {endpoint}: {str(e)}")
    
    async def analyze_tire_strategy(self, session_key: int, driver_number: int) -> Dict[str, Any]:
        try:
            # Obtener datos de stints
            stints_data = await self.get_data("stints", {
                "session_key": session_key,
                "driver_number": driver_number
            })
            
            # Obtener tiempos por vuelta
            laps_data = await self.get_data("laps", {
                "session_key": session_key,
                "driver_number": driver_number
            })
            
            # Obtener info del piloto
            drivers_data = await self.get_data("drivers", {
                "session_key": session_key,
                "driver_number": driver_number
            })
            
            driver_info = drivers_data[0] if drivers_data else {}
            driver_name = f"{driver_info.get('first_name', '')} {driver_info.get('last_name', '')}"
            
            # Analizar cada stint
            stints_analysis = []
            for stint in stints_data:
                stint_laps = [lap for lap in laps_data 
                             if stint["stint_number"] == lap.get("stint_number")]
                
                if not stint_laps:
                    continue
                    
                # Calcular estadísticas del stint
                lap_times = [lap["lap_duration"] for lap in stint_laps 
                            if lap.get("lap_duration") and lap["lap_duration"] > 0]
                
                if len(lap_times) < 2:
                    continue
                
                avg_time = statistics.mean(lap_times)
                stint_analysis = TireStint(
                    compound=stint.get("compound", "Unknown"),
                    start_lap=min(lap["lap_number"] for lap in stint_laps),
                    end_lap=max(lap["lap_number"] for lap in stint_laps),
                    laps_count=len(stint_laps),
                    avg_lap_time=avg_time,
                    degradation_per_lap=self._calculate_degradation(lap_times),
                    stint_time=sum(lap_times)
                )
                stints_analysis.append(stint_analysis)
            
            return {
                "driver_name": driver_name,
                "driver_number": driver_number,
                "session_key": session_key,
                "stints": [
                    {
                        "compound": stint.compound,
                        "start_lap": stint.start_lap,
                        "end_lap": stint.end_lap,
                        "laps_count": stint.laps_count,
                        "avg_lap_time": round(stint.avg_lap_time, 3),
                        "degradation_per_lap": round(stint.degradation_per_lap, 4),
                        "total_time": round(stint.stint_time, 3)
                    } for stint in stints_analysis
                ],
                "total_pit_stops": len(stints_analysis) - 1,
                "strategy_effectiveness": "Análisis completado"
            }
        except Exception as e:
            return {"error": f"Error analizando estrategia: {str(e)}"}
    
    def _calculate_degradation(self, lap_times: List[float]) -> float:
        if len(lap_times) < 3:
            return 0.0
        
        try:
            n = len(lap_times)
            x_sum = sum(range(n))
            y_sum = sum(lap_times)
            xy_sum = sum(i * time for i, time in enumerate(lap_times))
            x2_sum = sum(i * i for i in range(n))
            
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
            return slope
        except:
            return 0.0
    
    async def get_driver_info(self, session_key: int) -> Dict[str, Any]:
        """Obtener información de pilotos en una sesión"""
        try:
            drivers = await self.get_data("drivers", {"session_key": session_key})
            
            drivers_info = []
            for driver in sorted(drivers, key=lambda x: x.get("driver_number", 0)):
                drivers_info.append({
                    "number": driver.get('driver_number', 'N/A'),
                    "name": f"{driver.get('first_name', '')} {driver.get('last_name', '')}",
                    "team": driver.get('team_name', 'N/A'),
                    "acronym": driver.get('name_acronym', 'N/A')
                })
            
            return {
                "session_key": session_key,
                "drivers": drivers_info,
                "total_drivers": len(drivers_info)
            }
        except Exception as e:
            return {"error": f"Error obteniendo pilotos: {str(e)}"}
    
    async def get_session_info(self, year: int, location: str = None) -> Dict[str, Any]:
        """Obtener información de sesiones"""
        try:
            sessions = await self.get_data("sessions", {"year": year})
            
            if location:
                sessions = [s for s in sessions if location.lower() in s.get("location", "").lower()]
            
            sessions_info = []
            for session in sessions:
                sessions_info.append({
                    "session_key": session.get('session_key'),
                    "session_name": session.get('session_name', 'Unknown'),
                    "location": session.get('location', 'Unknown'),
                    "country": session.get('country_name', 'N/A'),
                    "date": session.get('date_start', 'N/A')
                })
            
            return {
                "year": year,
                "location_filter": location,
                "sessions": sessions_info,
                "total_sessions": len(sessions_info)
            }
        except Exception as e:
            return {"error": f"Error obteniendo sesiones: {str(e)}"}

# Crear servidor MCP
server = Server("f1-strategy-analyzer")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="analyze_tire_strategy",
            description="Analiza la estrategia de neumáticos de un piloto específico en una sesión",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "Clave de sesión de OpenF1"
                    },
                    "driver_number": {
                        "type": "integer", 
                        "description": "Número del piloto"
                    }
                },
                "required": ["session_key", "driver_number"]
            }
        ),
        Tool(
            name="get_driver_info",
            description="Obtiene información de pilotos en una sesión específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_key": {
                        "type": "integer",
                        "description": "Clave de sesión de OpenF1"
                    }
                },
                "required": ["session_key"]
            }
        ),
        Tool(
            name="get_session_info",
            description="Obtiene información de sesiones disponibles por año y ubicación",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Año de la temporada"
                    },
                    "location": {
                        "type": "string",
                        "description": "Ubicación del circuito (opcional)"
                    }
                },
                "required": ["year"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    
    try:
        async with F1DataAnalyzer() as analyzer:
            if name == "analyze_tire_strategy":
                result = await analyzer.analyze_tire_strategy(
                    arguments["session_key"],
                    arguments["driver_number"]
                )
                
                if "error" in result:
                    return [TextContent(type="text", text=result["error"])]
                
                # Formatear resultado
                output = f"""=== ANÁLISIS DE ESTRATEGIA DE NEUMÁTICOS ===

Piloto: {result['driver_name']} (#{result['driver_number']})
Sesión: {result['session_key']}

STINTS DE NEUMÁTICOS:
"""
                for i, stint in enumerate(result['stints'], 1):
                    output += f"""
Stint {i} - {stint['compound']}:
  • Vueltas: {stint['start_lap']}-{stint['end_lap']} ({stint['laps_count']} vueltas)
  • Tiempo promedio: {stint['avg_lap_time']:.3f}s
  • Degradación/vuelta: {stint['degradation_per_lap']:.4f}s
  • Tiempo total: {stint['total_time']:.1f}s
"""
                
                output += f"\nPARADAS EN BOXES: {result['total_pit_stops']}"
                return [TextContent(type="text", text=output)]
            
            elif name == "get_driver_info":
                result = await analyzer.get_driver_info(arguments["session_key"])
                
                if "error" in result:
                    return [TextContent(type="text", text=result["error"])]
                
                output = f"""=== PILOTOS EN LA SESIÓN {result['session_key']} ===

Total de pilotos: {result['total_drivers']}

"""
                for driver in result['drivers']:
                    output += f"• #{driver['number']} - {driver['name']}\n"
                    output += f"  Equipo: {driver['team']}\n"
                    output += f"  Abreviatura: {driver['acronym']}\n\n"
                
                return [TextContent(type="text", text=output)]
            
            elif name == "get_session_info":
                year = arguments["year"]
                location = arguments.get("location")
                result = await analyzer.get_session_info(year, location)
                
                if "error" in result:
                    return [TextContent(type="text", text=result["error"])]
                
                filter_text = f" - {location}" if location else ""
                output = f"""=== SESIONES {year}{filter_text} ===

Total de sesiones: {result['total_sessions']}

"""
                for session in result['sessions']:
                    output += f"• {session['session_name']} - {session['location']}\n"
                    output += f"  Session Key: {session['session_key']}\n"
                    output += f"  País: {session['country']}\n"
                    output += f"  Fecha: {session['date']}\n\n"
                
                return [TextContent(type="text", text=output)]
            
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
        print("\n✅ Servidor F1 terminado correctamente", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error en servidor F1: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()