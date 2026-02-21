#!/bin/bash
# RunPod Deployment Script for Layout Generator Training
# Pod ID: zbfsosw5tmne0c

echo "=== Infographix Layout Generator Training ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo "CUDA: $(nvcc --version | grep release)"

# Create workspace
cd /workspace
mkdir -p infographix
cd infographix

# Install dependencies
echo "Installing dependencies..."
pip install torch transformers datasets accelerate sentencepiece --quiet

# Download training data (from your local machine)
echo "Waiting for training data..."
echo "Upload the following files to /workspace/infographix/:"
echo "  - ml/data/templates/intents.jsonl"
echo "  - ml/training/train_layout_generator.py"
echo ""
echo "Use: runpodctl send <file> or SCP"

# Training command (run after uploading files)
cat << 'EOF' > run_training.sh
#!/bin/bash
cd /workspace/infographix

# Run training
python train_layout_generator.py \
    --model t5-base \
    --epochs 20 \
    --batch-size 16 \
    --lr 3e-5 \
    --data-path intents.jsonl \
    --output-dir trained_model

echo "Training complete! Download trained_model/ folder"
EOF

chmod +x run_training.sh
echo "Setup complete. Run: ./run_training.sh"
