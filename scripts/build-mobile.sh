#!/bin/bash

set -e

echo "================================="
echo "Building XynaFaith Mobile"
echo "================================="

rm -rf mobile/www

mkdir -p mobile/www

cp -R ui-faith/* mobile/www/

echo ""
echo "Build Complete"