@echo off
chcp 65001 >nul
echo ============================================
echo  大观街道社区卫生服务中心智能问答系统
echo ============================================
echo.

:: 检查 .env 文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件，正在从 .env.example 复制...
    copy .env.example .env
    echo [请求] 请编辑 .env 文件，填写 DEEPSEEK_API_KEY 后重新运行！
    pause
    exit /b 1
)

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [提示] 正在创建虚拟环境...
    python -m venv venv
)

echo [提示] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [提示] 安装/检查依赖...
pip install -r requirements.txt -q

echo.
echo [启动] 正在启动应用，请稍候...
echo [访问] 浏览器将自动打开 http://localhost:8501
echo [停止] 按 Ctrl+C 停止服务
echo.

streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0

pause
