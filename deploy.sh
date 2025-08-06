#!/bin/bash

# deploy.sh - Automated deployment script for Website Analyzer Backend
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
SERVICE_NAME="website-analyzer-backend"
REGION="us-central1"
DEPLOYMENT_METHOD="cloudrun" # Options: cloudrun, appengine, gke

# Environment variables (move to .env.production for security)
MONGODB_URL="mongodb+srv://anand1234singh76:gJRKicWZeQ4OjBf7@cluster0.rly35fe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME="lead-gen-ai-db"
GEMINI_API_KEY="AIzaSyBWezIZl-crbdE-T60bK2KgHZyhqWehUXY"
GEMINI_MODEL="gemini-1.5-flash"
SECRET_KEY="your-super-secret-key-change-this-in-production"

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK is not installed. Please install it first."
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_error "Not authenticated with Google Cloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check if project is set
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            print_error "No GCP project set. Please set PROJECT_ID variable or run 'gcloud config set project PROJECT_ID'"
            exit 1
        fi
    fi
    
    print_status "Using project: $PROJECT_ID"
}

enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable containerregistry.googleapis.com
    
    if [ "$DEPLOYMENT_METHOD" = "appengine" ]; then
        gcloud services enable appengine.googleapis.com
    elif [ "$DEPLOYMENT_METHOD" = "gke" ]; then
        gcloud services enable container.googleapis.com
    fi
}

deploy_to_cloud_run() {
    print_status "Deploying to Cloud Run..."
    
    gcloud run deploy $SERVICE_NAME \
        --source . \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --set-env-vars="MONGODB_URL=$MONGODB_URL,DATABASE_NAME=$DATABASE_NAME,GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_MODEL=$GEMINI_MODEL,SECRET_KEY=$SECRET_KEY,DEBUG=False" \
        --memory 2Gi \
        --cpu 2 \
        --timeout 3600 \
        --max-instances 10 \
        --min-instances 0
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
    print_status "Service deployed at: $SERVICE_URL"
    
    # Test the deployment
    print_status "Testing deployment..."
    if curl -s "$SERVICE_URL/api/v1/health" > /dev/null; then
        print_status "✅ Health check passed!"
    else
        print_warning "⚠️  Health check failed. Check logs with: gcloud run logs tail $SERVICE_NAME --region $REGION"
    fi
}

deploy_to_app_engine() {
    print_status "Deploying to App Engine..."
    
    # Check if app.yaml exists
    if [ ! -f "app.yaml" ]; then
        print_error "app.yaml not found. Please create it first."
        exit 1
    fi
    
    gcloud app deploy app.yaml --quiet
    
    # Get service URL
    SERVICE_URL=$(gcloud app browse --no-launch-browser 2>&1 | grep -o 'https://[^"]*')
    print_status "Service deployed at: $SERVICE_URL"
}

deploy_to_gke() {
    print_status "Deploying to Google Kubernetes Engine..."
    print_warning "GKE deployment requires manual cluster setup. Please follow the manual instructions."
}

build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
    
    # Build image
    docker build -t "$IMAGE_NAME:latest" .
    
    # Push to Container Registry
    docker push "$IMAGE_NAME:latest"
    
    print_status "Image pushed: $IMAGE_NAME:latest"
}

main() {
    print_status "🚀 Starting deployment of Website Analyzer Backend"
    
    # Check if we're in the backend directory
    if [ ! -f "requirements.txt" ] || [ ! -f "app/main.py" ]; then
        print_error "Please run this script from the backend directory"
        exit 1
    fi
    
    check_prerequisites
    enable_apis
    
    case $DEPLOYMENT_METHOD in
        "cloudrun")
            deploy_to_cloud_run
            ;;
        "appengine")
            deploy_to_app_engine
            ;;
        "gke")
            build_and_push_image
            deploy_to_gke
            ;;
        *)
            print_error "Unknown deployment method: $DEPLOYMENT_METHOD"
            print_status "Available methods: cloudrun, appengine, gke"
            exit 1
            ;;
    esac
    
    print_status "🎉 Deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --method)
            DEPLOYMENT_METHOD="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID    GCP Project ID"
            echo "  --method METHOD         Deployment method (cloudrun, appengine, gke)"
            echo "  --region REGION         GCP Region (default: us-central1)"
            echo "  --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --project my-project --method cloudrun"
            echo "  $0 --project my-project --method appengine --region us-west1"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main