# InvestGlance

A financial literacy and market analytics platform that translates complex stock market data into accessible insights through interactive visualizations and comparative analysis.

## Running with Docker

### For Development

1. **Install Docker and Docker Compose**:
   - [Install Docker](https://docs.docker.com/get-docker/)
   - [Install Docker Compose](https://docs.docker.com/compose/install/)

2. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/invest-glance.git
   cd invest-glance
   ```

3. **Set up the secrets file**:
   - Create a `.streamlit` directory if it doesn't exist
   - Create a file `.streamlit/secrets.toml` with your API keys:
     ```toml
     [api_keys]
     newsapi = "your_newsapi_key"
     gemini = "your_gemini_api_key"
     ```

4. **Run the application**:
   ```bash
   docker-compose up
   ```

5. **Open the application**:
   - Navigate to [http://localhost:8501](http://localhost:8501) in your browser

6. **Development workflow**:
   - Edit files in your local directory
   - Changes will be reflected in the app when you refresh the browser
   - No need to restart the container for most code changes

### For Users

1. **Prerequisites**:
   - Docker installed on your system

2. **Quick start**:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/invest-glance.git
   cd invest-glance
   
   # Add your API keys
   mkdir -p .streamlit
   echo '[api_keys]' > .streamlit/secrets.toml
   echo 'newsapi = "your_newsapi_key"' >> .streamlit/secrets.toml
   echo 'gemini = "your_gemini_api_key"' >> .streamlit/secrets.toml
   
   # Run with Docker
   docker-compose up -d
   ```

3. **Access the application**:
   - Open [http://localhost:8501](http://localhost:8501) in your browser

4. **Stop the application**:
   ```bash
   docker-compose down
   ```

## Running Without Docker

1. **Set up a Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up secrets**:
   - Create `.streamlit/secrets.toml` as described above

3. **Run the application**:
   ```bash
   streamlit run app.py
   

# Clone the repository
git clone https://github.com/yourusername/invest-glance.git
cd invest-glance

# Add your API keys
mkdir -p .streamlit
echo '[api_keys]' > .streamlit/secrets.toml
echo 'newsapi = "your_newsapi_key"' >> .streamlit/secrets.toml
echo 'gemini = "your_gemini_api_key"' >> .streamlit/secrets.toml

# Run with Docker
docker-compose up -d


Running Without Docker
Set up a Python environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


Set up secrets:

Create .streamlit/secrets.toml as described above
Run the application:
streamlit run app.py