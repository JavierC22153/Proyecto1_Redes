# Proyecto1_Redes
# 🏎️ Chatbot F1 + MCP - Análisis Avanzado de Fórmula 1

Un chatbot inteligente que utiliza Claude AI y el protocolo MCP (Model Context Protocol) para realizar análisis avanzados de datos de Fórmula 1, manipulación de archivos y operaciones de Git.

## ✨ Características

-  **Análisis de F1**: Estrategias de neumáticos, timing de pit stops, comparaciones entre pilotos
-  **Manipulación de archivos**: Lectura, escritura y búsqueda de archivos
-  **Operaciones Git**: Commits, branches, historial del repositorio
-  **IA Conversacional**: Powered by Claude AI con capacidades avanzadas
-  **Datos de la Formula 1**: Integración con la API OpenF1

## 🛠️ Requisitos del Sistema

### Software necesario:
- **Python 3.8+**
- **Node.js 16+** (para servidores MCP)
- **Git** (para funcionalidades de control de versiones)

### Dependencias Python:
- `anthropic`: Cliente para la API de Claude
- `python-dotenv`: Manejo de variables de entorno
- `aiohttp`: Cliente HTTP asíncrono
- `mcp`: Protocolo de contexto de modelo

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
```

### 2. Crear entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto:

```env
ANTHROPIC_API_KEY=tu_api_key_aqui
```

**Para obtener tu API key:**
1. Visita [console.anthropic.com](https://console.anthropic.com)
2. Crea una cuenta o inicia sesión
3. Ve a la sección "API Keys"
4. Genera una nueva API key
5. Copia la key al archivo `.env`

## 🚀 Ejecución

```bash
python Chatbot.py
```

El programa iniciará y conectará automáticamente los servidores MCP disponibles:
- ✅ Servidor filesystem (manipulación de archivos)
- ✅ Servidor git (operaciones de Git)
- ✅ Servidor F1 (análisis de Fórmula 1)

## 💬 Uso

### Comandos especiales:
- `/tools` - Ver herramientas MCP disponibles
- `/f1` - Ver ejemplos de análisis F1
- `/logs` - Ver logs recientes de interacciones
- `/quit` - Salir del chatbot

### Ejemplos de consultas F1:

```
🏎️ Analiza la estrategia de neumáticos de Verstappen en la sesión 9158

🏎️ Compara el timing de pit stops entre los pilotos 1, 44 y 16

🏎️ Muéstrame todas las sesiones de 2024

🏎️ ¿Qué pilotos participaron en la sesión de Mónaco?
````

### Ejemplos de Git:

```
🔧 Muestra el estado del repositorio

🔧 Ver el historial de commits

🔧 Crear una nueva rama llamada feature-nueva
```
