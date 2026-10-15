#!/usr/bin/env python3
"""
Utility script to export and quantize Laya (ModernBERT-large) to INT8 ONNX.
Produces a ~420MB INT8 model capable of sub-15ms non-autoregressive inference on CPU.

Requirements:
    pip install optimum[onnxruntime] onnx onnxruntime
Usage:
    python export_laya_onnx.py --model convaiinnovations/laya --output ../models/laya_onnx
"""

import os
import sys
import argparse

def export_to_onnx(model_id: str, output_dir: str):
    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
        from optimum.onnxruntime.configuration import AutoQuantizationConfig
        from transformers import AutoTokenizer
    except ImportError:
        print("[Error] Optimum / ONNXRuntime is required. Install via: pip install optimum[onnxruntime] onnx")
        sys.exit(1)

    print(f"Loading and exporting {model_id} to ONNX format...")
    os.makedirs(output_dir, exist_ok=True)
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(output_dir)

    # 1. Export FP32/FP16 ONNX model
    ort_model = ORTModelForSequenceClassification.from_pretrained(model_id, export=True)
    ort_model.save_pretrained(output_dir)
    print(f"FP32 ONNX model exported to {output_dir}")

    # 2. Dynamic INT8 Quantization (Optimized for CPU latency)
    print("Applying INT8 dynamic quantization for CPU acceleration...")
    quantizer = ORTQuantizer.from_pretrained(ort_model)
    qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)
    
    quantized_dir = os.path.join(output_dir, "int8")
    quantizer.quantize(save_dir=quantized_dir, quantization_config=qconfig)
    tokenizer.save_pretrained(quantized_dir)
    
    print(f"\n[SUCCESS] Laya INT8 ONNX model ready at: {quantized_dir}")
    print("Memory footprint: ~420MB. Target inference latency: <15ms.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Laya to INT8 ONNX")
    parser.add_argument("--model", type=str, default="convaiinnovations/laya", help="HuggingFace model ID or local path")
    parser.add_argument("--output", type=str, default="models/laya_onnx", help="Output directory")
    args = parser.parse_args()
    
    export_to_onnx(args.model, args.output)
