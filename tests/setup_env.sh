#!/bin/bash

#SBATCH --job-name=any
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1          # crucial - only 1 task per dist per node!
#SBATCH --cpus-per-task=32 #
#SBATCH -o /cognitive_comp/zejianxie/outputs/%j-%x.log
#SBATCH -e /cognitive_comp/zejianxie/outputs/%j-%x.err
#SBATCH -p pog
# SBATCH --requeue
# SBATCH --qos=preemptive

set -ex
# 首先检查是否提供了环境位置参数
if [ -z "$1" ]; then
	echo "未提供环境位置参数"
	exit 1
fi

# export PATH=$CONDA_PREFIX/bin:$PATH
# pip install git+https://github.com/sustech-data/cocker.git
# pip install cocker/
# cocker remote.yml
# source activate cocker
# cocker dl.yml
mamba env create -f environment.yml -n $1 --force
source activate $1
echo $CONDA_PREFIX
mamba env config vars set -p $CONDA_PREFIX LD_LIBRARY_PATH=$CONDA_PREFIX/lib
pip install trl --no-deps
# pip install xformers --no-deps
pip install flash-attn --no-build-isolation
# git clone https://github.com/NVIDIA/cutlass --depth 1
# DS_BUILD_OPS=1 DS_BUILD_SPARSE_ATTN=0 DS_BUILD_EVOFORMER_ATTN=0 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"
DS_BUILD_FUSED_ADAM=1 pip install --no-binary deepspeed --no-cache-dir deepspeed --global-option="build_ext"


# Link Torch Libs
SRC_DIR="$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib"
DEST_DIR="$CONDA_PREFIX/lib"
if [ ! -d "$SRC_DIR" ]; then
	echo "源文件夹 $SRC_DIR 不存在!"
	exit 1
fi

# 检查目标文件夹是否存在
if [ ! -d "$DEST_DIR" ]; then
	echo "目标文件夹 $DEST_DIR 不存在!"
	exit 1
fi

# 为目标文件夹中的每一个.so文件创建软链接
find "$SRC_DIR" -type f -name "*.so" -exec ln -s {} "$DEST_DIR" \;
echo "链接完成!"
ds_report
python -m torch.utils.collect_env
