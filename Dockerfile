FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate synthetic data and build vector store during build
RUN python run_pipeline.py --count 120

# Expose Streamlit port
EXPOSE 7860

# HuggingFace Spaces expects port 7860
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true"]
