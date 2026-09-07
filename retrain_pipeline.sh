#!/bin/bash
cd /home/mohammed/Downloads/trading_platform
python3 scripts/build_expert_dataset.py
python3 scripts/ha3c_pretrain.py
python3 scripts/a2c_finetune.py
# Optionally restart trading service
