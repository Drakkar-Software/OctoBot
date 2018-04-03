#!/bin/sh
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
untar ta-lib-0.4.0-src.tar.gz
cd ta-lib-0.4.0-src
./configure --prefix=/usr
make
sudo make install