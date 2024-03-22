#!/bin/bash
set -ex
# 首先检查是否提供了环境位置参数
if [ -z "$1" ]; then
	echo "未提供环境位置参数"
	exit 1
fi

# pip install git+https://github.com/sustech-data/cocker.git
cocker dl.yml

CUDAVER="cu118"
PYTHON_VERSION="cp310"
API_URL="https://api.github.com/repos/Dao-AILab/flash-attention/releases/latest"
FA_VERSION=$(curl -s $API_URL | jq -r '.tag_name' | sed 's/^v//')
if [ "$FA_VERSION" == "null" ] || [ $? -ne 0 ] || [ -z "$FA_VERSION" ]; then
    # 如果curl命令失败或者FA_VERSION为空，则使用回退版本
    FA_VERSION="2.5.6" # 请将fallback_version替换为实际的回退版本号
fi

# VLLM_VERSION=0.3.3
# https://github.com/vllm-project/vllm/releases/download/v${VLLM_VERSION}/vllm-${VLLM_VERSION}+${CUDAVER}-cp${PYTHON_VERSION}-cp${PYTHON_VERSION}-manylinux1_x86_64.whl --no-deps
MAMBA_NO_LOW_SPEED_LIMIT=1 mamba env create -f environment.yml -n $1 --force
source activate $1
echo $CONDA_PREFIX
PYTHON_VER=$(python -c 'import sys; ver=sys.version_info; print(f"{ver.major}.{ver.minor}")')
TORCH_VERSION=$(pip show torch | grep "Version:" | cut -d ' ' -f 2 | cut -d "." -f1,2)
FA_URL="https://github.com/Dao-AILab/flash-attention/releases/download/v$FA_VERSION/flash_attn-${FA_VERSION}+${CUDAVER}torch${TORCH_VERSION}cxx11abiFALSE-${PYTHON_VERSION}-${PYTHON_VERSION}-linux_x86_64.whl"
export CUDNN_PATH=$CONDA_PREFIX/lib/python$PYTHON_VER/site-packages/nvidia/cudnn
export NVTE_FRAMEWORK=pytorch
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$CUDNN_PATH/lib
export LIBRARY_PATH=$CONDA_PREFIX/lib/stubs:$LIBRARY_PATH
set +e
cat requirements.txt | xargs -L 1 pip install
# pip install -r requirements.txt
set -e

mamba env config vars set -p $CONDA_PREFIX LD_LIBRARY_PATH=$LD_LIBRARY_PATH
mamba env config vars set -p $CONDA_PREFIX LIBRARY_PATH=$LIBRARY_PATH

bash -c 'cd $CUDNN_PATH/lib && for file in *.so.8; do ln -s "$file" "${file%.8}"; done'

mamba install -c xformers xformers

# pip install git+https://github.com/NVIDIA/TransformerEngine.git@stable
# pip install flash-attn git+https://github.com/Dao-AILab/flash-attention.git
pip install $FA_URL

# git clone https://github.com/NVIDIA/cutlass --depth 1
# DS_BUILD_OPS=1 DS_BUILD_SPARSE_ATTN=0 DS_BUILD_EVOFORMER_ATTN=0 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"
DS_BUILD_FUSED_ADAM=1 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"
python -m torch.utils.collect_env

ds_report
python -c 'import tensorflow as tf; print(tf.config.list_physical_devices("GPU"))'
