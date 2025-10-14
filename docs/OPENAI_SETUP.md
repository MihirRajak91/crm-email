# OpenAI Integration Setup Guide

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
poetry install
```

### 2. Set Environment Variables
Create or update your `.env` file:
```bash
# LLM Provider Selection
LLM_PROVIDER=openai  # or 'ollama'

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo  # optional, defaults to gpt-3.5-turbo
OPENAI_TIMEOUT=30  # optional, defaults to 30 seconds
OPENAI_MAX_TOKENS=2000  # optional, defaults to 2000

# Ollama Configuration (existing)
LLAMA3_API_KEY=your_ollama_url  # optional, for fallback
LLAMA_MODEL=llama3.1  # optional, defaults to llama3.1
OLLAMA_TIMEOUT=5  # optional, defaults to 5 seconds
```

### 3. Test the Integration
```bash
python test_llm_integration.py
```

## 🔧 Configuration Options

### Switch Between Providers

**Option 1: Environment Variable**
```bash
export LLM_PROVIDER=openai  # or 'ollama'
```

**Option 2: Edit Constants File**
Edit `crm/configs/constant.py`:
```python
LLM_PROVIDER = 'openai'  # or 'ollama'
```

### OpenAI Models Available
- `gpt-3.5-turbo` (default, cost-effective and fast)
- `gpt-4o-mini` (faster than GPT-4)
- `gpt-4o` (more capable)
- `gpt-4-turbo` (legacy)
- `gpt-3.5-turbo-16k` (longer context)

## 🔄 How It Works

1. **Automatic Provider Selection**: The system checks `LLM_PROVIDER` and loads the appropriate LLM
2. **Fallback Chain**: If OpenAI fails → tries Ollama → uses fallback response
3. **Unified Interface**: Same API regardless of provider
4. **Easy Switching**: Change one constant to switch providers

## 📝 Usage in Your Code

The integration is already applied to your existing code:

```python
# In qdrant_response.py and qdrant_response_optimized.py
from crm.services.llm_service import llm

# Use the LLM as before - no code changes needed!
response = llm.invoke(prompt)
```

## 🧪 Testing

Run the test script to verify everything works:
```bash
python test_llm_integration.py
```

This will show:
- Current provider configuration
- API key status
- Test response generation
- Configuration guide

## 🔍 Troubleshooting

### Common Issues:

1. **"OPENAI_API_KEY is not set"**
   - Add your OpenAI API key to `.env` file
   - Get one from: https://platform.openai.com/api-keys

2. **"Failed to import OpenAI service"**
   - Run `poetry install` to install dependencies
   - Check that `langchain-openai` and `openai` are installed

3. **"Connection timeout"**
   - Check your internet connection
   - Verify the API key is correct
   - Try increasing `OPENAI_TIMEOUT` in `.env`

4. **Falling back to Ollama**
   - This is normal if OpenAI is unavailable
   - Check your OpenAI API key and billing status

## 💡 Tips

- **Cost Optimization**: Use `gpt-3.5-turbo` for most use cases (cheaper than GPT-4)
- **Performance**: OpenAI is generally faster than Ollama
- **Privacy**: Ollama runs locally, OpenAI sends data to their servers
- **Reliability**: The fallback system ensures your app keeps working 