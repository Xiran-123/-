# 幻象机 · 人设知识库系统 - 一键启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   幻象机 · 人设知识库系统" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# 检查Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[错误] 未检测到Python，请先安装Python 3.9+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "[1/3] 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
}

# 激活虚拟环境
& .\venv\Scripts\Activate.ps1

# 安装依赖
Write-Host "[2/3] 安装依赖..." -ForegroundColor Yellow
pip install -r backend\requirements.txt -q

# 启动服务
Write-Host "[3/3] 启动服务..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " 服务已启动！" -ForegroundColor Green
Write-Host " 前端页面: http://localhost:8000" -ForegroundColor White
Write-Host " API文档:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

python backend\app.py
