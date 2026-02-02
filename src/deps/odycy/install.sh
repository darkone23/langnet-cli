#!/usr/bin/env bash
# 
# To install the small pipeline

ODYCY_SMALL_WHEEL="https://huggingface.co/chcaa/grc_odycy_joint_sm/resolve/main/grc_odycy_joint_sm-any-py3-none-any.whl"
OUTFILE="./grc_odycy_joint_sm-0.7.0-py3-none-any.whl"

if [ ! -f $OUTFILE ]; then
  wget $ODYCY_SMALL_WHEEL -O $OUTFILE
  pip3 install $OUTFILE
else
  echo "grc_odycy_joint_sm already installed" 1>&2
fi
