@echo off
chcp 65001 >nul
title 幻象机 · 人设知识库系统

echo ========================================
echo    幻象机 · 人设知识库系统
echo ========================================
echo.

cd /d "%~dp0"

REM 检测Python命令（优先python，其次py）
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [错误] 未检测到Python，请先安装Python 3.9+
        echo 下载地址: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo [1/3] 创建虚拟环境...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖（使用清华镜像加速）
echo [2/3] 安装依赖（首次运行较慢，请耐心等待）...
pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，核心功能仍可使用
)

REM 启动服务
echo.
echo [3/3] 启动服务...
echo.
echo ========================================
echo  服务已启动！
echo  前端页面: http://localhost:8000
echo  API文档:  http://localhost:8000/docs
echo ========================================
echo.

python backend\app.py

pause
