@echo off

python bullet-trade-main.py server ^
    --listen 0.0.0.0 ^
    --port 58620 ^
    --token secret_guojin ^
    --enable-data ^
    --enable-broker ^
    --accounts guojin=8884921312:stock

@REM zheshang=327006008:stock
@REM guojin=8884921312:stock
