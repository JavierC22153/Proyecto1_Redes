# MCP Chatbot

An advanced AI chatbot powered by Claude AI that integrates multiple specialized servers through the Model Context Protocol (MCP), including remote JSON-RPC capabilities hosted on Google Cloud Run.

### Specialized Servers

#### Formula 1 Strategy Analyzer
- Race strategy analysis and insights
- Tire strategy and pit stop timing analysis
- Driver and session data analysis
- Performance comparisons and statistics

#### League of Legends Build Advisor
- Champion build recommendations
- Rune configurations for different matchups
- Item optimization based on team compositions
- Strategic analysis for different game scenarios

#### Movie Advisor
- Movie search and recommendations
- TMDB API integration for comprehensive movie data
- Trending movies and personalized suggestions
- Detailed movie information including ratings and streaming platforms

#### File System Operations
- Read, write, and search files and directories
- File manipulation and content analysis
- Directory structure exploration

####  Git Operations
- Repository management
- Commit history and branch operations
- Git status and change tracking

####  Remote MCP JSON-RPC Server
- **Random Number Generation**: Simple and custom range number generation
- **Server Information**: Real-time server status and capabilities

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js and npm (for filesystem MCP server)
- Git (for git MCP server)
- Active internet connection (for remote MCP and API services)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd mcp-chatbot
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Required: Anthropic API Key
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional:Groq API Key
GROQ_API_KEY=your-groq-api-key-here

# Optional: TMDB API Key 
TMDB_API_KEY=your-tmdb-api-key-here
```

### 4. Install MCP Server Dependencies

#### Filesystem Server (Node.js)
The filesystem server will be automatically installed via npx when first run.

#### Git Server (Python)
```bash
pip install mcp-server-git
```

## Usage

### Starting the Chatbot
```bash
python Chatbot.py
```

### Interactive Commands
Once the chatbot is running, you can use these special commands:

- `/quit` - Exit the chatbot
- `/logs` - View recent interaction logs
- `/f1` - Show Formula 1 analysis examples
- `/lol` - Show League of Legends examples
- `/movies` - Show movie search examples
- `/remote` - Show remote MCP JSON-RPC examples

### Example Interactions

#### Remote Number Generation
```
You: "Give me a random number"
Claude: Generates a random number using the remote JSON-RPC server

You: "Generate a number between 50 and 200"
Claude: Uses custom range generation via remote MCP server
```

#### Formula 1 Analysis
```
You: "What drivers raced in the Singapore GP?"
Claude: Analyzes F1 data and provides driver information

You: "Show me Hamilton's strategy in session 9158"
Claude: Detailed strategy analysis using F1 MCP server
```

#### League of Legends
```
You: "I want to play Darius tank against Garen, Maokai, Ahri, Jinx, Lulu"
Claude: Provides build recommendations and strategic advice

You: "What runes should I use with Azir AP against heavy CC?"
Claude: Suggests optimal rune configurations
```

#### Movie Recommendations
```
You: "Recommend me action movies with rating above 8"
Claude: Provides personalized movie recommendations

You: "What's trending this week?"
Claude: Shows current trending movies
```

### Conversation History
The system maintains the last 20 messages for context. Adjust this in the `add_to_context` method:
```python
if len(self.conversation_history) > 20:  # Modify this number
```

### Timeout Settings
Server connection and tool execution timeouts can be adjusted:
```python
async with asyncio.timeout(15):  # Connection timeout
async with asyncio.timeout(30):  # Tool execution timeout
```

## Monitoring and Debugging

### Log Analysis
View recent interactions:
```bash
tail -f mcp_interactions.log
```

### Server Status
Check which servers are connected:
- The chatbot displays connection status during startup
- Use `/logs` command to see recent server interactions
- Check the log file for detailed error messages

## 📝 API Keys Setup

### Anthropic API Key
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account and generate an API key
3. Add it to your `.env` file as `ANTHROPIC_API_KEY`

### TMDB API Key (Optional)
1. Visit [TMDB](https://www.themoviedb.org/settings/api)
2. Register for an API key
3. Add it to your `.env` file as `TMDB_API_KEY`

## Troubleshooting

### Common Issues

**MCP Server Connection Failures**
- Ensure all dependencies are installed
- Check that Node.js is available for filesystem server
- Verify Python environment has required packages

**API Rate Limits**
- Respect Anthropic API rate limits
- TMDB API has daily request limits
- Remote MCP server has built-in rate limiting

**Environment Variables**
- Verify `.env` file is in the project root
- Check that API keys are valid and active
- Ensure no extra spaces in environment variables
