import asyncio
import sys
import json
import traceback
import os
import random
from typing import Dict, List, Any
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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

# Importación de TMDB
try:
    import tmdbsimple as tmdb
except ImportError as e:
    print(f"Error importing tmdbsimple: {e}")
    print("Please install: pip install tmdbsimple")
    sys.exit(1)

# Configurar API de TMDB
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
if not TMDB_API_KEY:
    print(" TMDB_API_KEY no encontrada en .env")
    TMDB_API_KEY = "f0a8429722a9279a0276fcc3204b6ec4"  # Fallback con tu clave

tmdb.API_KEY = TMDB_API_KEY

class MovieAnalyzer:
    
    def __init__(self):
        self.cache = {}
    
    async def search_movie(self, title: str) -> Dict[str, Any]:
        """Buscar información de película en TMDB"""
        try:
            if not title:
                return {"error": "El título de la película es requerido"}
            
            print(f"🔍 Buscando película: {title}")
            
            search = tmdb.Search()
            response = search.movie(query=title)
            
            if not search.results:
                return {"error": f"No se encontró la película '{title}' en TMDB"}
            
            movie = search.results[0]
            movie_id = movie['id']
            
            # Obtener detalles completos
            movie_details = tmdb.Movies(movie_id).info()
            
            # Obtener plataformas de streaming
            streaming_platforms = await self.get_streaming_info(movie_id)
            
            # Obtener películas similares
            similar_movies = await self.get_similar_movies(movie_id)
            
            return {
                "title": movie_details.get('title', 'Desconocido'),
                "overview": movie_details.get('overview', 'Sin sinopsis disponible'),
                "genres": [genre['name'] for genre in movie_details.get('genres', [])],
                "rating": movie_details.get('vote_average', 0),
                "release_date": movie_details.get('release_date', 'Desconocida'),
                "runtime": movie_details.get('runtime', 'N/A'),
                "budget": movie_details.get('budget', 0),
                "revenue": movie_details.get('revenue', 0),
                "streaming_platforms": streaming_platforms,
                "similar_movies": similar_movies
            }
        
        except Exception as e:
            return {"error": f"Error buscando película: {str(e)}"}
    
    async def get_streaming_info(self, movie_id: int) -> List[str]:
        """Obtener información de plataformas de streaming desde TMDB"""
        try:
            movie = tmdb.Movies(movie_id)
            providers = movie.watch_providers()
            
            streaming_platforms = []
            if providers and 'results' in providers:
                # Buscar en diferentes regiones
                for region in ['US', 'MX', 'ES', 'GT']:
                    if region in providers['results']:
                        flatrate = providers['results'][region].get('flatrate', [])
                        streaming_platforms.extend([provider['provider_name'] for provider in flatrate])
            
            return list(set(streaming_platforms))[:5] if streaming_platforms else ["Información no disponible"]
        
        except Exception as e:
            print(f" Error en get_streaming_info: {e}")
            return ["Información no disponible"]
    
    async def get_similar_movies(self, movie_id: int) -> List[Dict[str, Any]]:
        try:
            movie = tmdb.Movies(movie_id)
            similar = movie.similar_movies()
            
            return [
                {
                    "title": movie['title'],
                    "rating": movie['vote_average'],
                    "year": movie['release_date'][:4] if movie.get('release_date') else "N/A"
                }
                for movie in similar.get('results', [])[:5]
            ]
        
        except Exception as e:
            print(f" Error en get_similar_movies: {e}")
            return []
    
    async def get_movie_recommendations(self, genres: List[str] = None, min_rating: float = 7.0) -> Dict[str, Any]:
        try:
            genres = genres or []
            min_rating = min_rating or 7.0
            
            # Mapeo de géneros en español a IDs de TMDB
            genre_mapping = {
                'accion': '28', 'aventura': '12', 'animacion': '16', 'comedia': '35',
                'crimen': '80', 'documental': '99', 'drama': '18', 'familia': '10751',
                'fantasia': '14', 'historia': '36', 'horror': '27', 'musica': '10402',
                'misterio': '9648', 'romance': '10749', 'ciencia ficcion': '878',
                'terror': '27', 'thriller': '53', 'guerra': '10752', 'western': '37'
            }
            
            # Convertir géneros a IDs si es necesario
            genre_ids = []
            for genre in genres:
                genre_lower = genre.lower()
                if genre_lower in genre_mapping:
                    genre_ids.append(genre_mapping[genre_lower])
                else:
                    # Buscar por nombre en inglés
                    genre_ids.append(genre)
            
            discover = tmdb.Discover()
            movies = discover.movie(
                with_genres="|".join(genre_ids) if genre_ids else "",
                vote_average_gte=min_rating,
                sort_by='popularity.desc',
                page=1
            )
            
            return {
                "criteria": {
                    "genres": genres,
                    "min_rating": min_rating
                },
                "recommendations": [
                    {
                        "title": movie['title'],
                        "rating": movie['vote_average'],
                        "overview": (movie['overview'][:100] + "...") if movie.get('overview') else "Sin descripción",
                        "year": movie['release_date'][:4] if movie.get('release_date') else "N/A",
                        "popularity": movie.get('popularity', 0)
                    }
                    for movie in movies.get('results', [])[:5]
                ]
            }
        
        except Exception as e:
            return {"error": f"Error obteniendo recomendaciones: {str(e)}"}
    
    async def get_random_movie(self) -> Dict[str, Any]:
        """Obtener película aleatoria de las populares"""
        try:
            movies = tmdb.Movies()
            
            # Obtener páginas aleatorias para más variedad
            page = random.randint(1, 5)
            popular = movies.popular(page=page)
            
            if popular['results']:
                movie = random.choice(popular['results'])
                
                return {
                    "title": movie['title'],
                    "overview": movie.get('overview', 'Sin sinopsis disponible'),
                    "rating": movie.get('vote_average', 0),
                    "release_date": movie.get('release_date', 'Desconocida'),
                    "popularity": movie.get('popularity', 0),
                    "genre_ids": movie.get('genre_ids', [])
                }
            else:
                return {"error": "No se encontraron películas populares"}
        
        except Exception as e:
            return {"error": f"Error obteniendo película aleatoria: {str(e)}"}
    
    async def get_trending_movies(self) -> Dict[str, Any]:
        """Obtener películas en tendencia"""
        try:
            trending = tmdb.Trending()
            movies = trending.movie_week()  # Tendencias de la semana
            
            return {
                "trending_movies": [
                    {
                        "title": movie['title'],
                        "rating": movie.get('vote_average', 0),
                        "overview": (movie.get('overview', '')[:100] + "...") if movie.get('overview') else "Sin descripción",
                        "release_date": movie.get('release_date', 'N/A'),
                        "popularity": movie.get('popularity', 0)
                    }
                    for movie in movies.get('results', [])[:7]
                ]
            }
        
        except Exception as e:
            return {"error": f"Error obteniendo películas en tendencia: {str(e)}"}

