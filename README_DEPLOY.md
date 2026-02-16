# Deployment Guide

## Option 1: HuggingFace Spaces (Recommended for Demo)

HuggingFace Spaces provides free hosting for Streamlit apps — perfect for portfolio demos.

### Steps

1. **Create a HuggingFace account** at huggingface.co

2. **Create a new Space**:
   - Go to huggingface.co/new-space
   - Name: `contract-intelligence-agent`
   - SDK: Docker
   - Visibility: Public

3. **Push your code**:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/contract-intelligence-agent
   git push hf main
   ```

4. **Add secrets** (optional, for Claude mode):
   - Go to Space Settings > Repository secrets
   - Add `ANTHROPIC_API_KEY`

5. The Space will build automatically using the Dockerfile and be live at:
   `https://huggingface.co/spaces/YOUR_USERNAME/contract-intelligence-agent`

### Notes
- The Dockerfile generates synthetic data and builds the vector store during build
- First build takes ~5-10 minutes (embedding 3,000+ chunks)
- Mock mode works without any secrets configured
- Free tier has 2 vCPU / 16GB RAM — sufficient for this demo

## Option 2: Streamlit Community Cloud

1. Push code to GitHub
2. Go to share.streamlit.io
3. Connect your GitHub repo
4. Set `app/streamlit_app.py` as the main file
5. Add `ANTHROPIC_API_KEY` in Secrets if using Claude mode

**Note**: You'll need to modify `run_pipeline.py` to run during app startup
since Streamlit Cloud doesn't support Docker.

## Option 3: AWS / Azure (Production-Grade)

For a more production-like deployment:

```bash
# AWS
docker build -t contract-agent .
docker tag contract-agent:latest YOUR_ECR_REPO:latest
docker push YOUR_ECR_REPO:latest
# Deploy via ECS Fargate or App Runner

# Azure
az acr build --registry YOUR_ACR --image contract-agent .
az containerapp create --name contract-agent --image YOUR_ACR/contract-agent
```

## Embedding in Your Portfolio Website

Once deployed to HuggingFace Spaces, embed the demo in your portfolio site:

```html
<iframe
  src="https://YOUR_USERNAME-contract-intelligence-agent.hf.space"
  width="100%"
  height="800"
  frameborder="0"
  style="border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.1);"
></iframe>
```
