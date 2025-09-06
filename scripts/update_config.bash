#!/bin/bash
set -o errexit

rm -rf flash
mkdir flash
mpy-cross -o flash/config.mpy config.py
mpremote cp -r flash/* :.
rm -rf flash