# Crear servidor MCP
server = Server("movie-advisor")
analyzer = MovieAnalyzer()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="search_movie",
            description="Busca información detallada de una película por título",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título de la película a buscar"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="get_movie_recommendations",
            description="Obtiene recomendaciones de películas basadas en géneros y rating mínimo",
            inputSchema={
                "type": "object",
                "properties": {
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de géneros preferidos (ej: ['accion', 'comedia'])"
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "Rating mínimo (0-10)"
                    }
                }
            }
        ),
        Tool(
            name="get_random_movie",
            description="Obtiene una película aleatoria popular",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_trending_movies",
            description="Obtiene las películas más populares de la semana",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    
    try:
        if name == "search_movie":
            title = arguments.get("title", "")
            result = await analyzer.search_movie(title)
            
            if "error" in result:
                return [TextContent(type="text", text=f"❌ {result['error']}")]
            
            output = f"""🎬 INFORMACIÓN DE PELÍCULA

Título: {result['title']}
Año: {result.get('release_date', 'N/A')[:4] if result.get('release_date') else 'N/A'}
Rating:  {result.get('rating', 0)}/10
Duración: {result.get('runtime', 'N/A')} minutos
Géneros: {', '.join(result.get('genres', []))}

 SINOPSIS:
{result.get('overview', 'Sin sinopsis disponible')}

 PLATAFORMAS:
{', '.join(result.get('streaming_platforms', ['No disponible']))}

 PELÍCULAS SIMILARES:"""
            
            for similar in result.get('similar_movies', [])[:3]:
                output += f"\n• {similar['title']} ({similar['year']}) - ⭐ {similar['rating']}/10"
            
            return [TextContent(type="text", text=output)]
        
        elif name == "get_movie_recommendations":
            genres = arguments.get("genres", [])
            min_rating = arguments.get("min_rating", 7.0)
            result = await analyzer.get_movie_recommendations(genres, min_rating)
            
            if "error" in result:
                return [TextContent(type="text", text=f" {result['error']}")]
            
            criteria = result.get('criteria', {})
            output = f""" RECOMENDACIONES DE PELÍCULAS

Criterios:
• Géneros: {', '.join(criteria.get('genres', [])) if criteria.get('genres') else 'Cualquiera'}
• Rating mínimo: {criteria.get('min_rating', 7.0)}/10

 PELÍCULAS RECOMENDADAS:
"""
            
            for i, movie in enumerate(result.get('recommendations', []), 1):
                output += f"""
{i}. {movie['title']} ({movie['year']})
    {movie['rating']}/10
    {movie['overview']}
"""
            
            return [TextContent(type="text", text=output)]
        
        elif name == "get_random_movie":
            result = await analyzer.get_random_movie()
            
            if "error" in result:
                return [TextContent(type="text", text=f" {result['error']}")]
            
            output = f""" PELÍCULA ALEATORIA

 {result['title']}
 {result.get('release_date', 'N/A')[:4] if result.get('release_date') else 'N/A'}
 {result.get('rating', 0)}/10
 Popularidad: {result.get('popularity', 0):.1f}

 SINOPSIS:
{result.get('overview', 'Sin sinopsis disponible')}"""
            
            return [TextContent(type="text", text=output)]
        
        elif name == "get_trending_movies":
            result = await analyzer.get_trending_movies()
            
            if "error" in result:
                return [TextContent(type="text", text=f" {result['error']}")]
            
            output = " PELÍCULAS EN TENDENCIA ESTA SEMANA\n"
            
            for i, movie in enumerate(result.get('trending_movies', []), 1):
                output += f"""
{i}. {movie['title']} ({movie.get('release_date', 'N/A')[:4] if movie.get('release_date') else 'N/A'})
    {movie['rating']}/10 •  {movie.get('popularity', 0):.1f}
    {movie['overview']}
"""
            
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
        print("\n Servidor Movies terminado correctamente", file=sys.stderr)
    except Exception as e:
        print(f" Error en servidor Movies: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()