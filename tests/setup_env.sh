#!/bin/bash
set -ex
# 首先检查是否提供了环境位置参数
if [ -z "$1" ]; then
	echo "未提供环境位置参数"
	exit 1
fi

# pip install git+https://github.com/sustech-data/cocker.git
cocker dl.yml
mamba env create -f environment.yml -n $1 --force
source activate $1
echo $CONDA_PREFIX
PYTHON_VER=$(python -c 'import sys; ver=sys.version_info; print(f"{ver.major}.{ver.minor}")')
export CUDNN_PATH=$CONDA_PREFIX/lib/python$PYTHON_VER/site-packages/nvidia/cudnn
export NVTE_FRAMEWORK=pytorch
export MAMBA_NO_LOW_SPEED_LIMIT=1
mamba env config vars set -p $CONDA_PREFIX LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$CUDNN_PATH/lib

bash -c 'cd $CUDNN_PATH/lib && for file in *.so.8; do ln -s "$file" "${file%.8}"; done'

# pip install git+https://github.com/NVIDIA/TransformerEngine.git@stable
# git clone https://github.com/Dao-AILab/flash-attention.git
# cd flash-attnention
# python setup.py install
# pip install trl --no-deps
# pip install xformers --no-deps
# pip install flash-attn --no-build-isolation --no-deps --force-reinstall
# pip install flash-attn git+https://github.com/Dao-AILab/flash-attention.git

# git clone https://github.com/NVIDIA/cutlass --depth 1
# DS_BUILD_OPS=1 DS_BUILD_SPARSE_ATTN=0 DS_BUILD_EVOFORMER_ATTN=0 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"
DS_BUILD_FUSED_ADAM=1 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"
pip install deepspeed
# pip install https://github.com/vllm-project/vllm/releases/download/v0.2.2/vllm-0.2.2+cu118-cp310-cp310-manylinux1_x86_64.whl --no-deps
# pip install xformers==0.0.22.post4 --index-url https://download.pytorch.org/whl/cu118 --no-deps
ds_report
python -m torch.utils.collect_env
