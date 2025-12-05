# TRMNL Task Manager Widget - Windows Installation Script
# Run this script as Administrator on your Windows Server 2019

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  TRMNL Task Manager Widget - Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Warning: Running without admin rights. Firewall rule creation may fail." -ForegroundColor Yellow
    Write-Host ""
}

# Check Python installation
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python from https://python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Install psutil
Write-Host ""
Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
pip install psutil --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "psutil installed successfully" -ForegroundColor Green
} else {
    Write-Host "Warning: Failed to install psutil. Try running: pip install psutil" -ForegroundColor Yellow
}

# Create firewall rule
Write-Host ""
Write-Host "[3/4] Creating firewall rule for port 8080..." -ForegroundColor Yellow
if ($isAdmin) {
    $existingRule = Get-NetFirewallRule -DisplayName "TRMNL Metrics" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "Firewall rule already exists" -ForegroundColor Green
    } else {
        New-NetFirewallRule -DisplayName "TRMNL Metrics" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow | Out-Null
        Write-Host "Firewall rule created" -ForegroundColor Green
    }
} else {
    Write-Host "Skipped (requires admin rights)" -ForegroundColor Yellow
}

# Get server IP
Write-Host ""
Write-Host "[4/4] Getting server IP addresses..." -ForegroundColor Yellow
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -ne "127.0.0.1" }
Write-Host ""
Write-Host "Your server IP addresses:" -ForegroundColor Cyan
foreach ($ip in $ips) {
    Write-Host "  - $($ip.IPAddress)" -ForegroundColor White
}

# Done
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run the server:     python server.py" -ForegroundColor White
Write-Host "2. Test it works:      Open http://localhost:8080/metrics in browser" -ForegroundColor White
Write-Host "3. Create TRMNL plugin with polling URL:" -ForegroundColor White
Write-Host "   http://<YOUR_IP>:8080/metrics" -ForegroundColor Yellow
Write-Host ""
Write-Host "See SETUP.md for detailed instructions" -ForegroundColor Gray
